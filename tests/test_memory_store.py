"""
Unit tests for the SQLiteMemoryStore and MemoryRecord lifecycle (app.memory.store).
Verifies CRUD, user isolation, deduplication/upsert, TTL expiration, and deletion.
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.memory.models import MemoryRecord
from app.memory.store import SQLiteMemoryStore


@pytest.fixture
def store():
    """Isolated in-memory SQLite store for unit testing."""
    s = SQLiteMemoryStore(db_path=":memory:")
    yield s
    s.close()


def test_memory_store_put_and_get(store: SQLiteMemoryStore):
    now_iso = datetime.now(timezone.utc).isoformat()
    record = MemoryRecord(
        memory_id="mem_1",
        user_id="user_alice",
        memory_type="LEARNING_LEVEL",
        key="learning_level",
        value="beginner",
        source="explicit_user_statement",
        created_at=now_iso,
        updated_at=now_iso,
    )

    persisted = store.put(record)
    assert persisted.memory_id == "mem_1"

    fetched = store.get(user_id="user_alice", memory_id="mem_1")
    assert fetched is not None
    assert fetched.user_id == "user_alice"
    assert fetched.key == "learning_level"
    assert fetched.value == "beginner"


def test_strict_user_isolation(store: SQLiteMemoryStore):
    """Verifies that User A's memory is completely inaccessible to User B."""
    now_iso = datetime.now(timezone.utc).isoformat()
    rec_alice = MemoryRecord(
        memory_id="mem_alice_1",
        user_id="user_alice",
        memory_type="LEARNING_GOAL",
        key="goal",
        value="options_trading",
        created_at=now_iso,
        updated_at=now_iso,
    )
    store.put(rec_alice)

    # User Bob tries to get Alice's memory by ID
    bob_attempt = store.get(user_id="user_bob", memory_id="mem_alice_1")
    assert bob_attempt is None

    # User Bob lists their memories
    bob_list = store.list_by_user(user_id="user_bob")
    assert len(bob_list) == 0

    # User Alice lists their memories
    alice_list = store.list_by_user(user_id="user_alice")
    assert len(alice_list) == 1
    assert alice_list[0].value == "options_trading"


def test_memory_deduplication_and_upsert(store: SQLiteMemoryStore):
    """Verifies that duplicate (user_id, memory_type, key) updates in place."""
    now_iso = datetime.now(timezone.utc).isoformat()
    rec1 = MemoryRecord(
        memory_id="mem_init",
        user_id="user_charlie",
        memory_type="LEARNING_LEVEL",
        key="learning_level",
        value="beginner",
        created_at=now_iso,
        updated_at=now_iso,
    )
    store.put(rec1)

    # Update to intermediate
    rec2 = MemoryRecord(
        memory_id="mem_new_id",
        user_id="user_charlie",
        memory_type="LEARNING_LEVEL",
        key="learning_level",
        value="intermediate",
        created_at=now_iso,
        updated_at=now_iso,
    )
    updated = store.put(rec2)

    # Must preserve stable memory_id and have single record
    assert updated.memory_id == "mem_init"
    assert updated.value == "intermediate"

    all_charlie = store.list_by_user(user_id="user_charlie")
    assert len(all_charlie) == 1
    assert all_charlie[0].value == "intermediate"


def test_memory_expiration_ttl(store: SQLiteMemoryStore):
    """Verifies that expired memories are filtered out from get and list."""
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(hours=1)).isoformat()
    future_time = (now + timedelta(hours=1)).isoformat()

    expired_rec = MemoryRecord(
        memory_id="mem_exp",
        user_id="user_david",
        memory_type="USER_PREFERENCE",
        key="temp_pref",
        value="bullet_points",
        created_at=expired_time,
        updated_at=expired_time,
        expires_at=expired_time,
    )
    store.put(expired_rec)

    active_rec = MemoryRecord(
        memory_id="mem_active",
        user_id="user_david",
        memory_type="USER_PREFERENCE",
        key="perm_pref",
        value="concise",
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        expires_at=future_time,
    )
    store.put(active_rec)

    # get() on expired record returns None
    assert store.get("user_david", "mem_exp") is None
    # get() on active record returns record
    assert store.get("user_david", "mem_active") is not None

    # list_by_user filters expired by default
    active_list = store.list_by_user("user_david")
    assert len(active_list) == 1
    assert active_list[0].memory_id == "mem_active"

    # include_expired returns both
    all_list = store.list_by_user("user_david", include_expired=True)
    assert len(all_list) == 2


