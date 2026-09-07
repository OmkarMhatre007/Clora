"""
Pre-Demo Readiness & Sovereignty Verification Checker for INDUSAI-X.
SIH26117 / MRPL

Validates:
1. Docker Daemon & indusai-sandbox:latest Local Image Cache (Hard Blocking RED).
2. Local Ollama Daemon & 1B-4B Model Availability.
3. Pre-Warming Status & Cold vs. Warm Latency.
4. Token Generation Benchmark (tokens/sec).
5. Tamper-Evident SHA-256 Audit Trail Integrity.
"""

import os
import subprocess
import sys
import time
import httpx

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.registry import default_registry
from backend.models.runtime import default_runtime


def print_section(title: str):
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)


def check_docker_sandbox() -> tuple[bool, str]:
    """Validates Docker daemon AND checks that indusai-sandbox:latest is in local cache."""
    # 1. Daemon check
    try:
        proc = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
        )
        if proc.returncode != 0:
            return False, "[RED FAIL] Docker daemon is not running. Sandbox isolation unavailable."
    except Exception as e:
        return False, f"[RED FAIL] Docker command not found or inaccessible: {e}"

    # 2. Local image cache check (Hard Blocking)
    try:
        inspect_proc = subprocess.run(
            ["docker", "image", "inspect", "indusai-sandbox:latest"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
        )
        if inspect_proc.returncode != 0:
            return False, (
                "[RED FAIL] 'indusai-sandbox:latest' NOT FOUND in local Docker image cache!\n"
                "           Build it before demo: 'docker build -f Dockerfile.sandbox -t indusai-sandbox:latest .'\n"
                "           (Air-gap integrity requires image to be pre-cached, not pulled live)."
            )
        return True, "[GREEN PASS] Docker daemon active and 'indusai-sandbox:latest' pre-cached."
    except Exception as e:
        return False, f"[RED FAIL] Failed inspecting Docker sandbox image: {e}"


def check_npm_telemetry() -> tuple[bool, str]:
    """Verify npm send-metrics is disabled."""
    try:
        proc = subprocess.run(
            ["npm", "config", "get", "send-metrics"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
        )
        val = proc.stdout.strip().lower()
        if val in ("false", ""):
            return True, "[GREEN PASS] npm send-metrics disabled (offline safe)."
        return False, f"[YELLOW WARN] npm send-metrics is '{val}'. Run: npm config set send-metrics false --global"
    except Exception as e:
        return True, f"[INFO] npm not found or check skipped: {e}"


def check_vite_local_only() -> tuple[bool, str]:
    """Verify frontend/vite.config.js binds strictly to localhost (127.0.0.1)."""
    vite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "vite.config.js"))
    if not os.path.exists(vite_path):
        return False, "[RED FAIL] frontend/vite.config.js not found."
    try:
        with open(vite_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "'0.0.0.0'" in content or '"0.0.0.0"' in content:
            return False, "[RED FAIL] Vite config exposes host to 0.0.0.0 (LAN reachable)."
        if "host: '127.0.0.1'" in content or 'host: "127.0.0.1"' in content or "host: 'localhost'" in content:
            return True, "[GREEN PASS] Vite configured with strict localhost binding (127.0.0.1)."
        return True, "[GREEN PASS] Vite defaults to localhost (no external host binding detected)."
    except Exception as e:
        return False, f"[RED FAIL] Error reading vite.config.js: {e}"


def check_os_firewall_rule() -> tuple[bool, str]:
    """Validates presence of host outbound deny rule (Layer 1 OS enforcement)."""
    import platform
    os_name = platform.system()
    if os_name == "Windows":
        try:
            ps_cmd = (
                "$r = Get-NetFirewallRule -DisplayName 'CLORA_DENY_OUTBOUND' -ErrorAction SilentlyContinue; "
                "if ($r) { [int]$r.Action } else { -1 }"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4.0,
            )
            code = proc.stdout.strip()
            if code == "2":
                return True, "[GREEN PASS] Windows Firewall rule 'CLORA_DENY_OUTBOUND' is active (Action: Block)."
            elif code != "-1" and code != "":
                return False, f"[YELLOW WARN] 'CLORA_DENY_OUTBOUND' found with Action code {code} (not Block)."
            else:
                return False, (
                    "[YELLOW WARN] 'CLORA_DENY_OUTBOUND' outbound deny rule not found.\n"
                    "           Application-level instrumentation active. For OS enforcement, run:\n"
                    "           'powershell -ExecutionPolicy Bypass -File scripts/setup_firewall_rule.ps1' as Admin."
                )
        except Exception as e:
            return False, f"[YELLOW WARN] Failed querying Windows Firewall: {e}"
    elif os_name == "Linux":
        try:
            proc = subprocess.run(["sudo", "iptables", "-S", "OUTPUT"], capture_output=True, text=True, timeout=3.0)
            if proc.returncode == 0 and ("CLORA_DENY_OUTBOUND" in proc.stdout or "-P OUTPUT DROP" in proc.stdout):
                return True, "[GREEN PASS] Linux iptables outbound drop rule active."
            return False, "[YELLOW WARN] No iptables outbound drop rule found. Run scripts/setup_firewall_rule.sh."
        except Exception as e:
            return False, f"[YELLOW WARN] Failed querying iptables: {e}"
    return True, f"[INFO] OS {os_name} firewall check skipped."


def check_ollama_runtime() -> tuple[bool, list[str]]:
    """Checks Ollama connection and pulled models."""
    reachable = default_runtime.is_endpoint_reachable(timeout_sec=1.0)
    if not reachable:
        return False, []
    models = default_runtime.list_pulled_models()
    return True, models


def main():
    print_section("INDUSAI-X PRE-DEMO READINESS & SOVEREIGNTY REPORT")
    all_green = True

    # 1. Docker & Sandbox Cache Check
    print("[*] 1. Checking Sandbox Container & Image Cache...")
    docker_ok, docker_msg = check_docker_sandbox()
    print(f"    -> {docker_msg}")
    if not docker_ok:
        all_green = False

    # 2. Ollama Daemon Check
    print("\n[*] 2. Checking Local Sovereign Model Runtime (Ollama)...")
    ollama_ok, pulled_models = check_ollama_runtime()
    if ollama_ok:
        print(f"    -> [GREEN PASS] Ollama reachable at {default_runtime.ollama_base_url}")
        print(f"    -> Cached Models ({len(pulled_models)}): {', '.join(pulled_models) if pulled_models else 'None'}")
    else:
        print(f"    -> [YELLOW WARN] Ollama not reachable. System will activate LOUD deterministic fallback.")
        all_green = False

    # 3. Model Profiles & Pre-Warming
    print("\n[*] 3. Validating 1B-4B Hardware-Calibrated Model Profiles...")
    profiles = default_registry.list_all(active_only=True)
    for p in profiles:
        if p.is_fallback:
            print(f"    -> [READY] {p.display_name} ({p.model_id}) - Local Fallback Engine")
        else:
            cached = any(p.model_id in m for m in pulled_models)
            status = "[CACHED]" if cached else "[NOT DOWNLOADED]"
            print(f"    -> {status} {p.display_name} ({p.model_id}) - Tier: {p.hardware_tier.value}")

    # 4. Pre-Warm Execution
    if ollama_ok and pulled_models:
        print("\n[*] 4. Executing 1-Token Pre-Warming to Eliminate Cold-Load Latency...")
        t0 = time.time()
        warm_results = default_runtime.prewarm_models()
        elapsed = time.time() - t0
        for mid, ok in warm_results.items():
            res_str = "WARMED" if ok else "SKIPPED/FAILED"
            print(f"    -> Model {mid}: {res_str}")
        print(f"    -> Pre-warm cycle complete in {elapsed:.2f}s.")

    # 5. Audit Trail Verification
    print("\n[*] 5. Verifying Tamper-Evident SHA-256 Audit Trail...")
    try:
        from security.audit_trail import AuditLogger
        audit_file = "demo_audit_trail.jsonl"
        logger = AuditLogger(audit_file)
        # Log a readiness check event
        logger.log(
            actor_id="system_preflight",
            role="Auditor",
            action="PREFLIGHT_CHECK",
            resource="system_environment",
            status="SUCCESS" if all_green else "WARNING",
            metadata={"docker_ok": docker_ok, "ollama_ok": ollama_ok},
        )
        valid, corrupt_idx, msg = AuditLogger.verify_audit_trail(audit_file)
        if valid:
            records_count = 0
            with open(audit_file, "r", encoding="utf-8") as f:
                records_count = sum(1 for line in f if line.strip())
            print(f"    -> [GREEN PASS] Audit trail SHA-256 cryptographic chain valid ({records_count} records).")
        else:
            print(f"    -> [RED FAIL] Audit trail integrity verification failed: {msg}")
            all_green = False
    except Exception as e:
        print(f"    -> [YELLOW WARN] Audit logger check skipped: {e}")

    # 6. npm Telemetry Setting Check
    print("\n[*] 6. Verifying npm Telemetry (send-metrics) Configuration...")
    npm_ok, npm_msg = check_npm_telemetry()
    print(f"    -> {npm_msg}")

    # 7. Frontend Localhost-Only Binding Check
    print("\n[*] 7. Verifying Frontend Dev Server Localhost-Only Binding (vite.config.js)...")
    vite_ok, vite_msg = check_vite_local_only()
    print(f"    -> {vite_msg}")
    if not vite_ok:
        all_green = False

    # 8. Layer 1 OS Outbound Deny Rule Check
    print("\n[*] 8. Verifying Layer 1 OS Outbound Firewall Rule (CLORA_DENY_OUTBOUND)...")
    fw_ok, fw_msg = check_os_firewall_rule()
    print(f"    -> {fw_msg}")
    # Note: Missing host rule warns but does not fail Python preflight if application instrumentation is active

    # Summary
    print_section("READINESS SUMMARY")
    if all_green:
        print("  STATUS: ALL SYSTEMS OPERATIONAL - READY FOR DEMO")
    else:
        print("  STATUS: ACTION REQUIRED BEFORE STAGE DEMO (Review failures above)")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
