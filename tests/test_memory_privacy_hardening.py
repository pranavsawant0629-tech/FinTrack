"""Stage 7F: Memory and Privacy Hardening Tests.

Validates:
1. Strict user memory isolation across independent user identities.
2. Anonymous query non-persistence (empty or None user_id rejected).
3. Deterministic PII rejection (PAN, Aadhaar, phone, card numbers, passwords, CVV).
4. Transient market data non-persistence (live prices rejected).
5. User preference safety invariant (preferences never override safety guardrails).
"""

from __future__ import annotations

import pytest

from app.memory.models import MemoryRecord
from app.memory.store import SQLiteMemoryStore
from app.memory.validator import MemoryValidator, memory_validator
from app.router.safety import GlobalSafetyGuardrail


class TestMemoryPrivacyHardening:
    """Stage 7F: Rigorous memory isolation, PII rejection, and privacy tests."""

    @pytest.fixture
    def memory_store(self) -> SQLiteMemoryStore:
        """Isolated in-memory SQLite store for testing."""
        return SQLiteMemoryStore(db_path=":memory:")

    @pytest.fixture
    def validator(self) -> MemoryValidator:
        return memory_validator

    # =========================================================================
    # 1. Strict Multi-Tenant User Isolation
    # =========================================================================
    def test_strict_user_isolation(self, memory_store: SQLiteMemoryStore):
        """User A's memory records must never be accessible to User B."""
        rec_a = MemoryRecord(
            memory_id="mem_a1",
            user_id="user_alice",
            memory_type="user_preference",
            key="risk_tolerance",
            value="conservative",
            source="explicit_user_statement",
            confidence=1.0,
            created_at="2026-03-30T10:00:00Z",
            updated_at="2026-03-30T10:00:00Z",
        )
        rec_b = MemoryRecord(
            memory_id="mem_b1",
            user_id="user_bob",
            memory_type="user_preference",
            key="risk_tolerance",
            value="aggressive",
            source="explicit_user_statement",
            confidence=1.0,
            created_at="2026-03-30T10:05:00Z",
            updated_at="2026-03-30T10:05:00Z",
        )

        memory_store.put(rec_a)
        memory_store.put(rec_b)

        # Bob cannot retrieve Alice's memory by ID
        assert memory_store.get("user_bob", "mem_a1") is None

        # Bob's list only contains Bob's memories
        bob_memories = memory_store.list_by_user("user_bob")
        assert len(bob_memories) == 1
        assert bob_memories[0].value == "aggressive"

        # Alice's list only contains Alice's memories
        alice_memories = memory_store.list_by_user("user_alice")
        assert len(alice_memories) == 1
        assert alice_memories[0].value == "conservative"

        # Clearing Bob's memories leaves Alice untouched
        deleted_count = memory_store.clear_user("user_bob")
        assert deleted_count == 1
        assert len(memory_store.list_by_user("user_bob")) == 0
        assert len(memory_store.list_by_user("user_alice")) == 1

    # =========================================================================
    # 2. Anonymous Query Non-Persistence
    # =========================================================================
    @pytest.mark.parametrize("invalid_user_id", ["", "   ", None])
    def test_anonymous_query_rejected_from_persistence(
        self,
        validator: MemoryValidator,
        invalid_user_id: str | None,
    ):
        """Anonymous sessions must never create or persist memory records."""
        is_valid, reason = validator.validate_candidate(
            user_id=invalid_user_id,  # type: ignore[arg-type]
            memory_type="user_preference",
            key="theme",
            value="dark_mode",
        )
        assert is_valid is False
        assert "strictly requires an explicit, non-empty user_id" in (reason or "")

    # =========================================================================
    # 3. Deterministic PII Rejection
    # =========================================================================
    @pytest.mark.parametrize(
        "pii_value,desc",
        [
            ("ABCDE1234F", "Indian PAN card"),
            ("9876 5432 1098", "Aadhaar number with spaces"),
            ("987654321098", "Aadhaar number continuous"),
            ("4532 0150 1234 5678", "Credit Card number"),
            ("My secret password is Pass123!", "Account password"),
            ("api_key: sk_live_999999999999", "API secret key"),
            ("Bank a/c number is 10023456789", "Bank account number"),
            ("My CVV is 456", "Card security code"),
            ("OTP is 789123", "One-time password"),
            ("9876543210", "Indian mobile number"),
            ("+919876543210", "Indian mobile number with +91"),
        ],
    )
    def test_pii_strictly_rejected(
        self,
        validator: MemoryValidator,
        pii_value: str,
        desc: str,
    ):
        """All PII, credentials, and financial account identifiers must be rejected."""
        is_valid, reason = validator.validate_candidate(
            user_id="user_123",
            memory_type="user_preference",
            key="contact_info",
            value=pii_value,
        )
        assert is_valid is False, f"Failed to reject {desc}: {pii_value}"
        assert "Contains sensitive financial data" in (reason or "")

    # =========================================================================
    # 4. Transient Market Data Non-Persistence
    # =========================================================================
    @pytest.mark.parametrize(
        "transient_value",
        [
            "Reliance is trading at 2950.00 right now",
            "The current price is 1500",
            "I bought at 2800 yesterday",
            "Last traded price was 500",
        ],
    )
    def test_transient_market_data_rejected(
        self,
        validator: MemoryValidator,
        transient_value: str,
    ):
        """Transient live prices and trade execution details must not be persisted."""
        is_valid, reason = validator.validate_candidate(
            user_id="user_123",
            memory_type="user_preference",
            key="market_note",
            value=transient_value,
        )
        assert is_valid is False
        assert "Live prices and trade transactions must not be stored" in (reason or "")

    # =========================================================================
    # 5. User Preference Precedence: Guardrails Always Win
    # =========================================================================
    def test_preferences_cannot_bypass_safety_guardrails(self):
        """Stored user preferences (e.g. 'I want penny stock tips') cannot override safety."""
        guardrail = GlobalSafetyGuardrail()

        # Malicious or prohibited query aligned with an aggressive user preference
        query = "Give me guaranteed return multi-bagger penny stock tips to double my money"
        decision = guardrail.evaluate(query)

        assert decision.is_safe is False
        assert decision.refusal_reason is not None
        assert "educational platform" in (decision.refusal_message or "")
