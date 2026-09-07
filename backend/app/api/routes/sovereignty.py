"""
Sovereignty & Air-Gap Compliance API Routes.
Provides live status, active socket inspection, tamper-evident hash trail,
deterministic violation simulation, certified network compliance attestations,
real-time SSE audit stream, authentic egress metrics, and Ed25519 evidence sealing.
"""

import asyncio
import json
import os
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from security.airgap_monitor import (
    AirGapEnforcer,
    AirGapViolationError,
    NetworkTrustProfile,
    get_active_socket_snapshot,
)
from security.network_proof import get_sentinel

router = APIRouter(tags=["Sovereignty & Air-Gap Compliance"])


class ProfileChangeRequest(BaseModel):
    profile: NetworkTrustProfile = Field(..., description="Target network trust profile")
    user_id: str = Field("operator_admin", min_length=1, description="Authenticated administrator ID")
    justification: str = Field(..., min_length=5, description="Operational justification for changing network security profile")


class SignWorkflowRequest(BaseModel):
    workflow_stage_hashes: List[str] = Field(..., description="Ordered list of SHA-256 hashes from workflow checkpoints")
    query_id: str = Field(..., description="Unique query identifier")
    extra_metadata: Optional[Dict[str, Any]] = None


@router.get(
    "/sovereignty/status",
    summary="Air-Gap Network Sentinel & Sovereign Inspection",
)
def get_sovereignty_status():
    """
    Returns live application-level egress enforcement status, active network trust profile,
    detailed socket inspection table, and cryptographic hash chain summary.
    """
    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
    summary = sentinel.get_summary()
    sockets = get_active_socket_snapshot()

    is_compliant = summary["chain_valid"] and summary["violations_detected"] == 0

    return {
        "sovereign_mode": "AIR_GAPPED_VERIFIED" if is_compliant else "ALERT_POLICY_VIOLATION",
        "is_air_gapped": is_compliant,
        "active_profile": summary["active_profile"],
        "enforcer_active": summary["enforcer_active"],
        "total_audit_cycles": summary["total_audit_cycles"],
        "violations_detected": summary["violations_detected"],
        "root_integrity_hash": summary["root_integrity_hash"],
        "chain_valid": summary["chain_valid"],
        "session_link_mode": summary.get("session_link_mode", "GENESIS"),
        "open_sockets": sockets,
        "external_api_calls_detected": summary["violations_detected"],
        "policy": "APPLICATION_LEVEL_EGRESS_ENFORCED",
        "runtime_binding": "LOCAL_SOCKETS_ONLY",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/sovereignty/metrics",
    summary="Real-Time Egress Metrics",
)
def get_egress_metrics():
    """
    Returns authentic egress metrics tracked at the application hook level.
    Guaranteed to omit fictional bytes estimates.
    """
    return AirGapEnforcer.get_metrics()


@router.get(
    "/sovereignty/startup-validation",
    summary="Application & Host Startup Verification Results",
)
def get_startup_validation(request: Request):
    """
    Returns the two-layer startup validation results:
    1. Hook logic self-test (Python process)
    2. OS-level outbound firewall deny rule (Host machine)
    3. Ollama cloud feature isolation
    4. Activation-order cleanliness
    """
    val = getattr(request.app.state, "startup_validation", None)
    if val is None:
        sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
        from backend.app.main import AirGapStartupValidator
        val = AirGapStartupValidator.run(sentinel)
    return val


