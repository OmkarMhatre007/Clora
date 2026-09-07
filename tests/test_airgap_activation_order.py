"""
Test Air-Gap Hook Activation Order with Subprocess Isolation.
Ensures that pre-activation imports of socket.getaddrinfo are accurately detected,
and that activation prior to imports is cleanly verified without sys.modules caching pollution.
"""

import os
import subprocess
import sys
import pytest


def test_activation_after_dns_import_raises_in_strict_mode():
    """
    Subprocess isolation: A module grabs a direct reference to unpatched socket.getaddrinfo
    BEFORE AirGapEnforcer.activate() runs with AIRGAP_STRICT_MODE=hard_fail.
    Must raise RuntimeError in the isolated subprocess naming the offending module.
    """
    code = (
        "import os\n"
        "os.environ['AIRGAP_STRICT_MODE'] = 'hard_fail'\n"
        "from socket import getaddrinfo\n"
        "import sys\n"
        "from security.airgap_monitor import AirGapEnforcer, NetworkTrustProfile\n"
        "try:\n"
        "    AirGapEnforcer.activate(profile=NetworkTrustProfile.STRICT_AIRGAP)\n"
        "    sys.exit(0)\n"
        "except RuntimeError as e:\n"
        "    print(f'CAUGHT_RUNTIME_ERROR: {e}', file=sys.stderr)\n"
        "    sys.exit(42)\n"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 42
    assert "imported direct reference to socket.getaddrinfo BEFORE activation" in res.stderr


def test_activation_first_is_clean_in_strict_mode():
    """
    Subprocess isolation: AirGapEnforcer.activate() executes FIRST.
    Subsequent imports must proceed with is_pre_activation_dns_clean() returning True.
    """
    code = (
        "import os, sys\n"
        "os.environ['AIRGAP_STRICT_MODE'] = 'hard_fail'\n"
        "from security.airgap_monitor import AirGapEnforcer, NetworkTrustProfile\n"
        "AirGapEnforcer.activate(profile=NetworkTrustProfile.STRICT_AIRGAP)\n"
        "import socket\n"
        "assert AirGapEnforcer.is_pre_activation_dns_clean(), 'Expected clean activation'\n"
        "sys.exit(0)\n"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, f"Subprocess failed with stderr: {res.stderr}"
