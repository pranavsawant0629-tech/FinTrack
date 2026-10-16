"""
API tests for Conversations endpoints in Finova AI.
Validates CRUD, user isolation, and strict server-side direct-access rejection (IDOR defense).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.conversations.store import SQLiteConversationStore
import app.conversations.service as conv_service_mod

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_conversation_store(monkeypatch):
    """Use an isolated in-memory SQLite store for each test."""
    test_store = SQLiteConversationStore(db_path=":memory:")
    monkeypatch.setattr(conv_service_mod, "conversation_store", test_store)
    monkeypatch.setattr(conv_service_mod.conversation_service, "store", test_store)
    yield test_store
    test_store.close()


def test_create_and_list_conversations_user_isolation():
    """Test creating conversations for two users and verifying user isolation in listing."""
    # User 1 creates conversation
    res1 = client.post(
        "/conversations",
        json={"user_id": "usr_alice", "title": "Alice Portfolio Chat", "domain": "general"},
    )
    assert res1.status_code == 201
    c1 = res1.json()
    assert c1["conversation_id"].startswith("conv_")
    assert c1["user_id"] == "usr_alice"
    assert c1["title"] == "Alice Portfolio Chat"
    assert c1["domain"] == "general"

    # User 2 creates conversation
    res2 = client.post(
        "/conversations",
        json={"user_id": "usr_bob", "title": "Bob Crypto Chat", "domain": "crypto"},
    )
    assert res2.status_code == 201
    c2 = res2.json()
    assert c2["user_id"] == "usr_bob"

    # Listing for Alice should only show Alice's conversation
    alice_list = client.get("/conversations", params={"user_id": "usr_alice"})
    assert alice_list.status_code == 200
    alice_data = alice_list.json()
    assert len(alice_data) == 1
    assert alice_data[0]["conversation_id"] == c1["conversation_id"]
    assert alice_data[0]["title"] == "Alice Portfolio Chat"

    # Listing for Bob should only show Bob's conversation
    bob_list = client.get("/conversations", params={"user_id": "usr_bob"})
    assert bob_list.status_code == 200
    bob_data = bob_list.json()
    assert len(bob_data) == 1
    assert bob_data[0]["conversation_id"] == c2["conversation_id"]

    # Listing for a user with no conversations returns empty list
    charlie_list = client.get("/conversations", params={"user_id": "usr_charlie"})
    assert charlie_list.status_code == 200
    assert charlie_list.json() == []


def test_cross_user_direct_access_rejection_idor():
    """
    CRITICAL SECURITY TEST:
    Verifies that if a user directly attempts to fetch, modify, add messages to, or delete
    another user's conversation by ID, the server rejects it with 403 Forbidden.
    """
    # 1. Alice creates a private conversation
    res = client.post(
        "/conversations",
        json={"user_id": "usr_alice", "title": "Alice Confidential Wealth"},
    )
    assert res.status_code == 201
    alice_conv_id = res.json()["conversation_id"]

    # Add a message to Alice's conversation
    client.post(
        f"/conversations/{alice_conv_id}/messages",
        json={
            "user_id": "usr_alice",
            "role": "user",
            "content": "Alice's secret financial strategy",
        },
    )

    # 2. Bob attempts to GET Alice's conversation directly by ID -> MUST REJECT WITH 403
    bob_get = client.get(f"/conversations/{alice_conv_id}", params={"user_id": "usr_bob"})
    assert bob_get.status_code == 403
    assert "Access denied" in bob_get.json()["detail"]

    # 3. Bob attempts to POST a message to Alice's conversation -> MUST REJECT WITH 403
    bob_msg = client.post(
        f"/conversations/{alice_conv_id}/messages",
        json={
            "user_id": "usr_bob",
            "role": "user",
            "content": "Malicious injected message",
        },
    )
    assert bob_msg.status_code == 403

    # 4. Bob attempts to PATCH (rename) Alice's conversation -> MUST REJECT WITH 403
    bob_patch = client.patch(
        f"/conversations/{alice_conv_id}",
        json={"user_id": "usr_bob", "title": "Hacked Title"},
    )
    assert bob_patch.status_code == 403

    # 5. Bob attempts to DELETE Alice's conversation -> MUST REJECT WITH 403
    bob_del = client.delete(f"/conversations/{alice_conv_id}", params={"user_id": "usr_bob"})
    assert bob_del.status_code == 403

    # Confirm Alice's conversation is still intact and undisturbed
    alice_get = client.get(f"/conversations/{alice_conv_id}", params={"user_id": "usr_alice"})
    assert alice_get.status_code == 200
    assert alice_get.json()["conversation"]["title"] == "Alice Confidential Wealth"
    assert len(alice_get.json()["messages"]) == 1


def test_empty_conversation_not_persisted_until_message():
    """
    Verifies Section 6 requirement:
    An unsent 'new conversation' state in the UI does NOT create an empty conversation record in the database.
    """
    # Simply listing conversations for a new user produces 0 records
    res = client.get("/conversations", params={"user_id": "usr_fresh"})
    assert res.status_code == 200
    assert len(res.json()) == 0


def test_rename_and_delete_conversation():
    """Test renaming a conversation and deleting it with message cascade."""
    # Create conversation
    res = client.post(
        "/conversations",
        json={"user_id": "usr_dan", "title": "Initial Title"},
    )
    conv_id = res.json()["conversation_id"]

    # Add message
    client.post(
        f"/conversations/{conv_id}/messages",
        json={"user_id": "usr_dan", "role": "user", "content": "Hello Finova"},
    )

    # Rename
    patch_res = client.patch(
        f"/conversations/{conv_id}",
        json={"user_id": "usr_dan", "title": "Renamed Market Title"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Renamed Market Title"

    # Delete
    del_res = client.delete(f"/conversations/{conv_id}", params={"user_id": "usr_dan"})
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Fetching deleted conversation returns 404
    get_res = client.get(f"/conversations/{conv_id}", params={"user_id": "usr_dan"})
    assert get_res.status_code == 404
