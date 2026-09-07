# ══════════════════════════════════════════════════════════════
# MUST BE FIRST — activate socket hooks before any library import
# ══════════════════════════════════════════════════════════════
import os
import platform
import socket
import subprocess
import sys
from typing import Any, Dict

from security.airgap_monitor import (
    AirGapEnforcer,
    AirGapViolationError,
    NetworkTrustProfile,
)

# Apply default strict airgap hook immediately upon Python process initialization
_DEFAULT_PROFILE = NetworkTrustProfile.STRICT_AIRGAP
AirGapEnforcer.activate(profile=_DEFAULT_PROFILE)

# ══════════════════════════════════════════════════════════════
# Subsequent Application Imports
# ══════════════════════════════════════════════════════════════
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.router import api_router
from backend.app.api.routes import health
from backend.app.core.config import settings
from backend.app.db import database
from backend.app.services.agent_service import recover_zombie_queries
from security.network_proof import get_sentinel, get_background_auditor, AirGapSentinel
from security.attestation import get_key_manager

logger = logging.getLogger("clora.backend.main")

# Set offline environment variables
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["OLLAMA_NO_CLOUD"] = "1"


def _check_linux_iptables_deny() -> Dict[str, Any]:
    """Checks whether Linux iptables has an outbound drop rule."""
    try:
        res = subprocess.run(["sudo", "iptables", "-S", "OUTPUT"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            is_blocked = ("CLORA_DENY_OUTBOUND" in res.stdout) or ("-P OUTPUT DROP" in res.stdout) or ("-j DROP" in res.stdout)
            return {
                "status": "PASS" if is_blocked else "NOT_FOUND",
                "label": "Linux iptables outbound deny rule",
                "note": "" if is_blocked else "No iptables OUTPUT drop rule detected. Run scripts/setup_firewall_rule.sh."
            }
    except Exception as e:
        return {"status": "CHECK_FAILED", "error": str(e)}
    return {"status": "NOT_FOUND", "label": "Linux iptables check could not verify"}


def _check_os_deny_rule() -> Dict[str, Any]:
    """
    Queries for the specific named outbound deny rule at the OS level (Layer 1 enforcement).
    Uses numeric Action enum (2 = Block) on Windows for locale independence.
    """
    os_name = platform.system()
    rule_name = getattr(settings, "AIRGAP_OS_DENY_RULE_NAME", "CLORA_DENY_OUTBOUND")

    if os_name == "Windows":
        try:
            ps_cmd = (
                f"$r = Get-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue; "
                "if ($r) { [int]$r.Action } else { -1 }"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=4
            )
            action_code = res.stdout.strip()
            # Action 2 is NET_FW_ACTION_BLOCK in Windows Firewall API
            is_blocked = (action_code == "2")
            return {
                "status": "PASS" if is_blocked else "NOT_FOUND",
                "label": f"OS outbound deny rule ({rule_name})",
                "details": f"PowerShell Action code: {action_code} (2=Block)",
                "note": "" if is_blocked else (
                    f"No active '{rule_name}' rule with Action=Block found. "
                    "Application instrumentation is active; enforce Layer 1 with: "
                    "powershell -ExecutionPolicy Bypass -File scripts/setup_firewall_rule.ps1"
                )
            }
        except Exception as e:
            return {"status": "CHECK_FAILED", "error": str(e)}

    elif os_name == "Linux":
        return _check_linux_iptables_deny()
    else:
        return {
            "status": "INFO",
            "label": f"OS {os_name} firewall verification skipped (development host)."
        }


class AirGapStartupValidator:
    """
    Executes honest, multi-layer validation at application startup:
    1. Behavioral hook self-test (Layer 2 instrumentation verification).
    2. OS-level outbound firewall rule check (Layer 1 enforcement verification).
    3. Ollama cloud feature isolation verification.
    4. Activation-order cleanliness check.
    """

    @staticmethod
    def run(sentinel: AirGapSentinel) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        # CHECK 1: Behavioral hook self-test (thread-isolated)
        hook_worked = False
        try:
            AirGapEnforcer.set_self_test_mode(True)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.settimeout(0.5)
                s.connect(("1.1.1.1", 443))
            except AirGapViolationError:
                hook_worked = True
            except Exception:
                hook_worked = False
            finally:
                s.close()
        finally:
            AirGapEnforcer.set_self_test_mode(False)

        results["hook_self_test"] = {
            "passed": hook_worked,
            "label": "Instrumentation logic check — confirms AirGapViolationError fires",
            "scope": "PYTHON_PROCESS_ONLY"
        }

        # CHECK 2: OS-level outbound deny rule
        results["os_firewall_rule"] = _check_os_deny_rule()

        # CHECK 3: Ollama cloud features disabled
        results["ollama_cloud_disabled"] = os.environ.get("OLLAMA_NO_CLOUD", "") == "1"

        # CHECK 4: HF offline flags
        results["hf_offline_flags"] = {
            "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE", "") == "1",
            "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE", "") == "1",
        }

        # CHECK 5: Activation order
        results["pre_activation_dns_clean"] = AirGapEnforcer.is_pre_activation_dns_clean()

        # Record SESSION_START in the SHA-256 hash chain
        sentinel.audit_cycle("SESSION_START", extra_metadata=results)
        return results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with strictly ordered security startup:
    1. Provisions physical storage directories.
    2. Initializes database schemas and recovers zombie queries.
    3. Verifies single-worker concurrency constraint for SSE stream.
    4. Executes synchronous startup validation STRICTLY BEFORE auditor thread spawns.
    5. Starts background network auditor daemon.
    """
    # 1. Ensure storage root exists
    ws_dir = settings.STORAGE_DIR / "workspaces"
    ws_dir.mkdir(parents=True, exist_ok=True)

    # 2. Initialize DB tables
    database.Base.metadata.create_all(bind=database.engine)

    # 3. Startup Sweep: Transition stuck queries from previous restarts into 'failed'
    db = database.SessionLocal()
    try:
        recover_zombie_queries(db)
    finally:
        db.close()

    # 4. SSE Single-Worker Assertion
    workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
    if workers > 1:
        logger.critical(
            "WEB_CONCURRENCY=%d detected. AirGap SSE in-memory stream requires single worker process. "
            "SSE route disabled with HTTP 503.", workers
        )
        app.state.sse_available = False
    else:
        app.state.sse_available = True

    # 5. Initialize Keys and Sentinel
    get_key_manager(str(settings.KEYS_DIR))
    sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))

    # Re-apply profile from settings if specified
    try:
        profile_enum = NetworkTrustProfile(settings.AIRGAP_PROFILE)
    except Exception:
        profile_enum = NetworkTrustProfile.STRICT_AIRGAP

    AirGapEnforcer.activate(
        profile=profile_enum,
        approved_cidrs=settings.AIRGAP_APPROVED_CIDRS,
        on_violation=lambda ip, port, prof, is_self_test=False: sentinel.log_violation(
            destination_ip=ip,
            destination_port=port,
            reason=f"Intercepted unapproved connection under {prof} policy.",
            is_self_test=is_self_test
        ),
    )

    # 6. Synchronous Startup Validation (runs STRICTLY BEFORE BackgroundNetworkAuditor starts)
    val_results = AirGapStartupValidator.run(sentinel)
    app.state.startup_validation = val_results
    app.state.sentinel = sentinel

    # 7. Start Background Network Auditor daemon AFTER validator completes
    auditor = get_background_auditor(interval_sec=settings.AIRGAP_AUDIT_INTERVAL_SEC)
    auditor.start()

    yield

    # Teardown: Stop auditor and deactivate enforcer
    auditor.stop()
    AirGapEnforcer.deactivate()


class AirGapHeaderMiddleware(BaseHTTPMiddleware):
    """Injects real-time AirGap profile and chain head hash into HTTP response headers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            sentinel = get_sentinel(str(settings.AIRGAP_LOG_PATH))
            current_hash = sentinel.get_current_hash()
            response.headers["X-AirGap-Profile"] = AirGapEnforcer.get_profile().value
            response.headers["X-AirGap-Hash"] = current_hash[:16]
        except Exception:
            pass
        return response


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title="INDUSAI-X Backend API",
        description="Industrial Intelligence Platform - Multi-Agent Orchestration & Persistence Spine",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach AirGap headers
    app.add_middleware(AirGapHeaderMiddleware)

    # Mount health checks
    app.include_router(health.router)

    # Mount core API endpoints under /api
    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
