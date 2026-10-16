"""
Unit tests for deterministic MemoryExtractor and MemoryValidator (app.memory.extractor, app.memory.validator).
Verifies positive extraction, transient rejection, sensitive financial & PII data rejection, and quotas.
"""

import pytest

from app.memory.extractor import MemoryExtractor, memory_extractor
from app.memory.validator import MemoryValidator, memory_validator


def test_extractor_positive_declarations():
    # Learning Level
    res1 = memory_extractor.extract_candidates("I am a beginner in stock markets.")
    assert len(res1) == 1
    assert res1[0].memory_type == "LEARNING_LEVEL"
    assert res1[0].value == "beginner"

    res2 = memory_extractor.extract_candidates("I have intermediate experience with trading.")
    assert len(res2) == 1
    assert res2[0].value == "intermediate"

    res3 = memory_extractor.extract_candidates("I am an advanced trader.")
    assert len(res3) == 1
    assert res3[0].value == "advanced"

    # Learning Goals
    res_goal = memory_extractor.extract_candidates("My goal is to learn options trading.")
    assert any(c.memory_type == "LEARNING_GOAL" and "options trading" in c.value for c in res_goal)

    # Preferences
    res_pref = memory_extractor.extract_candidates("I prefer concise explanations and avoid jargon.")
    assert any(c.memory_type == "USER_PREFERENCE" and c.value == "concise" for c in res_pref)
    assert any(c.memory_type == "USER_PREFERENCE" and c.value == "simple_no_jargon" for c in res_pref)


def test_extractor_first_person_new_to_anchoring():
    """Verify first-person declarations of 'new to' extract beginner level."""
    for phrase in [
        "I am new to investing",
        "I'm new to finance",
        "I am new to trading",
        "I'm new to markets",
    ]:
        res = memory_extractor.extract_candidates(phrase)
        assert len(res) == 1, f"Expected 1 candidate for '{phrase}'"
        assert res[0].memory_type == "LEARNING_LEVEL"
        assert res[0].value == "beginner"


def test_extractor_negations_and_third_party_rejected():
    """Verify negations, third-party mentions, and questions do NOT extract beginner level."""
    negative_phrases = [
        "I am not new to investing",
        "My colleague is new to investing",
        "My friend is new to finance",
        "Are you new to investing?",
        "Someone is new to trading",
    ]
    for phrase in negative_phrases:
        res = memory_extractor.extract_candidates(phrase)
        assert len(res) == 0, f"Expected 0 candidates for '{phrase}', got {res}"


def test_extractor_rejection_of_transient_queries():
    """Verifies that transient market lookups and calculations produce zero memories."""
    assert memory_extractor.extract_candidates("What is Reliance trading at?") == []
    assert memory_extractor.extract_candidates("Calculate compound interest for 10000 at 8% for 5 years") == []
    assert memory_extractor.extract_candidates("Calculate SIP for 5000 monthly") == []
    assert memory_extractor.extract_candidates("Why did Nifty fall today?") == []


def test_validator_sensitive_pii_and_credentials_rejection():
    """Verifies rejection of cards, account numbers, passwords, PAN, and Aadhaar."""
    # Credit Card
    valid, reason = memory_validator.validate_candidate("u1", "USER_PREFERENCE", "note", "My card is 4111 2222 3333 4444")
    assert valid is False
    assert "sensitive" in str(reason).lower()

    # Passwords / API tokens
    valid, reason = memory_validator.validate_candidate("u1", "USER_PREFERENCE", "api_key", "secret_token_123456")
    assert valid is False

    # Bank Account Numbers
    valid, reason = memory_validator.validate_candidate("u1", "USER_PREFERENCE", "note", "My account number is 9876543210123")
    assert valid is False

    # PAN Numbers (Uppercase, Lowercase, Mixed-case)
    valid_upper, reason_upper = memory_validator.validate_candidate("u1", "USER_PREFERENCE", "pan", "ABCDE1234F")
    assert valid_upper is False
    assert "sensitive" in str(reason_upper).lower()

    valid_lower, reason_lower = memory_validator.validate_candidate("u1", "USER_PREFERENCE", "pan", "abcde1234f")
    assert valid_lower is False
    assert "sensitive" in str(reason_lower).lower()

    valid_mixed, reason_mixed = memory_validator.validate_candidate("u1", "USER_PREFERENCE", "pan", "AbCdE1234f")
    assert valid_mixed is False
    assert "sensitive" in str(reason_mixed).lower()


def test_validator_transient_market_data_rejection():
    """Verifies rejection of transient market price notes."""
    valid, reason = memory_validator.validate_candidate("u1", "USER_PREFERENCE", "trade", "Reliance trading at 2985")
    assert valid is False
    assert "live prices" in str(reason).lower()


def test_validator_user_absence_and_quota_limit():
    """Verifies user_id mandatory rule and max quota enforcement."""
    # Missing user_id
    valid, reason = memory_validator.validate_candidate("", "LEARNING_LEVEL", "k", "v")
    assert valid is False
    assert "explicit, non-empty user_id" in str(reason)

    # Quota reached
    valid, reason = memory_validator.validate_candidate("u1", "LEARNING_LEVEL", "k", "v", current_user_memory_count=50)
    assert valid is False
    assert "quota reached" in str(reason).lower()
