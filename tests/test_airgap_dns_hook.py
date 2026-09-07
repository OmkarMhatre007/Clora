"""
Test socket.getaddrinfo preventive DNS interception in AirGapEnforcer.
"""

import socket
import pytest

from security.airgap_monitor import (
    AirGapEnforcer,
    AirGapViolationError,
    NetworkTrustProfile,
)


def test_dns_hook_allows_localhost():
    """Localhost DNS resolution must be allowed under STRICT_AIRGAP."""
    AirGapEnforcer.deactivate()
    AirGapEnforcer.activate(profile=NetworkTrustProfile.STRICT_AIRGAP)
    try:
        # Loopback resolutions should succeed
        res = socket.getaddrinfo("localhost", 80)
        assert len(res) > 0

        res127 = socket.getaddrinfo("127.0.0.1", 8000)
        assert len(res127) > 0
    finally:
        AirGapEnforcer.deactivate()


def test_dns_hook_blocks_external_host():
    """External domain resolution must raise AirGapViolationError before network DNS handshake."""
    AirGapEnforcer.deactivate()
    AirGapEnforcer.activate(profile=NetworkTrustProfile.STRICT_AIRGAP)
    try:
        with pytest.raises(AirGapViolationError) as exc_info:
            socket.getaddrinfo("google.com", 443)

        assert "google.com" in str(exc_info.value) or exc_info.value.destination_ip == "google.com"
        assert exc_info.value.profile == NetworkTrustProfile.STRICT_AIRGAP.value
    finally:
        AirGapEnforcer.deactivate()