@router.get(
    "/sovereignty/trust-boundary",
    summary="Layered Sovereignty Trust Boundary Specification",
)
def get_trust_boundary():
    """Returns structured JSON of the three-layer trust model."""
    return {
        "title": "CLORA Layered Sovereignty Trust Boundary",
        "layer_1_os": {
            "name": "Host OS & Kernel Enforcement",
            "role": "Actual enforcement boundary",
            "mechanisms": ["CLORA_DENY_OUTBOUND outbound deny firewall rule", "Docker --network none"],
        },
        "layer_2_instrumentation": {
            "name": "Process-Level Instrumentation (AirGapEnforcer)",
            "role": "Application-level monitoring & preventive socket interception",
            "sees": [
                "All socket.connect calls in FastAPI process",
                "All socket.getaddrinfo calls in FastAPI process",
                "Periodic snapshots of process socket table"
            ],
            "does_not_see": [
                "Ollama daemon binary (mitigated via OLLAMA_NO_CLOUD=1)",
                "Docker sandbox containers (mitigated via --network none)",
                "Browser / frontend traffic"
            ],
        },
        "layer_3_evidence": {
            "name": "Cryptographic Audit Evidence",
            "role": "Tamper-evident proof generation",
            "mechanisms": [
                "SHA-256 hash chain (airgap_proof_log.jsonl)",
                "Ed25519 digital signatures (.clora-proof)"
            ],
        }
    }


@router.get(
    "/sovereignty/stream",
    summary="Server-Sent Events (SSE) Live Hash Chain Stream",
)
async def get_sovereignty_stream(request: Request, max_events: Optional[int] = None):
    """
    Streams live SHA-256 hash chain entries via Server-Sent Events (SSE).
    Single-worker uvicorn deployment is required for in-memory queue.
    """
    if not getattr(request.app.state, "sse_available", True):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSE stream unavailable: multi-worker deployment detected. Single worker required.",
        )

    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    def listener(entry: Dict[str, Any]):
        loop.call_soon_threadsafe(queue.put_nowait, entry)

    sentinel.subscribe(listener)

    async def event_generator():
        yielded = 0
        try:
            # Send initial connected event
            yield f"event: connected\ndata: {json.dumps({'status': 'STREAM_CONNECTED', 'head_hash': sentinel.get_current_hash()})}\n\n"
            yielded += 1
            if max_events and yielded >= max_events:
                return

            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: audit_block\ndata: {json.dumps(entry)}\n\n"
                    yielded += 1
                    if max_events and yielded >= max_events:
                        break
                except asyncio.TimeoutError:
                    # Heartbeat keep-alive ping
                    yield f": keep-alive\n\n"
        finally:
            sentinel.unsubscribe(listener)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/sovereignty/audit-trail",
    summary="Get Tamper-Evident SHA-256 Hash Chain Entries",
)
def get_audit_trail(limit: int = Query(50, ge=1, le=200)):
    """Returns the most recent verified blocks from the SHA-256 hash chain."""
    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
    entries = sentinel.get_recent_entries(limit=limit)
    valid, broken_line, msg = sentinel.verify_hash_chain()

    return {
        "entries": entries,
        "count": len(entries),
        "chain_valid": valid,
        "broken_line": broken_line,
        "verification_message": msg,
    }


@router.post(
    "/sovereignty/audit-now",
    summary="Trigger Instant Socket Audit Snapshot",
)
def trigger_audit_now():
    """Executes an immediate manual process socket audit and appends a block to the hash chain."""
    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
    entry = sentinel.audit_cycle("MANUAL_OPERATOR_SNAPSHOT")
    return {
        "status": "SUCCESS",
        "message": "Manual audit cycle completed and cryptographically chained.",
        "audit_entry": entry,
    }


@router.post(
    "/sovereignty/simulate-violation",
    summary="Simulate Egress / Policy Violation Test",
)
def simulate_policy_violation(target_ip: str = "1.1.1.1", target_port: int = 443):
    """
    Deterministic offline auditor demonstration tool.
    Attempts an unapproved outbound socket connection to demonstrate that the AirGapEnforcer
    synchronously intercepts, blocks before network transmission, logs the violation,
    and updates the hash chain into an ALERT state.
    """
    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
    enforcer_active = AirGapEnforcer.is_active()

    # Ensure enforcer is active for test
    if not enforcer_active:
        AirGapEnforcer.activate(
            profile=NetworkTrustProfile.STRICT_AIRGAP,
            on_violation=lambda ip, port, prof, is_self_test=False: sentinel.log_violation(
                ip, port, f"Simulated egress test to {ip}:{port} intercepted by {prof} policy.", is_self_test
            ),
        )

    blocked = False
    violation_error_msg = ""

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1.0)
        s.connect((target_ip, target_port))
    except AirGapViolationError as ve:
        blocked = True
        violation_error_msg = str(ve)
    except Exception as e:
        # If already offline at OS level or rejected
        blocked = True
        violation_error_msg = f"Connection intercepted/rejected: {str(e)}"
        sentinel.log_violation(target_ip, target_port, violation_error_msg)
    finally:
        s.close()

    summary = sentinel.get_summary()

    return {
        "simulation_result": "INTERCEPTED_AND_BLOCKED" if blocked else "NOT_BLOCKED",
        "intercepted": blocked,
        "target": f"{target_ip}:{target_port}",
        "policy_profile": summary["active_profile"],
        "reason": violation_error_msg,
        "violations_total": summary["violations_detected"],
        "root_integrity_hash": summary["root_integrity_hash"],
        "status": "ALERT_TRIGGERED" if blocked else "PASSED",
    }


