"""
Inference & Sovereign Model Control Plane API routes for CLORA.
Endpoints: generate, stream, models (catalog/discover/register/approve/switch/unload/transitions),
sovereignty status, and deliverables generation.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.ai.models import UnsupportedModelError, list_models, resolve_model, DEFAULT_MODEL
from app.ai.prompts import list_tasks
from app.ai.inference import InferenceService, UnsafePromptError
from app.ai.registry import registry
from app.ai.sovereignty import SovereignEndpointPolicy, SovereigntyViolationError
from app.ai.rbac import RBACManager, UserRole, ModelPermission
from app.ai.providers.openai_compatible_provider import OpenAICompatibleProvider

logger = logging.getLogger("indusai.routes")
router = APIRouter(tags=["inference"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The user prompt to process")
    model: Optional[str] = Field(None, description="Model tag (uses default if omitted)")
    task: str = Field("general", description="Task type: general, summarize, classify, reason, extract")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8192)
    images: Optional[List[str]] = Field(None, description="Optional base64 images for visual models")
    check_safety: bool = Field(True, description="Whether to check prompt safety")
    trace_id: Optional[str] = Field(None, description="Trace ID for telemetry and audit chain")


class GenerateResponse(BaseModel):
    model: str
    response: str
    tokens_generated: Optional[int] = None
    latency_ms: Optional[float] = None
    trace_id: Optional[str] = None
    done: bool = True


class SwitchModelRequest(BaseModel):
    model: str = Field(..., description="Target model tag (e.g. ollama/llama3.2:3b or llama3.2:3b)")
    user_role: Optional[str] = Field("ENGINEER", description="Refinery user role requesting the switch")


class RegisterModelRequest(BaseModel):
    provider: str = Field("ollama", description="Provider hosting the model (e.g. ollama, openai-compatible)")
    model: str = Field(..., description="Model identifier")
    label: Optional[str] = Field(None, description="Human-readable display name")
    context_length: int = Field(8192, description="Model context window length")
    estimated_vram_mb: int = Field(4096, description="Advisory VRAM requirement in MB")
    user_role: Optional[str] = Field("PLANT_DIRECTOR", description="Role registering model")


class ApproveModelRequest(BaseModel):
    canonical_id: str = Field(..., description="Target model canonical id (e.g. ollama/qwen2.5:3b)")
    user_role: Optional[str] = Field("PLANT_DIRECTOR", description="Role approving model")


class RevokeModelRequest(BaseModel):
    canonical_id: str = Field(..., description="Target model canonical id")
    user_role: Optional[str] = Field("PLANT_DIRECTOR", description="Role revoking model")


class UnloadModelRequest(BaseModel):
    model: Optional[str] = Field(None, description="Model to unload from VRAM (defaults to active)")
    user_role: Optional[str] = Field("OPERATIONS_SUPERVISOR", description="Role requesting unload")


class RegisterProviderRequest(BaseModel):
    name: str = Field(..., description="Provider unique identifier (e.g. edge-vllm)")
    provider_type: str = Field("openai-compatible", description="Provider type: openai-compatible or ollama")
    base_url: str = Field(..., description="Inference endpoint base URL")
    api_key: Optional[str] = Field(None, description="Optional local token/API key")
    user_role: Optional[str] = Field("PLANT_DIRECTOR", description="Role configuring provider")


class DeliverableGenerateRequest(BaseModel):
    investigation_id: Optional[str] = Field(None, description="Investigation ID")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    user_query: Optional[str] = Field(None, description="Query text")
    user_role: Optional[str] = Field("ENGINEER", description="User authorization role")
    format_type: str = Field("all", description="Output format: docx, xlsx, pptx, zip, all")


def _get_service(request: Request) -> InferenceService:
    service = getattr(request.app.state, "inference_service", None)
    if not service:
        service = InferenceService()
        request.app.state.inference_service = service
    return service


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/health", summary="Basic health probe")
async def health(request: Request):
    service = _get_service(request)
    ollama_ok = await service.health_check()
    return {
        "status": "ok" if ollama_ok else "degraded",
        "sovereign_mode": True,
        "ollama": "reachable" if ollama_ok else "unreachable",
        "active_model": registry.active_model,
    }


@router.get("/sovereignty/status", summary="Sovereignty & Egress Policy Status")
async def sovereignty_status():
    return SovereignEndpointPolicy.get_status()


# --- Control Plane Model Governance Routes ---

@router.get("/models", summary="List registered models and capabilities")
async def get_models():
    return {
        "active_model": registry.active_model,
        "active_provider": registry.active_provider_name,
        "models": registry.list_registered_models(),
    }


@router.post("/models/discover", summary="Discover locally installed candidate models")
async def discover_models(request: Request, force: bool = False):
    role = RBACManager.resolve_role(request.headers.get("X-User-Role", "ENGINEER"))
    RBACManager.require_model_permission(role, ModelPermission.DISCOVER)
    discovered = await registry.discover_models(force=force)
    return {
        "status": "success",
        "count": len(discovered),
        "candidates": discovered,
    }


@router.post("/models/register", summary="Stage a new candidate model in the catalog")
async def register_model(body: RegisterModelRequest):
    role = RBACManager.resolve_role(body.user_role)
    RBACManager.require_model_permission(role, ModelPermission.REGISTER)

    candidate = registry.catalog.register_candidate(
        provider=body.provider,
        model=body.model,
        label=body.label,
        context_length=body.context_length,
        estimated_vram_mb=body.estimated_vram_mb,
    )
    return {
        "status": "staged",
        "model": candidate,
    }


@router.post("/models/approve", summary="Approve a candidate model for active execution")
async def approve_model(body: ApproveModelRequest):
    role = RBACManager.resolve_role(body.user_role)
    RBACManager.require_model_permission(role, ModelPermission.APPROVE)

    success = registry.catalog.approve_model(body.canonical_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model '{body.canonical_id}' not found")
    return {
        "status": "approved",
        "canonical_id": body.canonical_id,
    }


@router.post("/models/revoke", summary="Revoke approval for a model")
async def revoke_model(body: RevokeModelRequest):
    role = RBACManager.resolve_role(body.user_role)
    RBACManager.require_model_permission(role, ModelPermission.REVOKE)

    success = registry.catalog.revoke_model(body.canonical_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model '{body.canonical_id}' not found")
    return {
        "status": "revoked",
        "canonical_id": body.canonical_id,
    }


@router.post("/models/switch", summary="Resource-aware model switch with automatic rollback", status_code=status.HTTP_200_OK)
async def switch_model(body: SwitchModelRequest):
    role = RBACManager.resolve_role(body.user_role)
    RBACManager.require_model_permission(role, ModelPermission.SWITCH)

    try:
        res = await registry.switch_model(body.model, role=role.value)
        if res.get("conflict"):
            raise HTTPException(status_code=409, detail=res.get("reason"))
        if not res["success"]:
            raise HTTPException(status_code=400, detail=f"Model switch failed: {res.get('reason')}")
        return res
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/models/transitions/{transition_id}", summary="Inspect status of an asynchronous switch transition")
async def get_transition(transition_id: str):
    tr = registry.catalog.get_transition(transition_id)
    if not tr:
        raise HTTPException(status_code=404, detail=f"Transition '{transition_id}' not found")
    return tr


@router.post("/models/unload", summary="Evict active model from GPU VRAM")
async def unload_model(body: UnloadModelRequest):
    role = RBACManager.resolve_role(body.user_role)
    RBACManager.require_model_permission(role, ModelPermission.UNLOAD)

    target = body.model or registry.active_model
    provider = registry.get_provider()
    res = await provider.unload(target)
    return {
        "model": target,
        "supported": res.supported,
        "reason": res.reason,
        "freed_vram_mb": res.freed_vram_mb,
    }


@router.get("/models/providers", summary="List registered provider runtimes and health")
async def get_providers():
    return await registry.health_check_all()


@router.post("/models/providers", summary="Register an inference provider runtime with SSRF validation")
async def register_provider(body: RegisterProviderRequest):
    role = RBACManager.resolve_role(body.user_role)
    RBACManager.require_model_permission(role, ModelPermission.PROVIDER_MANAGE)

    # SSRF & DNS rebinding validation
    try:
        SovereignEndpointPolicy.check_destination(body.base_url)
    except SovereigntyViolationError as exc:
        raise HTTPException(status_code=400, detail=f"Provider endpoint rejected by security policy: {exc}")

    if body.provider_type == "openai-compatible":
        prov = OpenAICompatibleProvider(
            base_url=body.base_url,
            api_key=body.api_key,
            provider_name=body.name,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider type '{body.provider_type}'")

    registry.register_provider(body.name, prov)
    return {
        "status": "registered",
        "provider": body.name,
        "base_url": body.base_url,
    }


# --- Inference Execution ---

@router.post("/generate", summary="Full text generation with telemetry", response_model=GenerateResponse)
async def generate(body: GenerateRequest, request: Request):
    service = _get_service(request)
    trace_id = body.trace_id or f"TRC-{int(request.state.get('start_time', 0)*1000)}" if hasattr(request.state, "start_time") else "TRC-00000"

    try:
        result = await service.run(
            prompt=body.prompt,
            task=body.task,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            images=body.images,
            check_safety=body.check_safety,
            trace_id=trace_id,
        )
    except (UnsupportedModelError, UnsafePromptError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Inference failed")
        raise HTTPException(status_code=502, detail=f"Inference error: {exc}")

    return GenerateResponse(
        model=result.get("model", body.model or DEFAULT_MODEL),
        response=result.get("response", ""),
        tokens_generated=result.get("tokens_generated"),
        latency_ms=result.get("latency_ms"),
        trace_id=result.get("trace_id", trace_id),
    )


@router.post("/deliverables/generate", summary="Generate executive deliverables from evidence manifest")
async def generate_deliverables(body: DeliverableGenerateRequest):
    from data_intelligence.deliverable_engine import DeliverableEngine
    try:
        engine = DeliverableEngine()
        res = engine.generate_all(
            user_role=body.user_role or "ENGINEER",
            output_format=body.format_type or "all",
        )
        return {
            "status": "success",
            "deliverables": res,
            "trace_id": body.trace_id,
        }
    except Exception as exc:
        logger.exception("Deliverable generation failed")
        raise HTTPException(status_code=500, detail=f"Deliverable generation failed: {exc}")
