"""
Ollama Provider Implementation for CLORA Sovereign Model Control Plane.
Primary production local inference provider with native tags discovery and keep_alive: 0 VRAM eviction.
"""
from __future__ import annotations

import json
import logging
import time
from typing import AsyncIterator, Optional, Dict, Any, List

import httpx

from app.ai.providers.base_provider import BaseModelProvider
from app.ai.control_plane.models import (
    LifecycleAuthority,
    UnloadResult,
    ProviderCapabilities,
)
from app.ai.models import ModelCapabilities, get_model_capabilities, DEFAULT_MODEL
from app.config import settings
from app.ai.sovereignty import SovereignEndpointPolicy

logger = logging.getLogger("indusai.provider.ollama")


class OllamaProvider(BaseModelProvider):
    """Production Ollama Provider with native discovery and VRAM lifecycle control."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        provider_name: str = "ollama",
    ):
        super().__init__(
            provider_name=provider_name,
            lifecycle_authority=LifecycleAuthority.PROVIDER,
        )
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        SovereignEndpointPolicy.check_destination(self.base_url)
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=settings.connect_timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health(self) -> bool:
        """Health check verifying Ollama local REST endpoint is responsive."""
        try:
            client = await self._get_client()
            r = await client.get("/")
            return r.status_code == 200
        except (httpx.HTTPError, PermissionError):
            return False

    def get_capabilities(self, model: str = DEFAULT_MODEL) -> ProviderCapabilities:
        """Return declared/verified capabilities for the model."""
        caps = get_model_capabilities(model)
        supports_tools = caps.supports_tools if caps else True
        supports_json = caps.supports_json if caps else True
        supports_vision = caps.supports_vision if caps else False

        return ProviderCapabilities(
            chat=True,
            completion=True,
            tools={"declared": supports_tools, "verified": False},
            structured_json={"declared": supports_json, "verified": False},
            vision=supports_vision,
            streaming=True,
        )

    async def unload(self, model: str) -> UnloadResult:
        """Evict model from GPU memory using Ollama's keep_alive: 0 parameter."""
        try:
            client = await self._get_client()
            payload = {
                "model": model,
                "keep_alive": 0,
            }
            resp = await client.post("/api/generate", json=payload, timeout=10.0)
            if resp.status_code == 200:
                logger.info("Successfully evicted model '%s' from VRAM via keep_alive: 0", model)
                return UnloadResult(
                    supported=True,
                    reason="Model evicted from VRAM via Ollama keep_alive=0",
                )
            return UnloadResult(
                supported=False,
                reason=f"Ollama returned HTTP {resp.status_code} during unload",
            )
        except Exception as exc:
            logger.warning("Failed to unload model '%s': %s", model, exc)
            return UnloadResult(
                supported=False,
                reason=f"Unload exception: {str(exc)}",
            )

    async def list_models(self) -> List[Dict[str, Any]]:
        """Query /api/tags and extract candidate models with digests."""
        try:
            client = await self._get_client()
            r = await client.get("/api/tags", timeout=5.0)
            if r.status_code != 200:
                return []
            data = r.json()
            models_raw = data.get("models", [])
            discovered = []
            for m in models_raw:
                name = m.get("name", "")
                digest = m.get("digest", "")
                details = m.get("details", {})
                size_mb = m.get("size", 0) // (1024 * 1024)
                discovered.append({
                    "model": name,
                    "provider": self.provider_name,
                    "digest": digest,
                    "parameter_size": details.get("parameter_size"),
                    "quantization_level": details.get("quantization_level"),
                    "size_mb": size_mb,
                    "estimated_vram_mb": int(size_mb * 1.2) if size_mb > 0 else 4096,
                })
            return discovered
        except Exception as exc:
            logger.warning("Ollama /api/tags discovery failed: %s", exc)
            return []

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List[str]] = None,
        trace_id: str = "TRC-00000",
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute non-streaming text generation via local Ollama."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options
        if images:
            payload["images"] = images

        t0 = time.perf_counter()
        client = await self._get_client()
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        eval_count = data.get("eval_count", 0)
        eval_duration = data.get("eval_duration", 0)
        tokens_per_sec = (
            round((eval_count / (eval_duration / 1e9)), 1)
            if eval_duration > 0
            else None
        )

        return {
            "response": data.get("response", ""),
            "model": data.get("model", model),
            "provider": self.provider_name,
            "latency_ms": latency_ms,
            "tokens_generated": eval_count,
            "tokens_per_second": tokens_per_sec,
            "temperature": temperature or 0.7,
            "trace_id": trace_id,
            "done": data.get("done", True),
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = DEFAULT_MODEL,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_id: str = "TRC-00000",
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute chat completion via local Ollama."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        t0 = time.perf_counter()
        client = await self._get_client()
        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        msg = data.get("message", {})
        return {
            "message": msg,
            "response": msg.get("content", ""),
            "model": data.get("model", model),
            "provider": self.provider_name,
            "latency_ms": latency_ms,
            "tokens_generated": data.get("eval_count", 0),
            "trace_id": trace_id,
            "done": data.get("done", True),
        }

    async def stream_generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Stream generated text tokens from local Ollama."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system

        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        client = await self._get_client()
        async with client.stream("POST", "/api/generate", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    chunk = json.loads(line)
                    yield chunk.get("response", "")
                    if chunk.get("done", False):
                        break
