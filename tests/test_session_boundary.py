"""
Test AirGapSentinel session-boundary linking and corrupted log recovery.
"""

import json
import os
import time
import pytest

from security.network_proof import AirGapSentinel, GENESIS_HASH


def test_genesis_on_first_run(tmp_path):
    """First-ever run with nonexistent log initializes in GENESIS mode."""
    log_file = str(tmp_path / "fresh_chain.jsonl")
    sentinel = AirGapSentinel(log_path=log_file)
    assert sentinel._session_link_mode == "GENESIS"
    assert sentinel.get_current_hash() == GENESIS_HASH


def test_prior_session_linked(tmp_path):
    """Sequential run links to prior session entry hash."""
    log_file = str(tmp_path / "linked_chain.jsonl")
    s1 = AirGapSentinel(log_path=log_file)
    entry1 = s1.audit_cycle("SESSION_1_WORK")
    last_hash = entry1["entry_hash"]

    # Start session 2 pointing to same file
    s2 = AirGapSentinel(log_path=log_file)
    assert s2._session_link_mode == "PRIOR_SESSION_LINKED"
    assert s2.get_current_hash() == last_hash

    entry2 = s2.audit_cycle("SESSION_2_WORK")
    assert entry2["prev_hash"] == last_hash

    valid, broken, _ = s2.verify_hash_chain()
    assert valid is True
    assert broken == -1


def test_corrupted_log_rotates_aside_and_starts_fresh(tmp_path):
    """
    When prior log has invalid JSON or corrupt data:
    1. The corrupt file is rotated aside to .corrupted.<timestamp>.
    2. Sentinel sets PRIOR_SESSION_UNREADABLE mode.
    3. Sentinel starts a fresh, fully verifiable chain from GENESIS.
    """
    log_file = str(tmp_path / "corrupted_chain.jsonl")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("CORRUPTED_NON_JSON_LINE\n")

    s = AirGapSentinel(log_path=log_file)
    assert s._session_link_mode == "PRIOR_SESSION_UNREADABLE"
    assert s.get_current_hash() == GENESIS_HASH

    # The corrupted file was rotated aside
    parent_files = os.listdir(tmp_path)
    corrupted_backups = [f for f in parent_files if ".corrupted." in f]
    assert len(corrupted_backups) == 1

    # Writing new entries to the fresh file verifies cleanly
    s.audit_cycle("SESSION_START")
    valid, broken, _ = s.verify_hash_chain()
    assert valid is True
    assert broken == -1
