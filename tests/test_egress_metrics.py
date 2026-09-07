"""
Test authentic EgressMetrics tracking and regression guards against fictional metrics.
"""

import socket
import pytest

from security.airgap_monitor import (
    AirGapEnforcer,
    AirGapViolationError,
    EgressMetrics,
    NetworkTrustProfile,
)


def test_egress_metrics_schema_and_regression_guard():
    """
    Verifies that EgressMetrics contains real metrics:
    - blocked_attempts_count
    - approved_connections_count
    - blocked_destinations
    CRITICAL REGRESSION GUARD: Must NOT contain bytes_intercepted_estimate.
    """
    metrics = EgressMetrics()
    snapshot = metrics.snapshot()

    assert "blocked_attempts_count" in snapshot
    assert "approved_connections_count" in snapshot
    assert "blocked_destinations" in snapshot
    assert "bytes_intercepted_estimate" not in snapshot, "Regression: fictional bytes metric re-introduced!"


def test_egress_metrics_increment_on_block():
    """Simulating blocked connection increments blocked_attempts_count."""
    AirGapEnforcer.deactivate()
    AirGapEnforcer.activate(profile=NetworkTrustProfile.STRICT_AIRGAP)
    try:
        initial = AirGapEnforcer.get_metrics()["blocked_attempts_count"]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("1.1.1.1", 443))
        except AirGapViolationError:
            pass
        finally:
            s.close()

        updated = AirGapEnforcer.get_metrics()["blocked_attempts_count"]
        assert updated == initial + 1
        assert "bytes_intercepted_estimate" not in AirGapEnforcer.get_metrics()
    finally:
        AirGapEnforcer.deactivate()
