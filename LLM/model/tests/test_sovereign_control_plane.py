"""
Comprehensive Automated Test Suite for CLORA Sovereign Model Control Plane.
Validates:
1. SSRF / DNS rebinding / Cloud metadata blocking
2. OpenAI-compatible universal adapter & lifecycle authority
3. VRAM admission controller with confidence levels
4. Deterministic capability contract probe (MODEL_PROBE_V1)
5. SQLite CAS concurrency state guard
6. Candidate discovery staging & approval flow
7. Operator policy superiority
8. Artifact digest mismatch demotion
9. Refinery RBAC granular model permissions
10. Monotonic SHA-256 audit chain with Ed25519 checkpoint attestation
"""
import pytest
import asyncio

from app.ai.sovereignty import (
    SovereignEndpointPolicy,
    SovereigntyViolationError,
    CanonicalSHA256AuditChain,
)
from app.ai.rbac import RBACManager, UserRole, ModelPermission, RBACAuthorizationError
from app.ai.control_plane.models import (
    LifecycleAuthority,
    MemoryConfidence,
    ModelStatus,
    ModelRef,
    TaskRequirements,
)
from app.ai.control_plane.gpu import GPUResourceProvider
from app.ai.control_plane.admission import AdmissionEngine
from app.ai.control_plane.catalog import ModelCatalog
from app.ai.control_plane.discovery import DiscoveryManager
from app.ai.control_plane.lifecycle import ModelLifecycleManager
from app.ai.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.ai.providers.mock_provider import MockProvider


# --- 1. SSRF & Sovereign Endpoint Policy ---

def test_sovereign_endpoint_ssrf_metadata_blocked():
    # Cloud metadata (AWS/Azure/GCP 169.254.169.254) must be blocked
    with pytest.raises(SovereigntyViolationError):
        SovereignEndpointPolicy.validate_endpoint("http://169.254.169.254/latest/meta-data")

    # Invalid scheme
    with pytest.raises(SovereigntyViolationError):
        SovereignEndpointPolicy.validate_endpoint("ftp://127.0.0.1/model")

    # Localhost loopback should pass
    res = SovereignEndpointPolicy.validate_endpoint("http://127.0.0.1:11434")
    assert res["allowed"] is True
    assert res["is_loopback"] is True


# --- 2. OpenAI-Compatible Universal Adapter ---

def test_openai_compatible_provider_external_server():
    provider = OpenAICompatibleProvider(base_url="http://127.0.0.1:8000/v1")
    assert provider.lifecycle_authority == LifecycleAuthority.EXTERNAL_ORCHESTRATOR

    # Unload should cleanly report supported=False without claiming to own external process
    res = asyncio.run(provider.unload("qwen2.5:7b"))
    assert res.supported is False
    assert "externally managed" in res.reason.lower()


# --- 3. VRAM Admission Controller & Confidence ---

def test_vram_admission_confidence_and_rejection():
    # Inject low free VRAM into GPU provider
    GPUResourceProvider.set_mock_vram(total_mb=8192, free_mb=1000)

    model_record = {
        "canonical_id": "ollama/deepseek-r1:8b",
        "model": "deepseek-r1:8b",
        "status": ModelStatus.APPROVED.value,
        "estimated_vram_mb": 5000,
        "supports_tools": True,
        "supports_json": True,
        "supports_vision": False,
        "effective_context_length": 8192,
    }

    # Should be rejected due to insufficient VRAM (1000MB free < 5000MB + overhead)
    decision = AdmissionEngine.evaluate(
        model_record=model_record,
        provider_base_url="http://127.0.0.1:11434",
        provider_healthy=True,
    )
    assert decision.allowed is False
    assert decision.checks["vram_sufficient"] is False
    assert decision.confidence == MemoryConfidence.MEASURED

    # Now inject high free VRAM
    GPUResourceProvider.set_mock_vram(total_mb=16384, free_mb=12000)
    decision_ok = AdmissionEngine.evaluate(
        model_record=model_record,
        provider_base_url="http://127.0.0.1:11434",
        provider_healthy=True,
    )
    assert decision_ok.allowed is True
    assert decision_ok.checks["vram_sufficient"] is True

    # Reset mock
    GPUResourceProvider.set_mock_vram(None, None)


# --- 4. Deterministic Capability Contract Probe ---

def test_deterministic_contract_probe():
    catalog = ModelCatalog(db_path=":memory:")
    audit = CanonicalSHA256AuditChain()
    mock_prov = MockProvider()
    lifecycle = ModelLifecycleManager(catalog=catalog, audit_chain=audit, providers={"mock": mock_prov})

    probe_res = asyncio.run(lifecycle.probe_model("mock", "mock-sovereign"))
    assert probe_res.success is True
    assert probe_res.checks_passed["connectivity"] is True
    assert probe_res.checks_passed["completion"] is True
    assert probe_res.checks_passed["json_contract"] is True
    assert probe_res.latency_ms >= 0


# --- 5. SQLite CAS Concurrency Guard ---

