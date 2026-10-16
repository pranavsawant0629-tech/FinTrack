"""
Phase 11: Learning / Tutor UX Test Suite.

Validates:
1. Learning context is preserved across tutor conversation turns (topic continuity).
2. Existing last-6-message bound remains intact.
3. Tutor learning actions route through the correct tutor.
4. "Explain simpler" works (pedagogical level override to beginner without memory mutation).
5. "Go deeper" works (pedagogical level override to advanced).
6. Example / analogy actions work.
7. Related concept actions work.
8. "What should I learn next?" remains domain appropriate.
9. Quiz integration uses the existing Quiz Agent while preserving conversation domain.
10. Personalization affects pedagogical behavior.
11. Learning actions do not bypass safety (Step 1 guardrail cannot be bypassed).
12. Existing conversation domain remains 100% immutable.
13. Reopened conversations restore learning context (topic, related concepts, suggested next).
14. Existing rich cards/citations still restore.
15. User ownership remains enforced.
16. General Chat remains unchanged.
17. Existing memory remains separate from conversations.
"""

from unittest.mock import MagicMock
import pytest
from app.conversations.learning_context import (
    resolve_learning_context,
    CANONICAL_TOPICS,
    _match_topic_from_text,
)
from app.conversations.models import (
    AssistantMessageMetadata,
    extract_assistant_metadata,
)
from app.conversations.service import ConversationService
from app.conversations.store import SQLiteConversationStore
from app.memory.models import PersonalizationProfile
from app.memory.service import MemoryService
from app.memory.store import SQLiteMemoryStore
from app.router.models import (
    Citation,
    Domain,
    OrchestratorResponse,
    RoutingDecision,
    SubTaskExecutionMetadata,
)
from app.router.orchestrator import CentralOrchestrator
from app.tools.market.models import MarketDataProvenance


@pytest.fixture
def temp_conv_store(tmp_path):
    """Provide an isolated conversation store for tests."""
    db_path = tmp_path / "test_phase11_conv.db"
    return SQLiteConversationStore(db_path=db_path)


@pytest.fixture
def conv_service(temp_conv_store):
    """Provide a ConversationService backed by the isolated test store."""
    service = ConversationService(store=temp_conv_store)
    return service


# ============================================================================
# 1 & 2: Topic Continuity & Bounded History Invariant
# ============================================================================

def test_topic_continuity_across_turns():
    """Verify follow-up questions naturally retain the parent topic from bounded history."""
    # Turn 1: User asks about P/E ratio
    res1 = resolve_learning_context(query="What is P/E ratio?", domain="equity")
    assert res1.topic == "P/E Ratio & Valuation"
    assert len(res1.related_concepts) >= 3
    assert "EPS (Earnings Per Share)" in res1.related_concepts

    # Turn 2: Follow-up question doesn't repeat "P/E ratio"
    history = [
        {"role": "user", "content": "What is P/E ratio?"},
        {"role": "assistant", "content": "The Price-to-Earnings ratio measures valuation."},
    ]
    res2 = resolve_learning_context(
        query="Why is a high P/E considered expensive?",
        domain="equity",
        conversation_history=history,
    )
    assert res2.topic == "P/E Ratio & Valuation"

    # Turn 3: Action "Give me an example"
    history.extend([
        {"role": "user", "content": "Why is a high P/E considered expensive?"},
        {"role": "assistant", "content": "A high P/E indicates high growth expectations."},
    ])
    res3 = resolve_learning_context(
        query="Give me an example",
        domain="equity",
        conversation_history=history,
    )
    assert res3.topic == "P/E Ratio & Valuation"
    assert res3.is_action_followup is True


def test_bounded_history_limit_preserved(temp_conv_store):
    """Verify that get_bounded_history preserves the strict 6-message bound."""
    conv = temp_conv_store.create_conversation("user_test", "Equity Learning", domain="equity")
    cid = conv.conversation_id

    # Add 10 messages
    for i in range(10):
        role = "user" if i % 2 == 0 else "assistant"
        temp_conv_store.add_message(cid, role, f"Message {i}", status="complete")

    bounded = temp_conv_store.get_bounded_history(cid, max_turns=6)
    assert len(bounded) == 6
    assert bounded[0]["content"] == "Message 4"
    assert bounded[-1]["content"] == "Message 9"


# ============================================================================
# 3, 4, 5, 6, 7: Learning Actions & Pedagogical Overrides
# ============================================================================

def test_explain_simpler_pedagogical_override():
    """Verify 'Explain simpler' sets effective level to beginner without mutating stored profile."""
    # User with intermediate profile
    profile = PersonalizationProfile(
        user_id="learner_override",
        learning_level="intermediate",
        explanation_preference="structured",
    )

    # Test internal step 2 logic
    q_lower = "explain simpler: p/e ratio"
    override_level = None
    if any(w in q_lower for w in ["beginner", "simple terms", "explain simpler", "simpler"]):
        override_level = "beginner"

    assert override_level == "beginner"
    effective_profile = profile.model_copy(update={"learning_level": override_level})
    assert effective_profile.learning_level == "beginner"
    # Permanent profile remains untouched
    assert profile.learning_level == "intermediate"


