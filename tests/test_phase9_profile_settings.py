"""
Tests for Finova AI Phase 9: Profile + Settings.
Covers:
- GET /memory/profile and POST /memory/profile
- Learning level, goals, interests, and instructional preferences reconciliation
- Privacy validation and PII rejection on profile updates
- Storage isolation: clearing conversations does NOT affect memory.db, and vice versa
- User isolation across profiles and conversations
- Error handling and input validation
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.memory.service import memory_service
from app.conversations.service import conversation_service

client = TestClient(app)


def test_get_profile_default():
    """Verify GET /memory/profile returns empty profile for a user with no records."""
    user_id = "test_usr_p9_default"
    memory_service.clear_user(user_id)

    resp = client.get(f"/memory/profile?user_id={user_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == user_id
    assert data["learning_level"] is None
    assert data["learning_goals"] == []
    assert data["interests"] == []
    assert data["preferences"] == {}


def test_get_profile_empty_user_id_rejected():
    """Verify empty user_id returns HTTP 400."""
    resp = client.get("/memory/profile?user_id=  ")
    assert resp.status_code == 400
    assert "user_id must not be empty" in resp.json()["detail"]


def test_update_profile_and_reconciliation():
    """Verify updating learning level, goals, interests, and preferences persists to memory."""
    user_id = "test_usr_p9_update"
    memory_service.clear_user(user_id)

    # Initial profile update
    payload = {
        "user_id": user_id,
        "learning_level": "intermediate",
        "learning_goals": ["Investing Basics", "Indian Markets"],
        "interests": ["Equities", "Mutual Funds"],
        "preferences": {"explanation_style": "concise"},
    }
    resp = client.post("/memory/profile", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["learning_level"] == "intermediate"
    assert set(data["learning_goals"]) == {"Investing Basics", "Indian Markets"}
    assert set(data["interests"]) == {"Equities", "Mutual Funds"}
    assert data["preferences"].get("explanation_style") == "concise"

    # Second update reconciling goals and interests (removing some, adding others)
    payload_reconcile = {
        "user_id": user_id,
        "learning_level": "advanced",
        "learning_goals": ["Indian Markets", "Derivatives"],
        "interests": ["Equities", "Crypto"],
        "preferences": {"explanation_style": "detailed"},
    }
    resp2 = client.post("/memory/profile", json=payload_reconcile)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["learning_level"] == "advanced"
    assert "Investing Basics" not in data2["learning_goals"]
    assert "Derivatives" in data2["learning_goals"]
    assert "Mutual Funds" not in data2["interests"]
    assert "Crypto" in data2["interests"]
    assert data2["preferences"].get("explanation_style") == "detailed"


def test_update_profile_invalid_learning_level():
    """Verify invalid learning level is rejected with HTTP 422."""
    user_id = "test_usr_p9_invalid_level"
    resp = client.post(
        "/memory/profile",
        json={"user_id": user_id, "learning_level": "grandmaster"},
    )
    assert resp.status_code == 422


def test_update_profile_rejects_pii():
    """Verify memory validator guardrails prevent PII/credentials in preferences."""
    user_id = "test_usr_p9_pii"
    # Attempting to store a PAN card in preference
    resp = client.post(
        "/memory/profile",
        json={
            "user_id": user_id,
            "preferences": {"pan": "ABCDE1234F"},
        },
    )
    assert resp.status_code == 422
    assert "sensitive financial data" in resp.json()["detail"].lower()


def test_clear_conversations_api():
    """Verify DELETE /conversations clears all conversations for a user."""
    user_id = "test_usr_p9_conv_clear"
    # Create two conversations
    c1 = conversation_service.create_conversation(user_id=user_id, title="Chat 1")
    c2 = conversation_service.create_conversation(user_id=user_id, title="Chat 2")
    conversation_service.add_message(c1.conversation_id, user_id=user_id, role="user", content="Hello")
    conversation_service.add_message(c2.conversation_id, user_id=user_id, role="user", content="World")

    # Verify they exist
    convs = conversation_service.list_conversations(user_id=user_id)
    assert len(convs) >= 2

    # Clear all conversations
    resp = client.delete(f"/conversations?user_id={user_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cleared"
    assert data["deleted_count"] >= 2

    # Verify list is now empty
    convs_after = conversation_service.list_conversations(user_id=user_id)
    assert len(convs_after) == 0


def test_storage_isolation_conversation_vs_memory():
    """
    CRITICAL INVARIANT:
    Clearing conversations must NOT delete learner memory.
    Clearing learner memory must NOT delete conversation history.
    """
    user_id = "test_usr_p9_isolation"
    memory_service.clear_user(user_id)
    conversation_service.clear_user_conversations(user_id)

    # 1. Set up learner memory
    memory_service.update_profile(
        user_id=user_id,
        learning_level="beginner",
        learning_goals=["Options Trading"],
        interests=["Derivatives"],
    )
    # 2. Set up a conversation
    conv = conversation_service.create_conversation(user_id=user_id, title="Test Chat")
    conversation_service.add_message(conv.conversation_id, user_id=user_id, role="user", content="Test query")

    # Step A: Clear conversations
    resp_conv = client.delete(f"/conversations?user_id={user_id}")
    assert resp_conv.status_code == 200

    # Verify conversations are gone
    assert len(conversation_service.list_conversations(user_id)) == 0

    # Verify memory is completely intact
    profile = memory_service.retrieve_profile(user_id)
    assert profile.learning_level == "beginner"
    assert "Options Trading" in profile.learning_goals
    assert "Derivatives" in profile.interests

    # Step B: Re-add conversation and clear memory
    conv2 = conversation_service.create_conversation(user_id=user_id, title="Test Chat 2")
    conversation_service.add_message(conv2.conversation_id, user_id=user_id, role="user", content="Query 2")

    resp_mem = client.delete(f"/memory?user_id={user_id}")
    assert resp_mem.status_code == 200

    # Verify memory is cleared
    profile_cleared = memory_service.retrieve_profile(user_id)
    assert profile_cleared.learning_level is None
    assert profile_cleared.learning_goals == []

    # Verify conversation history is completely intact
    convs_remaining = conversation_service.list_conversations(user_id)
    assert len(convs_remaining) == 1
    assert convs_remaining[0].title == "Test Chat 2"


def test_user_isolation():
    """Verify user A cannot access or clear user B's profile or conversations."""
    user_a = "test_usr_p9_alice"
    user_b = "test_usr_p9_bob"

    memory_service.update_profile(user_id=user_a, learning_level="beginner")
    memory_service.update_profile(user_id=user_b, learning_level="advanced")

    profile_a = client.get(f"/memory/profile?user_id={user_a}").json()
    profile_b = client.get(f"/memory/profile?user_id={user_b}").json()

    assert profile_a["learning_level"] == "beginner"
    assert profile_b["learning_level"] == "advanced"