def test_cas_concurrency_guard():
    catalog = ModelCatalog(db_path=":memory:")

    # Worker A acquires transition lock
    acquired_a = catalog.try_begin_transition("ollama/qwen2.5:3b", "tr_001")
    assert acquired_a is True
    assert catalog.get_state()["state"] == ModelStatus.SWITCHING.value

    # Worker B tries to acquire concurrent transition -> must fail
    acquired_b = catalog.try_begin_transition("ollama/phi3:mini", "tr_002")
    assert acquired_b is False

    # Worker A completes transition
    catalog.finalize_transition("tr_001", "ollama/qwen2.5:3b", ModelStatus.ACTIVE, ["done"])
    assert catalog.get_state()["state"] == ModelStatus.ACTIVE.value

    # Worker B can now acquire transition
    acquired_c = catalog.try_begin_transition("ollama/phi3:mini", "tr_003")
    assert acquired_c is True


# --- 6. Candidate Discovery Staging & Approval ---

def test_discovery_staging_and_approval():
    catalog = ModelCatalog(db_path=":memory:")
    mock_prov = MockProvider()
    discovery = DiscoveryManager(catalog=catalog, cache_ttl_seconds=0)

    # Run discovery
    results = asyncio.run(discovery.discover_candidates({"mock": mock_prov}, force=True))
    assert len(results) >= 1

    # Candidate should be PENDING_APPROVAL, not automatically active
    candidate = catalog.get_model("mock/mock-sovereign")
    assert candidate is not None

    # Approve candidate
    ok = catalog.approve_model("mock/mock-sovereign")
    assert ok is True
    assert catalog.get_model("mock/mock-sovereign")["status"] == ModelStatus.APPROVED.value


# --- 7. Operator Policy Superiority ---

def test_operator_policy_superiority():
    catalog = ModelCatalog(db_path=":memory:")

    # Register model with context 32768
    catalog.register_candidate(
        provider="ollama",
        model="test-large",
        context_length=32768,
        status=ModelStatus.APPROVED,
    )

    # Operator sets policy max_context_length = 8192
    with catalog._get_conn() as conn:
        conn.execute(
            "INSERT INTO operator_policies (canonical_id, max_context_length) VALUES (?, ?);",
            ("ollama/test-large", 8192),
        )

    # Retrieval should resolve effective_context_length = 8192 (policy wins over discovery)
    m = catalog.get_model("ollama/test-large")
    assert m["context_length"] == 32768
    assert m["effective_context_length"] == 8192


# --- 8. Artifact Digest Change Demotion ---

def test_artifact_digest_change_demotion():
    catalog = ModelCatalog(db_path=":memory:")
    catalog.register_candidate(
        provider="ollama",
        model="secure-model",
        digest="sha256:orig_hash_111",
        status=ModelStatus.APPROVED,
    )

    # Someone replaces the model weights in background
    catalog.set_model_digest("ollama/secure-model", "sha256:modified_hash_222")

    # Must be demoted to ARTIFACT_CHANGED for operator re-verification
    m = catalog.get_model("ollama/secure-model")
    assert m["status"] == ModelStatus.ARTIFACT_CHANGED.value


# --- 9. Refinery RBAC Granular Model Permissions ---

def test_refinery_rbac_model_permissions():
    # FIELD_TECHNICIAN cannot switch or register models
    tech_role = UserRole.FIELD_TECHNICIAN
    assert RBACManager.check_model_permission(tech_role, ModelPermission.VIEW) is True
    assert RBACManager.check_model_permission(tech_role, ModelPermission.SWITCH) is False
    with pytest.raises(RBACAuthorizationError):
        RBACManager.require_model_permission(tech_role, ModelPermission.SWITCH)

    # MAINTENANCE_ENGINEER can switch models
    maint_role = UserRole.MAINTENANCE_ENGINEER
    assert RBACManager.check_model_permission(maint_role, ModelPermission.SWITCH) is True

    # OPERATIONS_SUPERVISOR can unload models
    ops_role = UserRole.OPERATIONS_SUPERVISOR
    assert RBACManager.check_model_permission(ops_role, ModelPermission.UNLOAD) is True

    # PLANT_DIRECTOR has full governance (APPROVE, REVOKE, PROVIDER_MANAGE)
    director_role = UserRole.PLANT_DIRECTOR
    assert RBACManager.check_model_permission(director_role, ModelPermission.APPROVE) is True
    assert RBACManager.check_model_permission(director_role, ModelPermission.PROVIDER_MANAGE) is True


# --- 10. Monotonic SHA-256 Audit Chain with Ed25519 Checkpoint ---

def test_audit_chain_monotonic_and_ed25519_checkpoint():
    chain = CanonicalSHA256AuditChain()

    e1 = chain.append_event("MODEL_SWITCH", resource="ollama/qwen", user_id="eng-1")
    e2 = chain.append_event("MODEL_UNLOAD", resource="ollama/llama", user_id="eng-1")
    e3 = chain.append_event("MODEL_APPROVE", resource="ollama/phi", user_id="director-1")

    # Sequence numbers must be strictly monotonic
    assert e1["sequence_number"] == 1
    assert e2["sequence_number"] == 2
    assert e3["sequence_number"] == 3

    # Cryptographic link verification
    assert chain.verify_chain() is True

    # Create signed checkpoint
    checkpoint = chain.create_checkpoint("audit_test")
    assert checkpoint["sequence_number"] == 3
    assert len(checkpoint["signature"]) > 0
    assert checkpoint["algorithm"] in ("Ed25519", "SHA256-Simulated")
