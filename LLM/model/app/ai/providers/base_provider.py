"""
Base Model Provider SPI for CLORA Sovereign Model Control Plane.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from app.ai.control_plane.models import (
    LifecycleAuthority,
    UnloadResult,
    ProviderCapabilities,
)


class BaseModelProvider(ABC):
    """
    Abstract Service Provider Interface (SPI) for inference runtimes.
    Decouples CLORA agents from runtime-specific communication protocols.
    """

    def __init__(self, provider_name: str, lifecycle_authority: LifecycleAuthority):
        self.provider_name = provider_name
        self.lifecycle_authority = lifecycle_authority

    @abstractmethod
    async def health(self) -> bool:
        """Check if provider daemon / socket is reachable and healthy."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List[str]] = None,
        trace_id: str = "TRC-00000",
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute non-streaming text generation."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_id: str = "TRC-00000",
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute chat completion."""
        pass

    @abstractmethod
    async def unload(self, model: str) -> UnloadResult:
        """
        Request model eviction from GPU memory.
        Returns UnloadResult with supported=True if provider handles unload,
        or supported=False if lifecycle is externally managed.
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """Query runtime for locally available models and digests."""
        pass

    @abstractmethod
    def get_capabilities(self, model: str) -> ProviderCapabilities:
        """Return declared/verified capabilities for model."""
        pass
