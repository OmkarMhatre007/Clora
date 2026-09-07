"""
Mock Provider Implementation for Automated Testing & Integration CI.
STRICTLY FLAGGED test_only=True. Never used as a production LLM fallback.
"""
from __future__ import annotations

import time
from typing import Dict, Any, List, Optional

from app.ai.providers.base_provider import BaseModelProvider
from app.ai.control_plane.models import (
    LifecycleAuthority,
    UnloadResult,
    ProviderCapabilities,
)
from app.ai.models import ModelCapabilities


class MockProvider(BaseModelProvider):
    """Mock Provider strictly for unit testing and CI validation."""

    def __init__(self, provider_name: str = "mock"):
        super().__init__(
            provider_name=provider_name,
            lifecycle_authority=LifecycleAuthority.PROVIDER,
        )
        self.model_name = "mock-sovereign"
        self._healthy = True
        self.unload_call_count = 0

    def set_health(self, healthy: bool) -> None:
        self._healthy = healthy

    async def health(self) -> bool:
        return self._healthy

    def get_capabilities(self, model: str = "mock-sovereign") -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            completion=True,
            tools={"declared": True, "verified": True},
            structured_json={"declared": True, "verified": True},
            vision=True,
            streaming=True,
        )

    def get_model_capabilities(self, model: str = "mock-sovereign") -> ModelCapabilities:
        """Backwards compatibility for legacy tests."""
        return ModelCapabilities(
            name="mock-sovereign",
            label="Mock Engine (Unit Test Only)",
            context_length=4096,
            supports_tools=True,
            supports_json=True,
            supports_vision=True,
            local_only=True,
            network_required=False,
            test_only=True,
        )

    async def unload(self, model: str) -> UnloadResult:
        self.unload_call_count += 1
        return UnloadResult(
            supported=True,
            reason="Mock model evicted from simulated VRAM",
            freed_vram_mb=4096,
        )

    async def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "model": "mock-sovereign",
                "provider": self.provider_name,
                "digest": "sha256:mock000000000000000000000000000000000000000000000000000000000000",
                "estimated_vram_mb": 2048,
            }
        ]

    async def generate(
        self,
        prompt: str,
        model: str = "mock-sovereign",
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List[str]] = None,
        trace_id: str = "TRC-TEST",
        **kwargs,
    ) -> Dict[str, Any]:
        """Return simulated structured test output."""
        return {
            "response": f"[MOCK TEST RESPONSE] Analysis for: '{prompt[:60]}...'",
            "model": model,
            "provider": "mock_test_only",
            "latency_ms": 15.0,
            "tokens_generated": 20,
            "tokens_per_second": 1333.3,
            "temperature": 0.0,
            "trace_id": trace_id,
            "done": True,
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "mock-sovereign",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_id: str = "TRC-TEST",
        **kwargs,
    ) -> Dict[str, Any]:
        return {
            "message": {"role": "assistant", "content": "[MOCK CHAT RESPONSE] Test completed."},
            "response": "[MOCK CHAT RESPONSE] Test completed.",
            "model": model,
            "provider": self.provider_name,
            "latency_ms": 10.0,
            "tokens_generated": 10,
            "trace_id": trace_id,
            "done": True,
        }
