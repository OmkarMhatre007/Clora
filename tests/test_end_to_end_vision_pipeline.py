"""
Phase 20, 21 & 22: Final End-to-End Multimodal Vision & Air-Gap Verification.
Validates the complete pipeline on flagship Pump P-101:
Ingestion -> SHA-256 -> Perception -> Validation -> Engineering Policy ->
Cross-Modal Corroboration -> Ed25519 Attestation -> Tamper Rejection -> Zero Internet.
"""

import json
import time
import pytest
from pathlib import Path

from backend.app.services.artifact_manager import default_artifact_manager
from backend.agents.vision_agent import MultimodalVisionAgent
from backend.verification.cross_correlation import CrossModalCorrelator
from security.attestation import get_attestor, EvidenceVerifier
from security.airgap_monitor import AirGapEnforcer, NetworkTrustProfile


@pytest.fixture(autouse=True)
def enforce_airgap():
    """Ensure strict offline air-gap enforcement during test execution."""
    AirGapEnforcer.activate(profile=NetworkTrustProfile.STRICT_AIRGAP)


def test_p101_flagship_end_to_end_pipeline():
    """
    Complete Phase 22 Definition of Done Test:
    User uploads P-101.jpg -> SHA-256 -> Proposal -> Validation -> Policy ->
    Evidence -> Telemetry -> SOP -> Correlation -> Claims -> Audit -> Ed25519.
    """
    fixture_path = Path("samples/vision_fixtures/p101_bearing.jpg")
    assert fixture_path.exists(), "P-101 fixture must exist"

    timings = {}

    # Stage 1: Ingestion & Fingerprinting
    t0 = time.perf_counter()
    record = default_artifact_manager.ingest_artifact(
        file_input=fixture_path,
        filename="p101_bearing.jpg",
        metadata={"scenario": "P101_BEARING_SPALLING"},
    )
    timings["ingestion_ms"] = (time.perf_counter() - t0) * 1000

    assert record.artifact_id.startswith("art_")
    assert record.content_hash == "c995c63f678792a2a16c01534ddcc5218ec163dd45e5273b7e50051898685493"
    assert record.mime_type == "image/jpeg"

    # Stage 2: Perception, Validation, and Engineering Policy Gate
    t1 = time.perf_counter()
    agent = MultimodalVisionAgent()
    telemetry = {
        "equipment_id": "P-101",
        "vibration_velocity_rms_mm_s": 9.82,
        "bearing_temperature_c": 104.2,
        "operating_hours": 14200,
    }
    insp_res = agent.inspect(
        artifact_id=record.artifact_id,
        image_path=record.storage_path,
        telemetry_context=telemetry,
        query="Inspect P-101 bearing for raceway degradation",
        execution_mode="test",
    )
    timings["vision_and_policy_ms"] = (time.perf_counter() - t1) * 1000

    # Invariants Verification
    assert "P-101" in insp_res.equipment_tag
    assert "SPALLING" in insp_res.defect_class.value
    assert insp_res.inspection_status.value in ["VERIFIED", "REQUIRES_REVIEW"]
    # Severity must be assigned by engineering policy, NOT raw VLM
    assert insp_res.severity.value in ["HIGH", "CRITICAL"]

    # Stage 3: Cross-Modal Correlation with Telemetry and Maintenance SOP
    t2 = time.perf_counter()
    sop_context = {
        "sop_id": "SOP-MRPL-P101-MNT",
        "title": "Sulzer P-101 Centrifugal Pump Bearing Inspection & Replacement SOP",
        "standard_ref": "ISO 10816-3 / API 610",
    }
    correlator = CrossModalCorrelator()
    cross_corr = correlator.correlate(
        visual_result=insp_res,
        telemetry_context=telemetry,
        sop_context=sop_context,
    )
    timings["cross_correlation_ms"] = (time.perf_counter() - t2) * 1000

    cc_dict = cross_corr.model_dump() if hasattr(cross_corr, "model_dump") else cross_corr
    assert cc_dict["visual_support"] is True
    assert cc_dict["telemetry_support"] is True
    assert cc_dict["sop_support"] is True
    assert cc_dict["corroboration"] in ["STRONG", "MODERATE"]

    # Stage 4: Local Ed25519 Cryptographic Evidence Attestation
    t3 = time.perf_counter()
    attestor = get_attestor()
    proof_package = attestor.sign_photograph_inspection(insp_res)
    timings["ed25519_attestation_ms"] = (time.perf_counter() - t3) * 1000

    assert proof_package["sealed"] is True
    assert proof_package["algorithm"] == "Ed25519"
    assert "signature" in proof_package

    # Stage 5: Independent Offline Verification
    is_valid, msg, details = EvidenceVerifier.verify_proof(proof_package)
    assert is_valid is True
    assert "VALID" in msg or "VERIFIED" in msg

    # Stage 6: Security & Tamper Detection Simulation
    tampered_package = json.loads(json.dumps(proof_package))
    tampered_package["canonical_payload"]["observation"] = "Bearing is in brand new pristine condition."
    tampered_valid, tampered_msg, _ = EvidenceVerifier.verify_proof(tampered_package)
    assert tampered_valid is False
    assert "MISMATCH" in tampered_msg or "INVALID" in tampered_msg

    total_pipeline_ms = sum(timings.values())
    print("\n" + "=" * 60)
    print("CLORA FLAGSHIP P-101 END-TO-END PIPELINE BENCHMARK")
    print("=" * 60)
    for stage, ms in timings.items():
        print(f"  {stage:<30}: {ms:>8.2f} ms")
    print("-" * 60)
    print(f"  {'Total Pipeline Latency':<30}: {total_pipeline_ms:>8.2f} ms")
    print("=" * 60)


def test_missing_image_production_rejection():
    """Verifies that missing image strictly yields INCONCLUSIVE in production mode (no synthetic fallback)."""
    agent = MultimodalVisionAgent()
    res = agent.inspect(
        artifact_id="art_nonexistent_image_123456",
        image_path="nonexistent/path/image.jpg",
        execution_mode="production",
    )
    assert res.inspection_status.value == "INCONCLUSIVE"
    assert res.severity.value in ["UNKNOWN", "NEGLIGIBLE"]
    assert "missing" in res.summary.lower()
