"""
Unit tests for SQLiteConversationStore and deterministic title generation.
Tests CRUD, cascade deletion, bounded history, and edge cases.
"""

import pytest

from app.conversations.store import (
    SQLiteConversationStore,
    generate_conversation_title,
)


def test_generate_conversation_title_edge_cases():
    """Test deterministic title generation across various edge cases."""
    # 1. Normal sentence
    t1 = generate_conversation_title("what is a call option and how does breakeven work?")
    assert t1.startswith("What is a call option and")
    assert not t1.endswith(" ")

    # 2. Short string
    assert generate_conversation_title("hi") == "Hi"
    assert generate_conversation_title("?") == "?"
    assert generate_conversation_title("a") == "A"

    # 3. Emoji-only
    assert generate_conversation_title("🚀📈") == "🚀📈"
    assert generate_conversation_title("  💰  ") == "💰"

    # 4. Non-Latin script (Devanagari / Hindi)
    hindi_query = "निफ्टी 50 क्या है और यह कैसे काम करता है?"
    t_hindi = generate_conversation_title(hindi_query)
    assert "निफ्टी" in t_hindi

    # 5. Empty and whitespace-only
    assert generate_conversation_title("") == "New Conversation"
    assert generate_conversation_title("   \n\t  ") == "New Conversation"

    # 6. No LLM invoked (synchronous, instant, deterministic)
    assert generate_conversation_title("SIP vs Lumpsum") == "SIP vs Lumpsum"


def test_store_conversation_crud():
    """Test conversation creation, retrieval, listing, title update, and deletion in an isolated in-memory DB."""
    store = SQLiteConversationStore(db_path=":memory:")

    # Create conversation
    conv = store.create_conversation(user_id="user_alpha", title="Alpha Inquiry", domain="general")
    assert conv.conversation_id.startswith("conv_")
    assert conv.user_id == "user_alpha"
    assert conv.title == "Alpha Inquiry"
    assert conv.domain == "general"
    assert conv.created_at is not None
    assert conv.updated_at is not None

    # Get conversation
    fetched = store.get_conversation(conv.conversation_id)
    assert fetched is not None
    assert fetched.conversation_id == conv.conversation_id
    assert fetched.title == "Alpha Inquiry"

    # Update title
    updated = store.update_title(conv.conversation_id, "Updated Alpha Title")
    assert updated is not None
    assert updated.title == "Updated Alpha Title"
    assert store.get_conversation(conv.conversation_id).title == "Updated Alpha Title"

    # List conversations
    listing = store.list_conversations("user_alpha")
    assert len(listing) == 1
    assert listing[0].conversation_id == conv.conversation_id
    assert listing[0].title == "Updated Alpha Title"
    assert listing[0].message_count == 0

    # Non-existent user
    assert len(store.list_conversations("user_unknown")) == 0

    # Delete conversation
    assert store.delete_conversation(conv.conversation_id) is True
    assert store.get_conversation(conv.conversation_id) is None
    assert len(store.list_conversations("user_alpha")) == 0
    store.close()


def test_store_messages_and_cascade_delete():
    """Test message persistence, status tracking, metadata preservation, and foreign key cascade deletion."""
    store = SQLiteConversationStore(db_path=":memory:")

    conv = store.create_conversation(user_id="user_beta", title="Derivatives Test")
    conv_id = conv.conversation_id

    # Add user message
    msg1 = store.add_message(
        conversation_id=conv_id,
        role="user",
        content="Explain Call options",
        status="complete",
    )
    assert msg1.role == "user"
    assert msg1.status == "complete"
    assert msg1.content == "Explain Call options"

    # Add assistant response with structured metadata
    meta = {
        "agent_name": "Derivatives Tutor",
        "domain_detected": "DERIVATIVES",
        "citations": [{"title": "NSE Options", "url": "https://nseindia.com"}],
        "derivatives_data": {"strike": 22000, "breakeven": 22150},
    }
    msg2 = store.add_message(
        conversation_id=conv_id,
        role="assistant",
        content="A Call Option gives the buyer the right to buy...",
        status="complete",
        metadata=meta,
    )
    assert msg2.role == "assistant"
    assert msg2.metadata == meta

    # Add a failed turn
    msg3 = store.add_message(
        conversation_id=conv_id,
        role="assistant",
        content="Error contacting engine",
        status="failed",
        metadata={"error": "Ollama timeout"},
    )
    assert msg3.status == "failed"

    # Get all messages
    all_msgs = store.get_messages(conv_id)
    assert len(all_msgs) == 3
    assert all_msgs[0].message_id == msg1.message_id
    assert all_msgs[1].message_id == msg2.message_id
    assert all_msgs[2].message_id == msg3.message_id
    assert all_msgs[1].metadata["agent_name"] == "Derivatives Tutor"

    # Check conversation message_count in listing
    listing = store.list_conversations("user_beta")
    assert len(listing) == 1
    assert listing[0].message_count == 3

    # Delete conversation and ensure messages are cascade deleted
    assert store.delete_conversation(conv_id) is True
    assert store.get_conversation(conv_id) is None
    assert len(store.get_messages(conv_id)) == 0

    store.close()


def test_store_bounded_history():
    """Verify that bounded history only returns completed turns, limits to max_turns, and maintains chronological order."""
    store = SQLiteConversationStore(db_path=":memory:")
    conv = store.create_conversation(user_id="user_gamma", title="History Test")
    conv_id = conv.conversation_id

    # Add 4 turns (8 messages) + 1 failed message
    for i in range(1, 5):
        store.add_message(
            conversation_id=conv_id,
            role="user",
            content=f"Question {i}",
            status="complete",
            timestamp=f"2026-09-12T10:0{i}:00Z",
        )
        store.add_message(
            conversation_id=conv_id,
            role="assistant",
            content=f"Answer {i}",
            status="complete",
            timestamp=f"2026-09-12T10:0{i}:30Z",
        )

    # Insert a failed assistant message
    store.add_message(
        conversation_id=conv_id,
        role="assistant",
        content="Failed turn",
        status="failed",
        timestamp="2026-09-12T10:05:00Z",
    )

    # Fetch bounded history with max_turns=4
    # Total completed messages = 8. Bounded to 4 means the last 4 completed messages: Q3, A3, Q4, A4
    bounded_4 = store.get_bounded_history(conv_id, max_turns=4)
    assert len(bounded_4) == 4
    assert bounded_4[0] == {"role": "user", "content": "Question 3"}
    assert bounded_4[1] == {"role": "assistant", "content": "Answer 3"}
    assert bounded_4[2] == {"role": "user", "content": "Question 4"}
    assert bounded_4[3] == {"role": "assistant", "content": "Answer 4"}

    # None of the failed messages should appear
    assert all("Failed" not in h["content"] for h in bounded_4)

    store.close()
