"""
Test AirGap startup self-test isolation and violation counter separation.
"""

import os
import socket
import pytest

from security.airgap_monitor import (
    AirGapEnforcer,
    AirGapViolationError,
    NetworkTrustProfile,
)
from security.network_proof import AirGapSentinel
from backend.app.main import AirGapStartupValidator


def test_startup_validator_does_not_increment_violation_count(tmp_path):
    """
    AirGapStartupValidator executes a behavioral hook self-test.
    The resulting block must be tagged SELF_TEST_EXPECTED_BLOCK and NOT increment violations_detected.
    """
    log_file = str(tmp_path / "test_self_test_log.jsonl")
    sentinel = AirGapSentinel(log_path=log_file)

    AirGapEnforcer.deactivate()
    AirGapEnforcer.activate(
        profile=NetworkTrustProfile.STRICT_AIRGAP,
        on_violation=lambda ip, port, prof, is_self_test=False: sentinel.log_violation(
            ip, port, "Test probe", is_self_test=is_self_test
        )
    )

    try:
        val_results = AirGapStartupValidator.run(sentinel)
        assert val_results["hook_self_test"]["passed"] is True

        summary = sentinel.get_summary()
        assert summary["violations_detected"] == 0

        entries = sentinel.get_recent_entries(10)
        stages = [e["stage"] for e in entries]
        assert "SELF_TEST_EXPECTED_BLOCK" in stages
        assert "SESSION_START" in stages
    finally:
        AirGapEnforcer.deactivate()


def test_violation_counter_increments_for_real_violation(tmp_path):
    """Confirm that non-self-test blocks DO increment the violation counter."""
    log_file = str(tmp_path / "test_real_violation_log.jsonl")
    sentinel = AirGapSentinel(log_path=log_file)

    AirGapEnforcer.deactivate()
    AirGapEnforcer.activate(
        profile=NetworkTrustProfile.STRICT_AIRGAP,
        on_violation=lambda ip, port, prof, is_self_test=False: sentinel.log_violation(
            ip, port, "Real probe", is_self_test=is_self_test
        )
    )

    try:
        # Non-self-test call
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("1.1.1.1", 443))
        except AirGapViolationError:
            pass
        finally:
            s.close()

        summary = sentinel.get_summary()
        assert summary["violations_detected"] == 1
    finally:
        AirGapEnforcer.deactivate()
