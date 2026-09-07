"""
Core Data Structures & Enums for CLORA Sovereign Model Control Plane.
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


class LifecycleAuthority(str, Enum):
    """Defines which entity owns model process/memory lifecycle."""
    CLORA = "clora"                        # CLORA owns subprocess
    PROVIDER = "provider"                  # Provider runtime owns lifecycle (e.g. Ollama keep_alive)
    EXTERNAL_ORCHESTRATOR = "orchestrator" # Externally managed server (e.g. static vLLM)


class MemoryConfidence(str, Enum):
    """Confidence level of GPU VRAM metrics."""
    UNKNOWN = "unknown"                    # No telemetry available
    ESTIMATED = "estimated"                # Advisory static estimate (conservative safety margin)
    MEASURED = "measured"                  # Verified by live GPU telemetry


class ModelStatus(str, Enum):
    """Lifecycle state machine for models in the control plane."""
    DISCOVERED = "DISCOVERED"              # Staged from runtime, unapproved
    PENDING_APPROVAL = "PENDING_APPROVAL"  # Waiting for authorized engineer sign-off
    APPROVED = "APPROVED"                  # Validated for production use
    ENABLED = "ENABLED"                    # Available for routing
    ACTIVE = "ACTIVE"                      # Currently serving requests
    SWITCHING = "SWITCHING"                # Transition in progress
    UNAVAILABLE = "UNAVAILABLE"            # Provider healthy, model missing from runtime
    FAILED = "FAILED"                      # Probe or execution error
    DEGRADED = "DEGRADED"                  # Running in reduced capability mode
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"# Node crashed during transition
    ARTIFACT_CHANGED = "ARTIFACT_CHANGED"  # Digest mismatch detected
    DISABLED = "DISABLED"                  # Manually deactivated
    REVOKED = "REVOKED"                    # Banned by security audit (preserved in audit log)


class ProviderStatus(str, Enum):
    """Live health state of an inference provider runtime."""
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ModelRef:
    """Canonical model reference with optional artifact cryptographic digest."""
    provider: str
    model: str
    digest: Optional[str] = None

    @property
    def canonical_id(self) -> str:
        return f"{self.provider}/{self.model}"

    @classmethod
    def from_string(cls, ref_str: str) -> ModelRef:
        """Parse 'provider/model' or 'provider/model@digest' or bare 'model'."""
        if "/" in ref_str:
            parts = ref_str.split("/", 1)
            prov = parts[0]
            rest = parts[1]
            if "@" in rest:
                m, d = rest.split("@", 1)
                return cls(provider=prov, model=m, digest=d)
            return cls(provider=prov, model=rest)
        return cls(provider="ollama", model=ref_str)


@dataclass
class UnloadResult:
    """Result of attempting to evict a model from VRAM."""
    supported: bool
    reason: str
    freed_vram_mb: Optional[int] = None


@dataclass
class ProviderCapabilities:
    """Declared and verified capability profile."""
    chat: bool = True
    completion: bool = True
    tools: Dict[str, bool] = field(default_factory=lambda: {"declared": False, "verified": False})
    structured_json: Dict[str, bool] = field(default_factory=lambda: {"declared": False, "verified": False})
    vision: bool = False
    streaming: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat": self.chat,
            "completion": self.completion,
            "tools": self.tools,
            "structured_json": self.structured_json,
            "vision": self.vision,
            "streaming": self.streaming,
        }


@dataclass
class TaskRequirements:
    """Workload contract requirements for routing an inference task."""
    needs_tools: bool = False
    needs_json: bool = False
    needs_vision: bool = False
    min_context: int = 4096


@dataclass
class ModelAdmissionDecision:
    """Structured audit record of an admission decision before model switch or inference."""
    allowed: bool
    model: str
    reason: str
    checks: Dict[str, bool]
    required_vram_mb: int
    available_vram_mb: int
    confidence: MemoryConfidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "model": self.model,
            "reason": self.reason,
            "checks": self.checks,
            "required_vram_mb": self.required_vram_mb,
            "available_vram_mb": self.available_vram_mb,
            "confidence": self.confidence.value,
        }


@dataclass
class ProbeResult:
    """Results from the 5-point contract probe."""
    success: bool
    latency_ms: float
    checks_passed: Dict[str, bool]
    error: Optional[str] = None
    observed_vram_mb: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "latency_ms": self.latency_ms,
            "checks_passed": self.checks_passed,
            "error": self.error,
            "observed_vram_mb": self.observed_vram_mb,
        }
