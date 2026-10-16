"""
SQLite-backed implementation of BaseMemoryStore using Python's standard library sqlite3.
Provides deterministic, ACID-compliant, user-isolated memory persistence
with zero external dependencies.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, cast

from app.memory.interfaces import BaseMemoryStore
from app.memory.models import MemoryRecord, MemorySource, MemoryType

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join("data", "memory.db")


class SQLiteMemoryStore(BaseMemoryStore):
    """
    Thread-safe SQLite storage engine for user memories.
    Supports in-memory mode (':memory:') for isolated unit tests.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()

        # Ensure directory exists if using a file path
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Create user_memories table and indexes if they do not exist."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memories (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    UNIQUE(user_id, memory_type, key)
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_memories_user_type
                ON user_memories (user_id, memory_type);
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_memories_user_expires
                ON user_memories (user_id, expires_at);
                """
            )

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        """Deserialize database row into a MemoryRecord."""
        raw_val = row["value"]
        try:
            val = json.loads(raw_val)
        except Exception:
            val = raw_val

        return MemoryRecord(
            memory_id=str(row["memory_id"]),
            user_id=str(row["user_id"]),
            memory_type=cast(MemoryType, row["memory_type"]),
            key=str(row["key"]),
            value=val,
            source=cast(MemorySource, row["source"]),
            confidence=float(row["confidence"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            expires_at=row["expires_at"],
        )

    def put(self, record: MemoryRecord) -> MemoryRecord:
        """
        Persist or update memory record.
        Enforces deduplication on (user_id, memory_type, key).
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        serialized_val = json.dumps(record.value) if not isinstance(record.value, str) else record.value

        with self._lock:
            cur = self._conn.cursor()
            # Check if record already exists for this (user_id, memory_type, key)
            cur.execute(
                """
                SELECT memory_id, created_at FROM user_memories
                WHERE user_id = ? AND memory_type = ? AND key = ?
                """,
                (record.user_id, record.memory_type, record.key),
            )
            existing = cur.fetchone()

            if existing:
                stable_id = str(existing["memory_id"])
                orig_created_at = str(existing["created_at"])
                cur.execute(
                    """
                    UPDATE user_memories
                    SET value = ?, source = ?, confidence = ?, updated_at = ?, expires_at = ?
                    WHERE user_id = ? AND memory_type = ? AND key = ?
                    """,
                    (
                        serialized_val,
                        record.source,
                        record.confidence,
                        now_iso,
                        record.expires_at,
                        record.user_id,
                        record.memory_type,
                        record.key,
                    ),
                )
                return MemoryRecord(
                    memory_id=stable_id,
                    user_id=record.user_id,
                    memory_type=record.memory_type,
                    key=record.key,
                    value=record.value,
                    source=record.source,
                    confidence=record.confidence,
                    created_at=orig_created_at,
                    updated_at=now_iso,
                    expires_at=record.expires_at,
                )
            else:
                cur.execute(
                    """
                    INSERT INTO user_memories (
                        memory_id, user_id, memory_type, key, value, source,
                        confidence, created_at, updated_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.memory_id,
                        record.user_id,
                        record.memory_type,
                        record.key,
                        serialized_val,
                        record.source,
                        record.confidence,
                        record.created_at,
                        now_iso,
                        record.expires_at,
                    ),
                )
                return record

    def get(self, user_id: str, memory_id: str) -> MemoryRecord | None:
        """Retrieve a specific memory record by user_id and memory_id."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM user_memories WHERE user_id = ? AND memory_id = ?",
                (user_id, memory_id),
            )
            row = cur.fetchone()
            if not row:
                return None

            rec = self._row_to_record(row)
            if rec.expires_at:
                now_iso = datetime.now(timezone.utc).isoformat()
                if rec.expires_at < now_iso:
                    return None
            return rec

    def get_by_key(self, user_id: str, memory_type: MemoryType, key: str) -> MemoryRecord | None:
        """Retrieve a memory record by user_id, memory_type, and key."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT * FROM user_memories
                WHERE user_id = ? AND memory_type = ? AND key = ?
                """,
                (user_id, memory_type, key),
            )
            row = cur.fetchone()
            if not row:
                return None

            rec = self._row_to_record(row)
            if rec.expires_at:
                now_iso = datetime.now(timezone.utc).isoformat()
                if rec.expires_at < now_iso:
                    return None
            return rec

    def list_by_user(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
        include_expired: bool = False,
    ) -> list[MemoryRecord]:
        """List active memories belonging to user_id, optionally filtered by type."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cur = self._conn.cursor()
            query_parts = ["SELECT * FROM user_memories WHERE user_id = ?"]
            params: list[Any] = [user_id]

            if memory_type:
                query_parts.append("AND memory_type = ?")
                params.append(memory_type)

            if not include_expired:
                query_parts.append("AND (expires_at IS NULL OR expires_at > ?)")
                params.append(now_iso)

            query_parts.append("ORDER BY created_at ASC")
            full_query = " ".join(query_parts)

            cur.execute(full_query, params)
            rows = cur.fetchall()
            return [self._row_to_record(r) for r in rows]

    def delete(self, user_id: str, memory_id: str) -> bool:
        """Delete a single memory record belonging to user_id."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "DELETE FROM user_memories WHERE user_id = ? AND memory_id = ?",
                (user_id, memory_id),
            )
            return cur.rowcount > 0

    def clear_user(self, user_id: str) -> int:
        """Delete all memories for user_id (Right to be Forgotten)."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
            return cur.rowcount

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            self._conn.close()