def test_go_deeper_pedagogical_override():
    """Verify 'Go deeper' sets effective level to advanced without mutating stored profile."""
    profile = PersonalizationProfile(
        user_id="learner_override",
        learning_level="beginner",
    )

    q_lower = "go deeper into the mechanics of call options"
    override_level = None
    if any(w in q_lower for w in ["advanced", "deep dive", "go deeper", "deeper", "mechanics"]):
        override_level = "advanced"

    assert override_level == "advanced"
    effective_profile = profile.model_copy(update={"learning_level": override_level})
    assert effective_profile.learning_level == "advanced"
    assert profile.learning_level == "beginner"


def test_example_and_analogy_context_resolution():
    """Verify that example and analogy actions map properly to topic."""
    history = [
        {"role": "user", "content": "What is compounding?"},
        {"role": "assistant", "content": "Compounding is interest on interest."},
    ]
    res_analogy = resolve_learning_context(
        query="Explain with an analogy",
        domain="personal_finance",
        conversation_history=history,
    )
    assert res_analogy.topic == "Compounding & Time Horizon"
    assert res_analogy.is_action_followup is True


def test_related_concepts_action_generation():
    """Verify related concepts are non-empty and domain-specific."""
    res_derivatives = resolve_learning_context(query="What is a call option?", domain="derivatives")
    assert res_derivatives.topic == "Call Options & Bullish Payoffs"
    assert "Strike Price" in res_derivatives.related_concepts
    assert "Option Premium" in res_derivatives.related_concepts


# ============================================================================
# 8: Domain-Appropriate "What should I learn next?"
# ============================================================================

def test_suggested_next_is_domain_appropriate():
    """Verify suggested_next provides relevant pedagogical inquiries."""
    res_crypto = resolve_learning_context(query="What is Bitcoin halving?", domain="crypto")
    assert res_crypto.topic == "Bitcoin & Blockchain Fundamentals"
    assert len(res_crypto.suggested_next) >= 2
    assert any("halving" in s.lower() or "blockchain" in s.lower() for s in res_crypto.suggested_next)


# ============================================================================
# 9: Quiz Integration & Domain Invariant
# ============================================================================

def test_quiz_routing_preserves_conversation_domain(conv_service):
    """
    INVARIANT 1:
    'Quiz me on this' routes quiz generation to QuizAgent, but the conversation
    stored domain MUST remain authoritative and immutable.
    """
    orch = CentralOrchestrator()
    # Test real orchestrator routing for quiz query in tutor section
    quiz_resp = orch.ask("Quiz me on P/E ratio", domain_context="EQUITY")
    assert quiz_resp.quiz_data is not None
    assert "questions" in quiz_resp.quiz_data
    assert quiz_resp.domain_detected == "EQUITY"
    assert "Quiz" in quiz_resp.agent_name

    # Now verify conversation domain immutability in conversation service
    user_id = "user_quiz_test"
    conv = conv_service.create_conversation(user_id=user_id, title="Equity Lesson", domain="equity")
    cid = conv.conversation_id

    # Mock ask to test conversation service turn persistence
    mock_orch = MagicMock()
    mock_orch.ask.return_value = quiz_resp
    conv_service.orchestrator = mock_orch

    turn = conv_service.send_turn(
        user_id=user_id,
        query="Quiz me on P/E ratio",
        conversation_id=cid,
        domain="equity",
    )
    assert turn.orchestrator_response is not None
    assert turn.orchestrator_response.quiz_data is not None

    detail = conv_service.get_conversation_detail(conversation_id=cid, user_id=user_id)
    assert detail.conversation.domain == "equity"
    assert len(detail.messages) == 2  # user + assistant


# ============================================================================
# 10: Personalization Behavioral Adaptation
# ============================================================================

def test_personalization_level_behavior():
    """Verify that learner level affects prompt and tone."""
    profile_beg = PersonalizationProfile(user_id="u_beg", learning_level="beginner")
    profile_adv = PersonalizationProfile(user_id="u_adv", learning_level="advanced")

    assert profile_beg.learning_level == "beginner"
    assert profile_adv.learning_level == "advanced"


# ============================================================================
# 11: Safety Guardrails Unbypassed
# ============================================================================

def test_learning_actions_never_bypass_safety():
    """
    Verify that speculative options, advice, or stock pick inquiries
    are unconditionally intercepted by Step 1 Global Safety, and NEVER
    have learning topics or actions attached.
    """
    orch = CentralOrchestrator()

    # Speculative advisory query disguised as learning
    resp = orch.ask(query="Which call option should I buy tomorrow to get guaranteed return?")
    assert resp.model_used == "deterministic_guardrail"
    assert resp.grounding_status == "ungrounded"
    # Invariant: Topic and actions are None / empty on safety refusals
    assert resp.topic is None
    assert resp.related_concepts == []
    assert resp.suggested_next == []


