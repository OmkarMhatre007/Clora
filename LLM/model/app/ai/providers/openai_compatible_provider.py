"""
OpenAI-Compatible Universal Provider for CLORA Sovereign Model Control Plane.
Adapts any standard local OpenAI-compatible inference server: vLLM, llama-server, LocalAI, TGI, LM Studio.
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any, List

import httpx

from app.ai.providers.base_provider import BaseModelProvider
from app.ai.control_plane.models import (
    LifecycleAuthority,
    UnloadResult,
    ProviderCapabilities,
)
from app.ai.sovereignty import SovereignEndpointPolicy

logger = logging.getLogger("indusai.provider.openai_compatible")


class OpenAICompatibleProvider(BaseModelProvider):
    """
    Universal adapter for OpenAI-compatible inference servers.
    Operates under LifecycleAuthority.EXTERNAL_ORCHESTRATOR.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000/v1",
        api_key: Optional[str] = "local-key",
        timeout: int = 30,
        provider_name: str = "openai-compatible",
    ):
        super().__init__(
            provider_name=provider_name,
            lifecycle_authority=LifecycleAuthority.EXTERNAL_ORCHESTRATOR,
        )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "local-key"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        SovereignEndpointPolicy.check_destination(self.base_url)
        if self._client is None or self._client.is_closed:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(self.timeout, connect=5.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health(self) -> bool:
        """Check if server responds on /models or /health."""
        try:
            client = await self._get_client()
            r = await client.get("/models")
            return r.status_code in (200, 401)
        except Exception:
            return False

    def get_capabilities(self, model: str) -> ProviderCapabilities:
        """Standard declared capabilities for OpenAI-compatible server."""
        return ProviderCapabilities(
            chat=True,
            completion=True,
            tools={"declared": True, "verified": False},
            structured_json={"declared": True, "verified": False},
            vision=False,
            streaming=True,
        )

    async def unload(self, model: str) -> UnloadResult:
        """
        External servers (e.g. static vLLM) own their model lifecycle.
        CLORA does not pretend to unload an externally managed process.
        """
        return UnloadResult(
            supported=False,
            reason=f"Provider '{self.provider_name}' is externally managed ({self.lifecycle_authority.value}); model lifecycle owned by runtime.",
        )

    async def list_models(self) -> List[Dict[str, Any]]:
        """Query /v1/models for available model tags."""
        try:
            client = await self._get_client()
            r = await client.get("/models")
            if r.status_code != 200:
                return []
            data = r.json()
            models = []
            for item in data.get("data", []):
                model_id = item.get("id", "")
                models.append({
                    "model": model_id,
                    "provider": self.provider_name,
                    "digest": None,
                    "estimated_vram_mb": 8192,
                })
            return models
        except Exception as exc:
            logger.warning("Failed to list models from %s: %s", self.base_url, exc)
            return []

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
        """Convert generate to chat completions format for maximum compatibility."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            trace_id=trace_id,
            **kwargs,
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_id: str = "TRC-00000",
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute chat completion via /v1/chat/completions."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        t0 = time.perf_counter()
        client = await self._get_client()
        resp = await client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        usage = data.get("usage", {})

        return {
            "message": msg,
            "response": msg.get("content", ""),
            "model": data.get("model", model),
            "provider": self.provider_name,
            "latency_ms": latency_ms,
            "tokens_generated": usage.get("completion_tokens", 0),
            "trace_id": trace_id,
            "done": True,
        }