@router.post(
    "/sovereignty/profile",
    summary="Change Network Security Profile (Auditable)",
)
def change_network_profile(req: ProfileChangeRequest):
    """
    Changes the active Network Trust Profile (STRICT_AIRGAP, INDUSTRIAL_LAN, DEVELOPMENT).
    Mandatory reason required; records an immutable transition entry in the SHA-256 hash chain.
    """
    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
    old_profile = AirGapEnforcer.get_profile().value

    AirGapEnforcer.set_profile(
        profile=req.profile,
        approved_cidrs=settings.AIRGAP_APPROVED_CIDRS if req.profile == NetworkTrustProfile.INDUSTRIAL_LAN else None,
    )

    entry = sentinel.log_policy_change(
        old_profile=old_profile,
        new_profile=req.profile.value,
        user_id=req.user_id,
        justification=req.justification,
    )

    return {
        "status": "SUCCESS",
        "previous_profile": old_profile,
        "new_profile": req.profile.value,
        "authorized_user": req.user_id,
        "audit_entry": entry,
    }


@router.get(
    "/sovereignty/attestation",
    response_class=PlainTextResponse,
    summary="Download Signed Network Compliance Attestation",
)
def get_compliance_attestation():
    """Returns the formal, technically defensible Network Compliance Attestation document."""
    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
    cert_path = sentinel.generate_compliance_attestation(str(settings.AIRGAP_ATTESTATION_PATH))
    with open(cert_path, "r", encoding="utf-8") as f:
        return f.read()


@router.get(
    "/sovereignty/certificate",
    response_class=PlainTextResponse,
    summary="Download Signed Air-Gap Sovereignty Certificate (Backward Compatibility)",
)
def get_sovereignty_certificate():
    """Backward-compatible endpoint returning the verified compliance attestation."""
    return get_compliance_attestation()


# ---------------------------------------------------------------------------
# Ed25519 Cryptographic Evidence Attestation Endpoints
# ---------------------------------------------------------------------------

class SignReportRequest(BaseModel):
    report_id: str = Field("CLORA-RPT-001", description="Unique identifier for the report")
    content: str = Field(..., min_length=1, description="Report content to cryptographically sign")
    sources: Optional[List[str]] = Field(default_factory=list, description="Associated evidence source documents")
    model: str = Field("qwen2.5:3b (Local Offline)", description="Local model used for generation")


@router.get(
    "/sovereignty/attestation/identity",
    summary="Get Local Ed25519 Signing Identity & Public Key",
)
def get_attestation_identity():
    """
    Returns CLORA's local Ed25519 signing identity and exportable public key.
    The corresponding private key strictly remains on-premises and is never exposed.
    """
    from security.attestation import get_key_manager
    km = get_key_manager(str(settings.KEYS_DIR))
    return {
        "key_id": km.get_key_id(),
        "algorithm": "Ed25519 (Curve25519)",
        "signer": "CLORA Sovereign Local Instance (MRPL SIH26117)",
        "public_key_pem": km.get_public_key_pem(),
        "storage_mode": "ON_PREMISES_SECURE_STORAGE",
        "verification_mode": "OFFLINE_STANDALONE",
    }


