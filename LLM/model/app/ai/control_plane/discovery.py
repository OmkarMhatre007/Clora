"""
Discovery Manager & Candidate Model Stager for CLORA Sovereign Model Control Plane.
Implements TTL caching against DoS, extracts runtime digests, and enforces candidate staging.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, List, Optional

from app.ai.control_plane.catalog import ModelCatalog
from app.ai.control_plane.models import ModelStatus

logger = logging.getLogger("indusai.discovery")


class DiscoveryManager:
    """
    Scans local inference runtimes (e.g. Ollama tags) for candidate models.
    Staged models are strictly flagged PENDING_APPROVAL and never automatically activated.
    """

    def __init__(self, catalog: ModelCatalog, cache_ttl_seconds: int = 30):
        self.catalog = catalog
        self.cache_ttl = cache_ttl_seconds
        self._last_scan_time: float = 0.0
        self._cached_results: List[Dict[str, Any]] = []

    async def discover_candidates(self, providers: Dict[str, Any], force: bool = False) -> List[Dict[str, Any]]:
        """
        Scan all registered providers for available models.
        Returns cached list if called within TTL window unless force=True.
        """
        now = time.time()
        if not force and (now - self._last_scan_time < self.cache_ttl) and self._cached_results:
            logger.debug("Returning cached model discovery results (%ds old)", int(now - self._last_scan_time))
            return self._cached_results

        all_discovered = []
        for prov_name, provider in providers.items():
            if not hasattr(provider, "list_models"):
                continue
            try:
                models = await provider.list_models()
                for item in models:
                    model_name = item.get("model", "")
                    digest = item.get("digest")
                    canonical_id = f"{prov_name}/{model_name}"

                    existing = self.catalog.get_model(canonical_id)
                    if not existing:
                        # Stage as PENDING_APPROVAL
                        self.catalog.register_candidate(
                            provider=prov_name,
                            model=model_name,
                            digest=digest,
                            label=f"{model_name} (Discovered)",
                            context_length=8192,
                            estimated_vram_mb=item.get("estimated_vram_mb", 4096),
                            status=ModelStatus.PENDING_APPROVAL,
                        )
                        status_str = ModelStatus.PENDING_APPROVAL.value
                    else:
                        status_str = existing.get("status", ModelStatus.DISCOVERED.value)
                        # Check digest drift
                        if digest and existing.get("digest") != digest:
                            self.catalog.set_model_digest(canonical_id, digest)
                            status_str = ModelStatus.ARTIFACT_CHANGED.value

                    all_discovered.append({
                        "canonical_id": canonical_id,
                        "provider": prov_name,
                        "model": model_name,
                        "digest": digest,
                        "status": status_str,
                        "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    })
            except Exception as exc:
                logger.warning("Discovery failed on provider '%s': %s", prov_name, exc)

        self._last_scan_time = now
        self._cached_results = all_discovered
        return all_discovered
