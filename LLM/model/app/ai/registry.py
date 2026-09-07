"""
Model Registry & Sovereign Model Gateway for CLORA.
Thin facade coordinating ModelCatalog, AdmissionEngine, ModelLifecycleManager,
DiscoveryManager, and provider SPI instances.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, Optional, List, Protocol

from app.ai.control_plane.models import (
    ModelRef,
    ModelStatus,
    TaskRequirements,
    ModelAdmissionDecision,
)
from app.ai.control_plane.catalog import ModelCatalog
from app.ai.control_plane.admission import AdmissionEngine
from app.ai.control_plane.discovery import DiscoveryManager
from app.ai.control_plane.lifecycle import ModelLifecycleManager
from app.ai.control_plane.gpu import GPUResourceProvider
from app.ai.providers.base_provider import BaseModelProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.ai.providers.mock_provider import MockProvider
from app.ai.sovereignty import global_audit_chain, SovereignEndpointPolicy
from app.ai.models import (
    DEFAULT_MODEL,
    resolve_model,
    get_model_capabilities,
    ModelCapabilities,
)

logger = logging.getLogger("indusai.gateway")


class ModelProviderProtocol(Protocol):
    async def health(self) -> bool: ...
    def get_capabilities(self, model: str) -> Any: ...
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]: ...
    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]: ...


class ModelGateway:
    """
    Sovereign Model Gateway (ModelRegistry).
    Orchestrates catalog persistence, admission control, lifecycle transitions,
    and provider routing.
    """

    _instance: Optional[ModelGateway] = None

    def __new__(cls) -> ModelGateway:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.catalog = ModelCatalog()
        self.audit_chain = global_audit_chain

        self._providers: Dict[str, BaseModelProvider] = {
            "ollama": OllamaProvider(),
            "openai-compatible": OpenAICompatibleProvider(),
            "mock": MockProvider(),
        }

        self.lifecycle_manager = ModelLifecycleManager(
            catalog=self.catalog,
            audit_chain=self.audit_chain,
            providers=self._providers,
        )

        self.discovery_manager = DiscoveryManager(catalog=self.catalog)
        self._telemetry_log: List[Dict[str, Any]] = []
        self._initialized = True
        logger.info("ModelGateway initialized with SQLite catalog and providers: %s", list(self._providers.keys()))

    @property
    def active_model(self) -> str:
        state = self.catalog.get_state()
        raw = state.get("active_model", "llama3.2:3b")
        ref = ModelRef.from_string(raw)
        return ref.model if ref.provider == "ollama" else ref.canonical_id

    @property
    def active_provider_name(self) -> str:
        ref = ModelRef.from_string(self.active_model)
        return ref.provider

    def get_provider(self, provider_name: Optional[str] = None) -> BaseModelProvider:
        name = provider_name or self.active_provider_name
        if name not in self._providers:
            # Fallback to ollama or mock if available
            if "ollama" in self._providers and name == "ollama":
                return self._providers["ollama"]
            raise KeyError(f"Provider '{name}' is not registered. Available: {list(self._providers.keys())}")
        return self._providers[name]

    def register_provider(self, name: str, provider: BaseModelProvider) -> None:
        """Register a new provider instance at runtime."""
        self._providers[name] = provider
        logger.info("Registered provider runtime: %s (%s)", name, provider.__class__.__name__)

    # --- Model Switching & Lifecycle ---

    async def switch_model(self, target_model: str, actor: str = "system", role: str = "ENGINEER") -> Dict[str, Any]:
        """
        Transactional model switch with atomic CAS, VRAM-aware admission check,
        and automatic rollback.
        """
        res = await self.lifecycle_manager.execute_switch(
            target_model=target_model,
            actor=actor,
            role=role,
        )
        if res.get("conflict"):
            return {
                "success": False,
                "active_model": self.active_model,
                "reason": res["error"],
                "rollback_performed": False,
                "conflict": True,
            }

        if not res["success"]:
            return {
                "success": False,
                "active_model": res.get("active_model", self.active_model),
                "reason": res.get("error", "Switch failed"),
                "rollback_performed": True,
            }

        return {
            "success": True,
            "active_model": res["active_model"],
            "transition_id": res.get("transition_id"),
            "rollback_performed": False,
        }

    # --- High-Level Inference Dispatcher ---

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List[str]] = None,
        trace_id: str = "TRC-00000",
        provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch generation through active provider with capability check."""
        target_str = model or self.active_model
        ref = ModelRef.from_string(target_str)

        # Legacy model mapping if bare model name passed
        if ref.provider == "ollama" and ref.model not in ("llama3.2:3b", "qwen2.5:3b", "phi3:mini", "moondream"):
            try:
                resolved = resolve_model(ref.model)
                ref = ModelRef.from_string(resolved)
            except Exception:
                pass

        if ref.model == "mock-sovereign" or provider_name == "mock":
            prov = self.get_provider("mock")
            return await prov.generate(
                prompt=prompt,
                model=ref.model,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                images=images,
                trace_id=trace_id,
            )

        prov = self.get_provider(provider_name or ref.provider)
        return await prov.generate(
            prompt=prompt,
            model=ref.model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            images=images,
            trace_id=trace_id,
        )

    async def health_check_all(self) -> Dict[str, Any]:
        """Check health across all registered providers."""
        results = {}
        for p_name, provider in self._providers.items():
            try:
                healthy = await provider.health()
                results[p_name] = "HEALTHY" if healthy else "UNAVAILABLE"
            except Exception:
                results[p_name] = "ERROR"

        return {
            "active_model": self.active_model,
            "sovereign_mode": True,
            "providers": results,
            "gpu_telemetry": GPUResourceProvider.get_telemetry(),
        }

    def list_registered_models(self) -> List[Dict[str, Any]]:
        """List all models in the catalog."""
        return self.catalog.list_models()

    async def discover_models(self, force: bool = False) -> List[Dict[str, Any]]:
        """Trigger cached candidate discovery across local runtimes."""
        return await self.discovery_manager.discover_candidates(self._providers, force=force)


# Dataclass & alias helpers
ModelRegistry = ModelGateway
registry = ModelGateway()
