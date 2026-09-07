"""
SQLite-Backed Persistent Model Catalog & CAS State Repository for CLORA.
Implements WAL mode, operator policy superiority, crash recovery detection,
and atomic Compare-And-Swap (CAS) state machine transitions.
"""
from __future__ import annotations

import os
import json
import sqlite3
import logging
import time
from typing import Optional, Dict, Any, List, Tuple

from app.ai.control_plane.models import (
    ModelRef,
    ModelStatus,
    ProviderStatus,
    ProviderCapabilities,
)

logger = logging.getLogger("indusai.catalog")

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "model_control_plane.db",
)


class ModelCatalog:
    """
    SQLite persistent storage for models, providers, operator policies, and state.
    Guarantees state durability across server restarts.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        if self.db_path != ":memory:":
            dirname = os.path.dirname(self.db_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            self._shared_conn = None
        else:
            # Shared in-memory connection to retain tables across queries
            self._shared_conn = sqlite3.connect("file::memory:?cache=shared", uri=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            conn = sqlite3.connect("file::memory:?cache=shared", uri=True)
        else:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if not present and seed initial models/providers."""
        with self._get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS providers (
                name TEXT PRIMARY KEY,
                provider_type TEXT NOT NULL,
                base_url TEXT NOT NULL,
                status TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS models (
                canonical_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                digest TEXT,
                label TEXT NOT NULL,
                context_length INTEGER NOT NULL,
                estimated_vram_mb INTEGER NOT NULL,
                status TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                test_only INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_capabilities (
                canonical_id TEXT PRIMARY KEY,
                supports_tools INTEGER NOT NULL,
                supports_json INTEGER NOT NULL,
                supports_vision INTEGER NOT NULL,
                verified_tools INTEGER NOT NULL DEFAULT 0,
                verified_json INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(canonical_id) REFERENCES models(canonical_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS operator_policies (
                canonical_id TEXT PRIMARY KEY,
                max_context_length INTEGER,
                enforce_sovereignty INTEGER NOT NULL DEFAULT 1,
                require_human_approval INTEGER NOT NULL DEFAULT 0,
                policy_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(canonical_id) REFERENCES models(canonical_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS model_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                active_model TEXT NOT NULL,
                state TEXT NOT NULL,
                transition_id TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transitions (
                transition_id TEXT PRIMARY KEY,
                from_model TEXT NOT NULL,
                to_model TEXT NOT NULL,
                status TEXT NOT NULL,
                logs_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                finished_at TEXT
            );
            """)

            # Seed default providers if empty
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM providers;")
            if cur.fetchone()[0] == 0:
                now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                conn.executemany(
                    "INSERT INTO providers VALUES (?, ?, ?, ?, ?, ?);",
                    [
                        ("ollama", "ollama", "http://127.0.0.1:11434", ProviderStatus.HEALTHY.value, "{}", now),
                        ("mock", "mock", "mock://local", ProviderStatus.HEALTHY.value, "{}", now),
                    ],
                )

            # Seed default models if empty
            cur.execute("SELECT COUNT(*) FROM models;")
            if cur.fetchone()[0] == 0:
                now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                default_models = [
                    ("ollama/llama3.2:3b", "ollama", "llama3.2:3b", "sha256:llama32b001", "Llama 3.2 3B (Sovereign Primary)", 8192, 4096, ModelStatus.ACTIVE.value, 1, 0, now, now),
                    ("ollama/qwen2.5:3b", "ollama", "qwen2.5:3b", "sha256:qwen25b002", "Qwen 2.5 3B (Structured Reasoning)", 32768, 4500, ModelStatus.APPROVED.value, 0, 0, now, now),
                    ("ollama/phi3:mini", "ollama", "phi3:mini", "sha256:phi3mini003", "Phi-3 Mini (Fast Local Fallback)", 4096, 3000, ModelStatus.APPROVED.value, 0, 0, now, now),
                    ("ollama/moondream", "ollama", "moondream", "sha256:moondream004", "Moondream (Local Diagram/Vision)", 2048, 3500, ModelStatus.APPROVED.value, 0, 0, now, now),
                    ("mock/mock-sovereign", "mock", "mock-sovereign", "sha256:mock000000", "Mock Sovereign Engine (Unit Test Only)", 4096, 2048, ModelStatus.APPROVED.value, 0, 1, now, now),
                ]
                conn.executemany(
                    "INSERT INTO models VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                    default_models,
                )

                caps = [
                    ("ollama/llama3.2:3b", 1, 1, 0, 1, 1),
                    ("ollama/qwen2.5:3b", 1, 1, 0, 1, 1),
                    ("ollama/phi3:mini", 0, 1, 0, 0, 1),
                    ("ollama/moondream", 0, 0, 1, 0, 0),
                    ("mock/mock-sovereign", 1, 1, 1, 1, 1),
                ]
                conn.executemany(
                    "INSERT INTO model_capabilities VALUES (?, ?, ?, ?, ?, ?);",
                    caps,
                )

            # Seed state row if empty
            cur.execute("SELECT COUNT(*) FROM model_state;")
            if cur.fetchone()[0] == 0:
                now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                conn.execute(
                    "INSERT INTO model_state VALUES (1, ?, ?, NULL, ?);",
                    ("ollama/llama3.2:3b", ModelStatus.ACTIVE.value, now),
                )

    # --- CAS State Transitions ---

    def try_begin_transition(self, to_model: str, transition_id: str) -> bool:
        """
        Atomic Compare-And-Swap (CAS) state update.
        Allows transition ONLY if current state is in ('ACTIVE', 'ENABLED', 'DEGRADED').
        Returns True if transition acquired, False if another transition is active.
        """
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE model_state
                SET state = ?, transition_id = ?, updated_at = ?
                WHERE id = 1 AND state IN ('ACTIVE', 'ENABLED', 'DEGRADED');
                """,
                (ModelStatus.SWITCHING.value, transition_id, now),
            )
            acquired = (cur.rowcount == 1)
            if acquired:
                # Get current active model
                cur.execute("SELECT active_model FROM model_state WHERE id = 1;")
                from_model = cur.fetchone()[0]
                conn.execute(
                    "INSERT INTO transitions VALUES (?, ?, ?, ?, '[]', ?, NULL);",
                    (transition_id, from_model, to_model, ModelStatus.SWITCHING.value, now),
                )
            return acquired

    def finalize_transition(self, transition_id: str, new_active_model: str, final_status: ModelStatus, logs: List[str]) -> None:
        """Complete a transition transaction and set active model and final status."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE model_state
                SET active_model = ?, state = ?, transition_id = NULL, updated_at = ?
                WHERE id = 1;
                """,
                (new_active_model, final_status.value, now),
            )
            conn.execute(
                """
                UPDATE transitions
                SET status = ?, logs_json = ?, finished_at = ?
                WHERE transition_id = ?;
                """,
                (final_status.value, json.dumps(logs), now, transition_id),
            )

    def get_state(self) -> Dict[str, Any]:
        """Fetch current active model, state machine state, and active transition."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT active_model, state, transition_id, updated_at FROM model_state WHERE id = 1;").fetchone()
            if not row:
                return {"active_model": "ollama/llama3.2:3b", "state": ModelStatus.ACTIVE.value, "transition_id": None}
            return dict(row)

    def get_transition(self, transition_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM transitions WHERE transition_id = ?;", (transition_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["logs"] = json.loads(d.get("logs_json", "[]"))
            return d

    # --- Model Query with Operator Policy Superiority ---

    def get_model(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch model definition, resolving operator policy superiority.
        Configured operator policy always overrides raw discovered values.
        """
        with self._get_conn() as conn:
            query = """
            SELECT m.*, 
                   c.supports_tools, c.supports_json, c.supports_vision, c.verified_tools, c.verified_json,
                   p.max_context_length, p.enforce_sovereignty, p.require_human_approval, p.policy_json
            FROM models m
            LEFT JOIN model_capabilities c ON m.canonical_id = c.canonical_id
            LEFT JOIN operator_policies p ON m.canonical_id = p.canonical_id
            WHERE m.canonical_id = ? OR m.model = ?;
            """
            row = conn.execute(query, (canonical_id, canonical_id)).fetchone()
            if not row:
                return None

            d = dict(row)
            # Operator Policy Superiority: configured max context overrides discovered context
            effective_context = d.get("max_context_length") or d.get("context_length")
            d["effective_context_length"] = effective_context
            return d

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models with effective capabilities."""
        with self._get_conn() as conn:
            rows = conn.execute("""
            SELECT m.*, 
                   c.supports_tools, c.supports_json, c.supports_vision, c.verified_tools, c.verified_json,
                   p.max_context_length
            FROM models m
            LEFT JOIN model_capabilities c ON m.canonical_id = c.canonical_id
            LEFT JOIN operator_policies p ON m.canonical_id = p.canonical_id
            ORDER BY m.is_default DESC, m.created_at ASC;
            """).fetchall()

            result = []
            for r in rows:
                d = dict(r)
                d["effective_context_length"] = d.get("max_context_length") or d.get("context_length")
                result.append(d)
            return result

    def register_candidate(
        self,
        provider: str,
        model: str,
        digest: Optional[str] = None,
        label: Optional[str] = None,
        context_length: int = 8192,
        estimated_vram_mb: int = 4096,
        status: ModelStatus = ModelStatus.PENDING_APPROVAL,
    ) -> Dict[str, Any]:
        """Stage a new model candidate."""
        canonical_id = f"{provider}/{model}"
        label = label or f"{model} ({provider})"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO models
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?);
                """,
                (canonical_id, provider, model, digest, label, context_length, estimated_vram_mb, status.value, now, now),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO model_capabilities VALUES (?, 1, 1, 0, 0, 0);
                """,
                (canonical_id,),
            )
        return self.get_model(canonical_id) or {}

    def approve_model(self, canonical_id: str) -> bool:
        """Transition a model to APPROVED state."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE models
                SET status = ?, updated_at = ?
                WHERE canonical_id = ? OR model = ?;
                """,
                (ModelStatus.APPROVED.value, now, canonical_id, canonical_id),
            )
            return cur.rowcount > 0

    def revoke_model(self, canonical_id: str) -> bool:
        """Revoke authorization for a model (preserved in DB for audit trail)."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE models
                SET status = ?, updated_at = ?
                WHERE canonical_id = ? OR model = ?;
                """,
                (ModelStatus.REVOKED.value, now, canonical_id, canonical_id),
            )
            return cur.rowcount > 0

    def set_model_digest(self, canonical_id: str, new_digest: str) -> None:
        """Update model digest and check for artifact change demotion."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._get_conn() as conn:
            m = self.get_model(canonical_id)
            if not m:
                return
            old_digest = m.get("digest")
            if old_digest and old_digest != new_digest:
                logger.warning("Artifact digest mismatch for %s: %s -> %s. Demoting to ARTIFACT_CHANGED.", canonical_id, old_digest, new_digest)
                conn.execute(
                    "UPDATE models SET digest = ?, status = ?, updated_at = ? WHERE canonical_id = ?;",
                    (new_digest, ModelStatus.ARTIFACT_CHANGED.value, now, canonical_id),
                )
            else:
                conn.execute(
                    "UPDATE models SET digest = ?, updated_at = ? WHERE canonical_id = ?;",
                    (new_digest, now, canonical_id),
                )

    def check_crash_recovery(self) -> Optional[str]:
        """
        Detect if previous process crashed during a transition.
        Transitions state to RECOVERY_REQUIRED.
        """
        state = self.get_state()
        if state["state"] in (ModelStatus.SWITCHING.value,):
            logger.critical("Process restart detected mid-transition (id: %s). Marking RECOVERY_REQUIRED.", state["transition_id"])
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE model_state SET state = ?, updated_at = ? WHERE id = 1;",
                    (ModelStatus.RECOVERY_REQUIRED.value, now),
                )
            return state["active_model"]
        return None