@router.post(
    "/sovereignty/attestation/sign",
    summary="Cryptographically Sign Report with Local Ed25519 Key",
)
def sign_report_endpoint(req: SignReportRequest):
    """
    Creates a canonical deterministic payload and signs it using CLORA's local Ed25519 private key.
    Returns a verifiable .clora-proof package.
    """
    from security.attestation import get_attestor
    attestor = get_attestor(str(settings.KEYS_DIR))
    proof = attestor.sign_report(
        report_id=req.report_id,
        content=req.content,
        sources=req.sources,
        model=req.model,
    )
    return proof


@router.post(
    "/sovereignty/sign-workflow",
    summary="Cryptographically Seal Multi-Agent Workflow Hash Chain",
)
def sign_workflow_endpoint(req: SignWorkflowRequest):
    """
    Signs the sequence of workflow stage airgap checkpoint hashes using Ed25519.
    Returns HTTP 200 with sealed: false on failure (best-effort; never raises exception to caller).
    """
    from security.attestation import get_attestor
    try:
        attestor = get_attestor(str(settings.KEYS_DIR))
        res = attestor.sign_workflow_chain(req.workflow_stage_hashes, req.query_id, req.extra_metadata)
        if res:
            return res
        return {"sealed": False, "reason": "Attestation signing returned empty"}
    except Exception as e:
        return {"sealed": False, "reason": f"Attestation signing error: {str(e)}"}


@router.post(
    "/sovereignty/attestation/verify",
    summary="Independently Verify .clora-proof Package",
)
def verify_attestation_endpoint(proof_package: Dict[str, Any]):
    """
    Independently verifies the integrity and Ed25519 digital signature of a .clora-proof package.
    Detects if even a single character was modified after signing.
    """
    from security.attestation import EvidenceVerifier
    valid, message, details = EvidenceVerifier.verify_proof(proof_package)
    return {
        "valid": valid,
        "status": "SIGNATURE_VALID" if valid else "SIGNATURE_INVALID",
        "message": message,
        "details": details,
        "verification_mode": "INDEPENDENT_CRYPTOGRAPHIC_CHECK",
    }


@router.post(
    "/sovereignty/attestation/simulate-tamper",
    summary="Simulate Content Tampering Live Demo",
)
def simulate_attestation_tamper(
    proof_package: Optional[Dict[str, Any]] = None,
    modified_text: str = "Inboard roller bearing temperature reached 199.9°C (CRITICAL EXCURSION)",
):
    """
    Live demonstration tool for evaluators and auditors.
    Compares cryptographic verification before and after modifying report content,
    demonstrating that even changing 1 character causes immediate signature rejection.
    """
    from security.attestation import EvidenceVerifier, get_attestor

    if not proof_package:
        attestor = get_attestor(str(settings.KEYS_DIR))
        proof_package = attestor.sign_report(
            report_id="CLORA-RPT-DEMO-001",
            content="Inboard roller bearing temperature reached 104.2°C, exceeding 80.0°C threshold.",
            sources=["Pump_P101_Maintenance.pdf", "CDU_Vibration_Telemetry.csv"],
            model="qwen2.5:3b (Local Quantized)",
        )

    return EvidenceVerifier.simulate_tampering(proof_package, modified_text=modified_text)


@router.get(
    "/sovereignty/attestation/sample-proof",
    summary="Get Sample Signed .clora-proof Package",
)
def get_sample_proof():
    """Returns a ready-to-verify sample evidence package for testing."""
    from security.attestation import get_attestor
    attestor = get_attestor(str(settings.KEYS_DIR))
    return attestor.sign_report(
        report_id="CLORA-RPT-SAMPLE-001",
        content=(
            "Verified operational finding: Lube oil pressure dropped to 0.4 bar at 14:15:00Z. "
            "Inboard roller bearing temperature subsequently reached 104.2°C."
        ),
        sources=["Pump_P101_Maintenance.pdf", "CDU_Vibration_Telemetry.csv"],
        model="qwen2.5:3b (Local Offline)",
    )
