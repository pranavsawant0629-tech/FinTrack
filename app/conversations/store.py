"""
SQLite-backed storage engine for persistent conversations and chat history in Finova AI.
Thread-safe, local-first, zero external dependencies, supporting ':memory:' for tests.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from app.conversations.models import (
    Conversation,
    ConversationSummary,
    Message,
)

logger = logging.getLogger(__name__)

DEFAULT_CONVERSATIONS_DB_PATH = os.path.join("data", "conversations.db")


def generate_conversation_title(first_message: str, max_length: int = 42) -> str:
    """
    Generate a deterministic, clean title from the first user message.
    Handles edge cases: empty strings, short messages, emojis, and non-Latin scripts (e.g. Devanagari).
    Does NOT invoke any LLM.
    """
    cleaned = first_message.strip()
    if not cleaned:
        return "New Conversation"

    # Collapse internal whitespace and newlines
    cleaned = " ".join(cleaned.split())

    # If within length, capitalize first char (if cased) and return
    if len(cleaned) <= max_length:
        if len(cleaned) == 1:
            return cleaned.upper()
        return cleaned[0].upper() + cleaned[1:]

    # Truncate at word boundary if feasible
    truncated = cleaned[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > 15:
        truncated = truncated[:last_space]

    final_str = truncated.strip() + "…"
    return final_str[0].upper() + final_str[1:]


class SQLiteConversationStore:
    """Thread-safe SQLite storage for conversations and messages."""

    def __init__(self, db_path: str = DEFAULT_CONVERSATIONS_DB_PATH) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()

        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )
        self._conn.row_factory = sqlite3.Row
        # Enable foreign key cascade deletion
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create conversations and messages tables and indices."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    domain TEXT DEFAULT 'general'
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
                ON conversations (user_id, updated_at DESC);
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'complete',
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_timestamp
                ON messages (conversation_id, timestamp ASC);
                """
            )

    def create_conversation(
        self,
        user_id: str,
        title: str | None = None,
        domain: str | None = "general",
        conversation_id: str | None = None,
    ) -> Conversation:
        """Create a new conversation record."""
        conv_id = conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        final_title = (title.strip() if title and title.strip() else "New Conversation")
        final_domain = domain or "general"

        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO conversations (conversation_id, user_id, title, created_at, updated_at, domain)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (conv_id, user_id, final_title, now, now, final_domain),
            )

        return Conversation(
            conversation_id=conv_id,
            user_id=user_id,
            title=final_title,
            created_at=now,
            updated_at=now,
            domain=final_domain,
        )

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Fetch a conversation by ID."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT conversation_id, user_id, title, created_at, updated_at, domain
                FROM conversations
                WHERE conversation_id = ?;
                """,
                (conversation_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Conversation(
                conversation_id=str(row["conversation_id"]),
                user_id=str(row["user_id"]),
                title=str(row["title"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                domain=row["domain"],
            )

    def list_conversations(self, user_id: str, domain: str | None = None) -> list[ConversationSummary]:
        """List all conversations for a user, optionally filtered by domain, ordered by most recently updated."""
        with self._lock:
            cur = self._conn.cursor()
            query = """
                SELECT c.conversation_id, c.user_id, c.title, c.created_at, c.updated_at, c.domain,
                       COUNT(m.message_id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE c.user_id = ?
            """
            params: list[Any] = [user_id]
            clean_domain = domain.strip().lower() if domain and domain.strip() else None
            if clean_domain and clean_domain != "all":
                query += " AND LOWER(c.domain) = ?"
                params.append(clean_domain)

            query += """
                GROUP BY c.conversation_id
                ORDER BY c.updated_at DESC;
            """
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            summaries: list[ConversationSummary] = []
            for r in rows:
                summaries.append(
                    ConversationSummary(
                        conversation_id=str(r["conversation_id"]),
                        user_id=str(r["user_id"]),
                        title=str(r["title"]),
                        created_at=str(r["created_at"]),
                        updated_at=str(r["updated_at"]),
                        domain=r["domain"],
                        message_count=int(r["message_count"]),
                    )
                )
            return summaries

    def update_title(self, conversation_id: str, title: str) -> Conversation | None:
        """Update conversation title deterministically and touch updated_at."""
        clean_title = title.strip()
        if not clean_title:
            return None
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE conversation_id = ?;
                """,
                (clean_title, now, conversation_id),
            )
            if cur.rowcount == 0:
                return None

        return self.get_conversation(conversation_id)

    def update_timestamp(self, conversation_id: str) -> None:
        """Touch updated_at timestamp on a conversation."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE conversation_id = ?;
                """,
                (now, conversation_id),
            )

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and cascade delete its messages."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                DELETE FROM conversations
                WHERE conversation_id = ?;
                """,
                (conversation_id,),
            )
            return cur.rowcount > 0

    def clear_user_conversations(self, user_id: str) -> int:
        """Delete all conversations and cascade messages for a user."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                DELETE FROM conversations
                WHERE user_id = ?;
                """,
                (user_id,),
            )
            return cur.rowcount

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        status: str = "complete",
        metadata: dict[str, Any] | None = None,
        message_id: str | None = None,
        timestamp: str | None = None,
    ) -> Message:
        """Persist a message into the conversation and update conversation updated_at."""
        msg_id = message_id or f"msg_{uuid.uuid4().hex[:12]}"
        now = timestamp or datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata) if metadata is not None else None

        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO messages (message_id, conversation_id, role, content, timestamp, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (msg_id, conversation_id, role, content, now, status, meta_json),
            )
            cur.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE conversation_id = ?;
                """,
                (now, conversation_id),
            )

        return Message(
            message_id=msg_id,
            conversation_id=conversation_id,
            role=cast(Any, role),
            content=content,
            timestamp=now,
            status=cast(Any, status),
            metadata=metadata,
        )

    def get_messages(self, conversation_id: str) -> list[Message]:
        """Fetch all messages for a conversation in chronological order."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT message_id, conversation_id, role, content, timestamp, status, metadata
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC;
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
            messages: list[Message] = []
            for r in rows:
                meta = None
                if r["metadata"]:
                    try:
                        meta = json.loads(r["metadata"])
                    except Exception:
                        meta = None
                messages.append(
                    Message(
                        message_id=str(r["message_id"]),
                        conversation_id=str(r["conversation_id"]),
                        role=cast(Any, r["role"]),
                        content=str(r["content"]),
                        timestamp=str(r["timestamp"]),
                        status=cast(Any, r["status"]),
                        metadata=meta,
                    )
                )
            return messages

    def get_bounded_history(self, conversation_id: str, max_turns: int = 6) -> list[dict[str, str]]:
        """
        Fetch the most recent completed messages bounded to max_turns
        for providing LLM context continuation.
        Excludes failed turns.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = ? AND status = 'complete'
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (conversation_id, max_turns),
            )
            rows = cur.fetchall()
            # Reverse because we fetched DESC
            history = [{"role": str(r["role"]), "content": str(r["content"])} for r in reversed(rows)]
            return history

    def close(self) -> None:
        """Close the underlying database connection."""
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass


conversation_store = SQLiteConversationStore()