def test_delete_and_clear_user_memory(store: SQLiteMemoryStore):
    """Verifies single deletion and full right-to-be-forgotten clearing."""
    now_iso = datetime.now(timezone.utc).isoformat()
    store.put(
        MemoryRecord(
            memory_id="m1",
            user_id="user_eve",
            memory_type="INTEREST",
            key="k1",
            value="crypto",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )
    store.put(
        MemoryRecord(
            memory_id="m2",
            user_id="user_eve",
            memory_type="INTEREST",
            key="k2",
            value="etfs",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )

    # Delete single
    deleted = store.delete("user_eve", "m1")
    assert deleted is True
    assert len(store.list_by_user("user_eve")) == 1

    # Clear user
    cleared_count = store.clear_user("user_eve")
    assert cleared_count == 1
    assert len(store.list_by_user("user_eve")) == 0


def test_memory_service_ephemeral_mode_when_user_id_none(store: SQLiteMemoryStore):
    """Verifies that user_id=None skips persistent reads and writes completely."""
    from app.memory.service import MemoryService

    svc = MemoryService(store=store)

    # Retrieval returns empty profile
    profile = svc.retrieve_profile(user_id=None)
    assert profile.user_id is None
    assert profile.learning_level is None
    assert profile.learning_goals == []

    # Processing candidates returns empty list and writes nothing
    saved = svc.process_and_save_candidates(user_id=None, query="I am a beginner and my goal is to learn options")
    assert saved == []
    assert len(store.list_by_user("default_user")) == 0


def test_memory_service_profile_assembly(store: SQLiteMemoryStore):
    """Verifies that MemoryService properly assembles PersonalizationProfile from explicit statements."""
    from app.memory.service import MemoryService

    svc = MemoryService(store=store)
    saved = svc.process_and_save_candidates(
        user_id="user_frank",
        query="I am a beginner and my goal is to learn options trading",
    )
    assert len(saved) >= 2

    profile = svc.retrieve_profile(user_id="user_frank")
    assert profile.user_id == "user_frank"
    assert profile.learning_level == "beginner"
    assert any("options trading" in g for g in profile.learning_goals)


def test_quota_allows_update_at_capacity(store: SQLiteMemoryStore):
    """
    Verifies quota enforcement:
    1. 49 memories + new key -> allowed
    2. 50 memories + new key -> rejected
    3. 50 memories + existing key update -> allowed
    4. existing key update still remains exactly one record
    """
    from app.memory.service import MemoryService
    from app.memory.validator import MemoryValidationError

    svc = MemoryService(store=store)
    user = "user_quota_test"

    # Seed 49 memories
    for i in range(49):
        svc.add_memory(user_id=user, memory_type="USER_PREFERENCE", key=f"pref_{i}", value=f"val_{i}")

    assert len(store.list_by_user(user)) == 49

    # 1. 49 memories + new key (50th) -> allowed
    svc.add_memory(user_id=user, memory_type="USER_PREFERENCE", key="pref_49", value="val_49")
    assert len(store.list_by_user(user)) == 50

    # 2. 50 memories + new key (51st) -> rejected
    with pytest.raises(MemoryValidationError, match="quota reached"):
        svc.add_memory(user_id=user, memory_type="USER_PREFERENCE", key="pref_new_51", value="val_51")
    assert len(store.list_by_user(user)) == 50

    # 3. 50 memories + existing key update -> allowed
    updated_rec = svc.add_memory(user_id=user, memory_type="USER_PREFERENCE", key="pref_0", value="updated_val_0")
    assert updated_rec.value == "updated_val_0"

    # 4. existing key update still remains exactly 50 records
    all_mems = store.list_by_user(user)
    assert len(all_mems) == 50
    rec_0 = next(r for r in all_mems if r.key == "pref_0")
    assert rec_0.value == "updated_val_0"