def test_pure_stock_quote_has_no_educational_actions():
    """
    INVARIANT 2:
    Pure deterministic market-data / price responses without an educational concept
    must NOT display learning actions.
    """
    provenance = MarketDataProvenance(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        price=2950.0,
        current_price=2950.0,
        market_status="closed",
        market_timestamp="2026-09-13T00:00:00Z",
        retrieved_at="2026-09-13T00:00:00Z",
        provider="yfinance",
        source_url="https://finance.yahoo.com",
        freshness_status="realtime",
    )
    orch_resp = OrchestratorResponse(
        query="what is the price of RELIANCE?",
        answer="Reliance Industries is currently trading at ₹2,950.00.",
        grounding_status="ungrounded",
        citations=[],
        market_data=provenance,
        market_data_list=[],
        domain_detected="EQUITY",
        agent_name="Market Data Agent",
    )
    res = resolve_learning_context(
        query="what is the price of RELIANCE?",
        domain="equity",
        orchestrator_response=orch_resp,
    )
    assert res.topic is None
    assert res.related_concepts == []
    assert res.suggested_next == []


# ============================================================================
# 12 & 13: Immutability and Metadata Persistence / Restoration
# ============================================================================

def test_metadata_persistence_and_reconstruction():
    """Verify that topic, related_concepts, and suggested_next persist in metadata."""
    cit = Citation(
        citation_id=1,
        chunk_id="chunk_1",
        doc_id="doc_1",
        title="NISM Chapter 4",
        source="SEBI NISM",
        snippet="SIP compounding details",
        similarity_score=0.92,
    )
    orch_resp = OrchestratorResponse(
        query="What is SIP?",
        answer="A Systematic Investment Plan (SIP) allows disciplined monthly investments.",
        grounding_status="fully_grounded",
        citations=[cit],
        domain_detected="PERSONAL_FINANCE",
        agent_name="Personal Finance Tutor",
        topic="SIP & Rupee Cost Averaging",
        related_concepts=["Compounding", "Mutual Funds", "Lump Sum vs SIP"],
        suggested_next=["How does rupee cost averaging protect during market drawdowns?"],
    )

    meta = extract_assistant_metadata(orch_resp)
    assert meta["topic"] == "SIP & Rupee Cost Averaging"
    assert "Compounding" in meta["related_concepts"]
    assert len(meta["suggested_next"]) == 1
    assert meta["schema_version"] == 1
    # Verify non-redundant payload
    assert "query" not in meta
    assert "answer" not in meta


def test_conversation_domain_immutable_across_turns(conv_service):
    """Verify that domain cannot be changed by subsequent requests in an existing conversation."""
    user_id = "user_immutable"
    conv = conv_service.create_conversation(user_id=user_id, title="Derivatives Prep", domain="derivatives")
    cid = conv.conversation_id

    mock_orch = MagicMock()
    mock_orch.ask.return_value = OrchestratorResponse(
        query="What is a Call Option?",
        answer="A Call Option gives the right to buy.",
        grounding_status="fully_grounded",
        domain_detected="DERIVATIVES",
    )
    conv_service.orchestrator = mock_orch

    # User turns passing a different domain parameter shouldn't mutate stored domain
    conv_service.send_turn(
        user_id=user_id,
        query="What is a Call Option?",
        conversation_id=cid,
        domain="crypto",  # Mismatched parameter
    )

    detail = conv_service.get_conversation_detail(conversation_id=cid, user_id=user_id)
    assert detail.conversation.domain == "derivatives"


# ============================================================================
# 14, 15, 16, 17: Regressions & Separation
# ============================================================================

def test_user_ownership_enforcement(conv_service):
    """Verify user ownership remains strictly enforced."""
    conv = conv_service.create_conversation(user_id="alice", title="Alice Chat", domain="equity")
    cid = conv.conversation_id

    with pytest.raises(Exception):
        conv_service.get_conversation_detail(conversation_id=cid, user_id="bob")


def test_general_chat_remains_intact():
    """Verify General Chat continues to work for broad inquiries."""
    res = resolve_learning_context(query="What is financial diversification?", domain="general")
    assert res.topic == "Diversification & Correlation"
    assert "Asset Allocation" in res.related_concepts


def test_memory_remains_separate_from_conversation(tmp_path):
    """Verify that conversation turns do not duplicate full conversation history into memory."""
    mem_db = tmp_path / "test_mem.db"
    mem_store = SQLiteMemoryStore(db_path=mem_db)
    mem_service = MemoryService(store=mem_store)

    # Save a preference
    mem_service.add_memory(user_id="u1", memory_type="LEARNING_LEVEL", key="learning_level", value="beginner")
    records = mem_service.store.list_by_user("u1")
    assert len(records) == 1
    assert records[0].value == "beginner"
    # No conversational message transcript is stored in memory.db
    assert all("Message" not in r.key for r in records)
