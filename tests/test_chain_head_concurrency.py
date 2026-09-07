"""
Test thread safety and torn-read prevention for AirGapSentinel chain head hash.
"""

import threading
import time
import pytest

from security.network_proof import AirGapSentinel


def test_concurrent_reads_during_writes(tmp_path):
    """50 reader threads calling get_current_hash() concurrently with 30 writes under single lock."""
    log_file = str(tmp_path / "test_concurrency_log.jsonl")
    sentinel = AirGapSentinel(log_path=log_file)
    read_results = []
    stop_event = threading.Event()

    def reader():
        while not stop_event.is_set():
            h = sentinel.get_current_hash()
            read_results.append(h)
            time.sleep(0.001)

    def writer():
        for i in range(25):
            sentinel.audit_cycle(f"CONCURRENT_WRITE_{i}")
            time.sleep(0.003)

    readers = [threading.Thread(target=reader, daemon=True) for _ in range(20)]
    writers = [threading.Thread(target=writer, daemon=True) for _ in range(2)]

    for r in readers:
        r.start()
    for w in writers:
        w.start()

    for w in writers:
        w.join(timeout=5.0)

    stop_event.set()
    for r in readers:
        r.join(timeout=1.0)

    assert len(read_results) > 50
    for h in read_results:
        assert isinstance(h, str)
        assert len(h) == 64, f"Torn read detected: length was {len(h)}, hash={h}"
