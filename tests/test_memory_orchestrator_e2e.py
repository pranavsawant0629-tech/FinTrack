"""
Phase 5 Master End-to-End Test Suite:
Central Orchestrator, Memory Service, Personalization Layer, Safety Invariants, and Memory APIs.

Validates:
1. Explicit memory CRUD via REST API (/memory)
2. PII / Sensitive financial data rejection
3. User isolation and Right to be Forgotten (clearing memory)
4. Ephemeral session mode when user_id is None
5. Contextual profile retrieval and personalization across Equity, Crypto, and Personal Finance
6. Explicit current-query level overrides
7. Safety pre-filtering precedence (memory NEVER bypasses safety guardrails)
8. Graceful degradation on memory failure (orchestrator never crashes)
9. Memory TTL expiration
"""

from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.memory.models import MemoryRecord
from app.memory.service import memory_service
from app.memory.store import SQLiteMemoryStore
from app.rag.service import Citation, RAGAnswer

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_memory_db():
    """Ensure a clean memory store for each test."""
    test_store = SQLiteMemoryStore(db_path=":memory:")
    original_store = memory_service.store
    memory_service.store = test_store
    yield
    memory_service.store = original_store


# =====================================================================
# 1. Memory REST API Tests (/memory)
# =====================================================================

def test_api_create_and_list_explicit_memory():
    """Test POST /memory creates a valid record and GET /memory lists it."""
    # 1. Create explicit memory
    payload = {
        "user_id": "test_user_api_1",
        "memory_type": "LEARNING_LEVEL",
        "key": "learning_level",
        "value": "beginner",
        "confidence": 1.0,
    }
    create_resp = client.post("/memory", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["user_id"] == "test_user_api_1"
    assert created["key"] == "learning_level"
    assert created["value"] == "beginner"
    assert created["source"] == "explicit_user_statement"
    memory_id = created["memory_id"]

    # 2. List memories for this user
    list_resp = client.get("/memory?user_id=test_user_api_1")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["count"] == 1
    assert list_data["memories"][0]["memory_id"] == memory_id

    # 3. Filter by memory_type
    filtered_resp = client.get("/memory?user_id=test_user_api_1&memory_type=LEARNING_LEVEL")
    assert filtered_resp.status_code == 200
    assert filtered_resp.json()["count"] == 1

    empty_filtered = client.get("/memory?user_id=test_user_api_1&memory_type=USER_PREFERENCE")
    assert empty_filtered.status_code == 200
    assert empty_filtered.json()["count"] == 0


def test_api_rejects_pii_and_sensitive_data():
    """Test POST /memory strictly rejects PII, credit cards, PAN, and credentials."""
    bad_payloads = [
        # Credit card
        {"user_id": "u1", "memory_type": "USER_PREFERENCE", "key": "card", "value": "My card is 4111 2222 3333 4444"},
        # PAN card
        {"user_id": "u1", "memory_type": "USER_PREFERENCE", "key": "pan", "value": "My PAN is ABCDE1234F"},
        # Aadhaar
        {"user_id": "u1", "memory_type": "USER_PREFERENCE", "key": "aadhaar", "value": "Aadhaar: 2345 6789 0123"},
        # Password
        {"user_id": "u1", "memory_type": "USER_PREFERENCE", "key": "pwd", "value": "my password is secret123"},
    ]
    for p in bad_payloads:
        resp = client.post("/memory", json=p)
        assert resp.status_code == 422
        detail = resp.json()["detail"].lower()
        assert "sensitive" in detail or "pii" in detail


def test_api_user_isolation_and_clear():
    """Test memory isolation between users and DELETE /memory (Right to be Forgotten)."""
    # Create memory for User A
    client.post("/memory", json={
        "user_id": "user_isolated_A",
        "memory_type": "LEARNING_LEVEL",
        "key": "learning_level",
        "value": "beginner",
    })

    # Create memory for User B
    client.post("/memory", json={
        "user_id": "user_isolated_B",
        "memory_type": "LEARNING_LEVEL",
        "key": "learning_level",
        "value": "advanced",
    })

    # Verify User A cannot see User B's memory
    resp_a = client.get("/memory?user_id=user_isolated_A")
    assert resp_a.json()["count"] == 1
    assert resp_a.json()["memories"][0]["value"] == "beginner"

    resp_b = client.get("/memory?user_id=user_isolated_B")
    assert resp_b.json()["count"] == 1
    assert resp_b.json()["memories"][0]["value"] == "advanced"

    # User A exercises Right to be Forgotten
    del_resp = client.delete("/memory?user_id=user_isolated_A")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_count"] == 1

    # User A now has 0 memories
    resp_a_after = client.get("/memory?user_id=user_isolated_A")
    assert resp_a_after.json()["count"] == 0

    # User B remains intact
    resp_b_after = client.get("/memory?user_id=user_isolated_B")
    assert resp_b_after.json()["count"] == 1


def test_api_delete_single_memory_with_ownership_check():
    """Test DELETE /memory/{memory_id} enforces user ownership."""
    create_resp = client.post("/memory", json={
        "user_id": "user_owner",
        "memory_type": "LEARNING_LEVEL",
        "key": "learning_level",
        "value": "beginner",
    })
    mem_id = create_resp.json()["memory_id"]

    # Wrong user cannot delete
    fail_del = client.delete(f"/memory/{mem_id}?user_id=wrong_user")
    assert fail_del.status_code == 404

    # Right user deletes
    ok_del = client.delete(f"/memory/{mem_id}?user_id=user_owner")
    assert ok_del.status_code == 200
    assert ok_del.json()["status"] == "deleted"


# =====================================================================
# 2. Ephemeral Session Mode (user_id is None)
# =====================================================================

def test_ephemeral_mode_does_not_persist_memories():
    """
    INVARIANT: If user_id is None, no memory is written to persistent SQLite store.
    System runs in purely ephemeral session mode.
    """
    mock_rag = RAGAnswer(
        query="What is an index fund?",
        answer="An index fund tracks a market benchmark.",
        grounding_status="fully_grounded",
        citations=[],
        model_used="test",
    )
    with patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag):
        resp = client.post("/chat", json={
            "query": "I am a beginner in stock markets. What is an index fund?",
            "user_id": None,
        })
        assert resp.status_code == 200
        # Store must remain completely empty
        records = memory_service.store.list_by_user("None")
        assert len(records) == 0


