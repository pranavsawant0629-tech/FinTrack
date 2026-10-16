"""
Central service for the Finova AI Memory Layer.
Coordinates storage, deterministic extraction, validation, profile retrieval,
and lifecycle operations with graceful error degradation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from app.memory.extractor import MemoryExtractor, memory_extractor
from app.memory.interfaces import BaseMemoryStore
from app.memory.models import MemoryRecord, MemorySource, MemoryType, PersonalizationProfile
from app.memory.store import SQLiteMemoryStore
from app.memory.validator import MemoryValidationError, MemoryValidator, memory_validator

logger = logging.getLogger(__name__)


class MemoryService:
    """High-level service coordinating memory operations and orchestrator integration."""

    def __init__(
        self,
        store: BaseMemoryStore | None = None,
        validator: MemoryValidator | None = None,
        extractor: MemoryExtractor | None = None,
    ) -> None:
        self.store = store or SQLiteMemoryStore()
        self.validator = validator or memory_validator
        self.extractor = extractor or memory_extractor

    def retrieve_profile(self, user_id: str | None, current_query: str = "") -> PersonalizationProfile:
        """
        Retrieve active, unexpired user profile.
        If user_id is absent, returns an empty profile (ephemeral session mode).
        """
        if not user_id or not user_id.strip():
            return PersonalizationProfile(user_id=None)

        try:
            records = self.store.list_by_user(user_id.strip(), include_expired=False)
            profile = PersonalizationProfile(user_id=user_id.strip(), active_memories=records)

            for rec in records:
                if rec.memory_type == "LEARNING_LEVEL" and rec.key == "learning_level":
                    val = str(rec.value).lower()
                    if val in ("beginner", "intermediate", "advanced"):
                        profile.learning_level = cast(Any, val)
                elif rec.memory_type == "LEARNING_GOAL":
                    profile.learning_goals.append(str(rec.value))
                elif rec.memory_type == "INTEREST":
                    profile.interests.append(str(rec.value))
                elif rec.memory_type == "USER_PREFERENCE":
                    profile.preferences[rec.key] = str(rec.value)

            return profile
        except Exception as exc:
            logger.warning("Failed to retrieve memory profile for user '%s': %s", user_id, exc)
            return PersonalizationProfile(user_id=user_id.strip())

    def update_profile(
        self,
        user_id: str,
        learning_level: str | None = None,
        learning_goals: list[str] | None = None,
        interests: list[str] | None = None,
        preferences: dict[str, str] | None = None,
    ) -> PersonalizationProfile:
        """
        Atomically update a user's personalization profile in memory.db:
        - Upserts LEARNING_LEVEL (key: 'learning_level').
        - Reconciles LEARNING_GOAL items (adds new, removes deselected).
        - Reconciles INTEREST items (adds new, removes deselected).
        - Reconciles USER_PREFERENCE items.
        Returns the fresh updated PersonalizationProfile.
        """
        import re

        clean_user = user_id.strip()
        if not clean_user:
            raise MemoryValidationError("user_id must not be empty.")

        # 1. Learning Level
        if learning_level is not None:
            norm_level = learning_level.strip().lower()
            if norm_level in ("beginner", "intermediate", "advanced"):
                self.add_memory(
                    user_id=clean_user,
                    memory_type="LEARNING_LEVEL",
                    key="learning_level",
                    value=norm_level,
                )
            elif norm_level == "":
                existing_ll = self.store.get_by_key(clean_user, "LEARNING_LEVEL", "learning_level")
                if existing_ll:
                    self.store.delete(clean_user, existing_ll.memory_id)
            else:
                raise MemoryValidationError(f"Invalid learning_level: {learning_level}")

        # 2. Learning Goals
        if learning_goals is not None:
            existing_goals = self.store.list_by_user(clean_user, memory_type="LEARNING_GOAL")
            existing_vals = {str(r.value): r for r in existing_goals}
            target_vals = set(g.strip() for g in learning_goals if g.strip())

            # Delete deselected
            for val, rec in existing_vals.items():
                if val not in target_vals:
                    self.store.delete(clean_user, rec.memory_id)

            # Add new
            for goal in target_vals:
                if goal not in existing_vals:
                    slug = re.sub(r"[^a-zA-Z0-9_]", "_", goal.lower())[:32]
                    self.add_memory(
                        user_id=clean_user,
                        memory_type="LEARNING_GOAL",
                        key=f"goal_{slug}",
                        value=goal,
                    )

        # 3. Interests
        if interests is not None:
            existing_interests = self.store.list_by_user(clean_user, memory_type="INTEREST")
            existing_vals = {str(r.value): r for r in existing_interests}
            target_vals = set(i.strip() for i in interests if i.strip())

            # Delete deselected
            for val, rec in existing_vals.items():
                if val not in target_vals:
                    self.store.delete(clean_user, rec.memory_id)

            # Add new
            for item in target_vals:
                if item not in existing_vals:
                    slug = re.sub(r"[^a-zA-Z0-9_]", "_", item.lower())[:32]
                    self.add_memory(
                        user_id=clean_user,
                        memory_type="INTEREST",
                        key=f"interest_{slug}",
                        value=item,
                    )

        # 4. Preferences
        if preferences is not None:
            existing_prefs = self.store.list_by_user(clean_user, memory_type="USER_PREFERENCE")
            existing_pref_map = {r.key: r for r in existing_prefs}

            for pref_k, pref_v in preferences.items():
                clean_k = pref_k.strip()
                clean_v = pref_v.strip() if pref_v else ""
                if not clean_k:
                    continue
                if clean_v:
                    self.add_memory(
                        user_id=clean_user,
                        memory_type="USER_PREFERENCE",
                        key=clean_k,
                        value=clean_v,
                    )
                else:
                    if clean_k in existing_pref_map:
                        self.store.delete(clean_user, existing_pref_map[clean_k].memory_id)

        return self.retrieve_profile(clean_user)

    def process_and_save_candidates(self, user_id: str | None, query: str) -> list[MemoryRecord]:
        """
        Extract and persist memory candidates from explicit user statements.
        Strictly requires an explicit user_id; if absent, skips persistence.
        Guaranteed non-breaking via synchronous exception suppression.
        """
        if not user_id or not user_id.strip():
            return []

        clean_user = user_id.strip()
        saved_records: list[MemoryRecord] = []

        try:
            candidates = self.extractor.extract_candidates(query)
            if not candidates:
                return []

            existing_records = self.store.list_by_user(clean_user, include_expired=False)
            current_count = len(existing_records)
            existing_keys: set[tuple[str, str]] = {(str(r.memory_type), r.key) for r in existing_records}

            now_iso = datetime.now(timezone.utc).isoformat()

            for cand in candidates:
                cand_type_norm: str = cand.memory_type.upper() if isinstance(cand.memory_type, str) else str(cand.memory_type)
                is_update = (cand_type_norm, cand.key) in existing_keys
                is_valid, reason = self.validator.validate_candidate(
                    user_id=clean_user,
                    memory_type=cand.memory_type,
                    key=cand.key,
                    value=cand.value,
                    current_user_memory_count=current_count,
                    is_update=is_update,
                )
                if not is_valid:
                    logger.debug("Memory candidate '%s' rejected: %s", cand.key, reason)
                    continue

                record = MemoryRecord(
                    memory_id=str(uuid.uuid4()),
                    user_id=clean_user,
                    memory_type=cand.memory_type,
                    key=cand.key,
                    value=cand.value,
                    source="explicit_user_statement",
                    confidence=1.0,
                    created_at=now_iso,
                    updated_at=now_iso,
                )
                persisted = self.store.put(record)
                saved_records.append(persisted)
                if not is_update:
                    current_count += 1
                    existing_keys.add((cand_type_norm, cand.key))

            return saved_records
        except Exception as exc:
            logger.warning("Error processing memory candidates for user '%s': %s", clean_user, exc)
            return []

    def add_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        key: str,
        value: Any,
        source: MemorySource = "explicit_user_statement",
        expires_at: str | None = None,
    ) -> MemoryRecord:
        """Explicitly add or update a memory record (e.g. via REST API)."""
        clean_user = user_id.strip()
        existing = self.store.list_by_user(clean_user, include_expired=False)
        norm_type = memory_type.upper() if isinstance(memory_type, str) else memory_type
        is_update = any(r.memory_type == norm_type and r.key == key for r in existing)

        is_valid, reason = self.validator.validate_candidate(
            user_id=clean_user,
            memory_type=memory_type,
            key=key,
            value=value,
            current_user_memory_count=len(existing),
            is_update=is_update,
        )
        if not is_valid:
            raise MemoryValidationError(reason or "Memory validation failed.")

        now_iso = datetime.now(timezone.utc).isoformat()
        record = MemoryRecord(
            memory_id=str(uuid.uuid4()),
            user_id=clean_user,
            memory_type=memory_type,
            key=key,
            value=value,
            source=source,
            confidence=1.0,
            created_at=now_iso,
            updated_at=now_iso,
            expires_at=expires_at,
        )
        return self.store.put(record)

    def get_memories(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
        include_expired: bool = False,
    ) -> list[MemoryRecord]:
        """List active memories for user_id."""
        return self.store.list_by_user(
            user_id=user_id.strip(),
            memory_type=memory_type,
            include_expired=include_expired,
        )

    def get_user_memories(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
        include_expired: bool = False,
    ) -> list[MemoryRecord]:
        """Convenience alias for get_memories."""
        return self.get_memories(user_id=user_id, memory_type=memory_type, include_expired=include_expired)

    def create_explicit_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        key: str,
        value: Any,
        confidence: float = 1.0,
        ttl_seconds: int | None = None,
        source: MemorySource = "explicit_user_statement",
    ) -> MemoryRecord:
        """Convenience method to add explicit memory with optional TTL."""
        from datetime import timedelta
        expires_at = None
        if ttl_seconds is not None and ttl_seconds > 0:
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        return self.add_memory(
            user_id=user_id,
            memory_type=memory_type,
            key=key,
            value=value,
            source=source,
            expires_at=expires_at,
        )

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a single memory record belonging to user_id."""
        return self.store.delete(user_id=user_id.strip(), memory_id=memory_id.strip())

    def clear_user_memory(self, user_id: str) -> int:
        """Clear all memories for user_id (Right to be Forgotten)."""
        return self.store.clear_user(user_id=user_id.strip())

    def clear_user(self, user_id: str) -> int:
        """Convenience alias for clear_user_memory."""
        return self.clear_user_memory(user_id=user_id)


memory_service = MemoryService()
