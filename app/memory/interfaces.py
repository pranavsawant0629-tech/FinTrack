"""
Abstract storage interface for the Finova AI Memory Layer.
Enables pluggable memory backends (SQLite, Redis, Postgres, vector stores)
without modifying agents, routers, or business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from app.memory.models import MemoryRecord, MemoryType


class BaseMemoryStore(ABC):
    """Abstract contract for persistent, user-isolated memory storage."""

    @abstractmethod
    def put(self, record: MemoryRecord) -> MemoryRecord:
        """
        Persist or update a memory record.
        Must enforce deduplication on (user_id, memory_type, key).
        """
        pass

    @abstractmethod
    def get(self, user_id: str, memory_id: str) -> MemoryRecord | None:
        """Retrieve a specific memory record by user_id and memory_id."""
        pass

    @abstractmethod
    def get_by_key(self, user_id: str, memory_type: MemoryType, key: str) -> MemoryRecord | None:
        """Retrieve a specific memory record by user_id, memory_type, and key."""
        pass

    @abstractmethod
    def list_by_user(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
        include_expired: bool = False,
    ) -> list[MemoryRecord]:
        """List all active (unexpired) memories belonging exclusively to user_id."""
        pass

    @abstractmethod
    def delete(self, user_id: str, memory_id: str) -> bool:
        """Delete a single memory record belonging to user_id. Returns True if deleted."""
        pass

    @abstractmethod
    def clear_user(self, user_id: str) -> int:
        """
        Delete all memories for user_id (Right to be Forgotten).
        Returns the count of deleted records.
        """
        pass