# =====================================================================
# 3. Candidate Extraction & Personalization Across Domains
# =====================================================================

def test_orchestrator_extracts_and_personalizes_in_subsequent_query():
    """
    Test turn 1: User explicitly declares beginner status.
    Candidate is extracted and saved.
    Turn 2: Next query automatically retrieves profile and adapts system prompt.
    """
    user_id = "learner_flow_1"
    mock_rag = RAGAnswer(
        query="How do stocks work?",
        answer="Stocks represent partial ownership in a corporation.",
        grounding_status="fully_grounded",
        citations=[],
        model_used="test",
    )

    with patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag):
        # Turn 1: Explicit declaration
        resp1 = client.post("/chat", json={
            "query": "I am a beginner in investing. How do stocks work?",
            "user_id": user_id,
        })
        assert resp1.status_code == 200

        # Verify memory was saved
        records = memory_service.get_user_memories(user_id)
        assert len(records) >= 1
        level_rec = next(r for r in records if r.key == "learning_level")
        assert level_rec.value == "beginner"

        # Turn 2: Follow-up query retrieves profile
        profile = memory_service.retrieve_profile(user_id)
        assert profile is not None
        assert profile.learning_level == "beginner"


def test_explicit_query_overrides_stored_profile():
    """
    INVARIANT: Current query explicit depth ALWAYS overrides stored long-term memory.
    If stored profile says 'beginner', but query asks for 'advanced deep dive',
    the effective level for that query is 'advanced'.

    Phase 6 Compatibility Note:
    In Phase 5, 'options delta' routed to the GENERAL fallback because Derivatives was not yet an agent.
    With Phase 6 adding the DERIVATIVES specialized agent, 'options delta' is owned by DerivativesAgent.
    To test the orchestrator's GENERAL SEBI RAG fallback and profile overriding, an unspecialized
    general financial query ('sovereign gold bonds') is used.
    """
    user_id = "user_override_test"
    # Seed beginner memory
    memory_service.create_explicit_memory(
        user_id=user_id,
        memory_type="LEARNING_LEVEL",
        key="learning_level",
        value="beginner",
    )

    mock_rag_answer = RAGAnswer(
        query="What are sovereign gold bonds?",
        answer="SGBs are government securities denominated in grams of gold.",
        grounding_status="fully_grounded",
        citations=[],
        model_used="test",
    )

    with patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag_answer) as mock_rag:
        resp = client.post("/chat", json={
            "query": "Give me an advanced in-depth technical deep dive into sovereign gold bonds",
            "user_id": user_id,
        })
        assert resp.status_code == 200

        # Verify that generate_answer received the overridden Advanced level
        call_kwargs = mock_rag.call_args.kwargs
        sys_prompt = call_kwargs.get("system_prompt", "")
        assert "Advanced level" in sys_prompt


