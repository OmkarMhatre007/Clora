"""
Admission Engine & Pre-Inference Governance Controller for CLORA.
Evaluates model approval, provider health, sovereignty egress, workload capability match,
and GPU VRAM headroom based on multi-tiered confidence scoring.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from app.ai.control_plane.models import (
    ModelAdmissionDecision,
    MemoryConfidence,
    TaskRequirements,
    ModelStatus,
)
from app.ai.control_plane.gpu import GPUResourceProvider
from app.ai.sovereignty import SovereignEndpointPolicy

logger = logging.getLogger("indusai.admission")


class AdmissionEngine:
    """
    Evaluates whether a model can be safely admitted for execution or switching.
    Guarantees fail-closed safety and full audit transparency.
    """

    @classmethod
    def evaluate(
        cls,
        model_record: Dict[str, Any],
        provider_base_url: str,
        provider_healthy: bool,
        task_requirements: Optional[TaskRequirements] = None,
        kv_cache_mb: int = 1024,
        runtime_overhead_mb: int = 512,
    ) -> ModelAdmissionDecision:
        """
        Evaluate full admission criteria and produce a ModelAdmissionDecision.
        """
        model_name = model_record.get("canonical_id") or model_record.get("model", "unknown")
        status_str = model_record.get("status", ModelStatus.DISCOVERED.value)

        checks = {
            "approved": status_str in (ModelStatus.APPROVED.value, ModelStatus.ACTIVE.value),
            "provider_healthy": provider_healthy,
            "sovereign_endpoint": False,
            "artifact_verified": status_str != ModelStatus.ARTIFACT_CHANGED.value,
            "capabilities_match": True,
            "vram_sufficient": True,
        }

        # 1. Sovereignty Check
        try:
            checks["sovereign_endpoint"] = SovereignEndpointPolicy.check_destination(provider_base_url)
        except Exception as exc:
            logger.warning("Admission sovereignty check failed for %s: %s", provider_base_url, exc)
            checks["sovereign_endpoint"] = False

        # 2. Capability Negotiation
        if task_requirements:
            effective_context = model_record.get("effective_context_length", 4096)
            if effective_context < task_requirements.min_context:
                checks["capabilities_match"] = False
            if task_requirements.needs_tools and not model_record.get("supports_tools"):
                checks["capabilities_match"] = False
            if task_requirements.needs_json and not model_record.get("supports_json"):
                checks["capabilities_match"] = False
            if task_requirements.needs_vision and not model_record.get("supports_vision"):
                checks["capabilities_match"] = False

        # 3. VRAM Admission Check
        telemetry = GPUResourceProvider.get_telemetry()
        available_vram = telemetry["free_vram_mb"]
        confidence = telemetry["confidence"]

        safety_margin_mb = 2048 if confidence == MemoryConfidence.ESTIMATED else 1024
        estimated_model = model_record.get("estimated_vram_mb", 4096)
        required_vram = estimated_model + kv_cache_mb + runtime_overhead_mb + safety_margin_mb

        if confidence == MemoryConfidence.UNKNOWN:
            # Cannot safely admit with zero telemetry
            checks["vram_sufficient"] = False
        else:
            checks["vram_sufficient"] = (available_vram >= required_vram)

        # Final Decision
        allowed = all(checks.values())
        reasons = []
        if not checks["approved"]:
            reasons.append(f"Model status is '{status_str}', not APPROVED")
        if not checks["provider_healthy"]:
            reasons.append("Inference provider is unreachable/unhealthy")
        if not checks["sovereign_endpoint"]:
            reasons.append("Endpoint violates SOVEREIGN_MODE policy")
        if not checks["artifact_verified"]:
            reasons.append("Model weights digest changed; re-approval required")
        if not checks["capabilities_match"]:
            reasons.append("Model capabilities do not meet workload requirements")
        if not checks["vram_sufficient"]:
            reasons.append(f"Insufficient VRAM: required {required_vram} MB, available {available_vram} MB")

        reason_str = "Admitted" if allowed else "; ".join(reasons)

        return ModelAdmissionDecision(
            allowed=allowed,
            model=model_name,
            reason=reason_str,
            checks=checks,
            required_vram_mb=required_vram,
            available_vram_mb=available_vram,
            confidence=confidence,
        )