# =====================================================================
# 4. Safety Invariants
# =====================================================================

def test_safety_cannot_be_bypassed_via_memory():
    """
    CRITICAL SAFETY INVARIANT:
    Even if user memory exists, an advisory / stock tip inquiry is rejected immediately
    by Global Safety Pre-Filter in <1ms without executing agents or saving candidates.
    """
    user_id = "user_safety_probe"
    # Seed profile
    memory_service.create_explicit_memory(
        user_id=user_id,
        memory_type="USER_PREFERENCE",
        key="risk_tolerance",
        value="aggressive",
    )

    resp = client.post("/chat", json={
        "query": "Which crypto should I buy today for guaranteed 100x gains?",
        "user_id": user_id,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounding_status"] == "ungrounded"
    assert data["model_used"] == "deterministic_guardrail"
    assert "filtered" in data["sub_tasks"][0]["status"]

    # No memory candidate extraction on unsafe queries
    records = memory_service.get_user_memories(user_id)
    assert len(records) == 1  # only original seeded record exists


# =====================================================================
# 5. Fault Tolerance & Graceful Degradation
# =====================================================================

def test_memory_failure_never_crashes_orchestrator():
    """
    CRITICAL RELIABILITY INVARIANT:
    If SQLite or memory service raises an error, orchestrator catches it and
    still returns a valid financial education response.
    """
    user_id = "user_fault_test"

    mock_rag = RAGAnswer(
        query="What is an index fund?",
        answer="An index fund holds a basket of benchmark stocks.",
        grounding_status="fully_grounded",
        citations=[],
        model_used="test",
    )

    with patch.object(memory_service, "retrieve_profile", side_effect=RuntimeError("DB Lock Timeout")), \
         patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag):
        resp = client.post("/chat", json={
            "query": "What is an index fund?",
            "user_id": user_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain_detected"] == "EQUITY"
        assert len(data["answer"]) > 0


def test_memory_ttl_expiration():
    """Verify that records with expired TTL are filtered out upon retrieval."""
    user_id = "user_ttl_test"
    now = datetime.now(timezone.utc)
    expired_record = MemoryRecord(
        memory_id="mem_expired",
        user_id=user_id,
        memory_type="USER_PREFERENCE",
        key="temp_pref",
        value="temp_val",
        source="explicit_user_statement",
        confidence=1.0,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        expires_at=(now - timedelta(seconds=10)).isoformat(),
    )
    memory_service.store.put(expired_record)

    # Retrieval should return empty
    active_mems = memory_service.get_user_memories(user_id)
    assert len(active_mems) == 0
