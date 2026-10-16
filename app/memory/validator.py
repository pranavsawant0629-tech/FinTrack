"""
Memory validator and privacy guardrails for the Finova AI Memory Layer.
Strictly validates memory schemas and rejects sensitive financial data, credentials,
and personal identifiable information (PII).
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.memory.models import MemoryType

# Security Limits
MAX_KEY_LENGTH = 64
MAX_VALUE_LENGTH = 512
MAX_USER_MEMORIES = 50

# Regex Patterns for Sensitive Data Detection
CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE)
AADHAAR_REGEX = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PHONE_REGEX = re.compile(r"\b(?:\+91|91|0)?[6-9]\d{9}\b")
SECRET_KEYWORDS = re.compile(
    r"\b(?:password|passwd|secret|api[_-]?key|token|bearer|pin|cvv|otp|auth)\b",
    re.IGNORECASE,
)
ACCOUNT_KEYWORDS = re.compile(
    r"\b(?:account\s*(?:no|number)|a/c\s*(?:no|number)|bank\s*acc)\b",
    re.IGNORECASE,
)
TRANSIENT_MARKET_PATTERNS = re.compile(
    r"\b(?:trading\s+at|current\s+price|last\s+traded|bought\s+at|sold\s+at|portfolio\s+balance)\b",
    re.IGNORECASE,
)


class MemoryValidationError(Exception):
    """Raised when a memory candidate fails validation or privacy rules."""
    pass


class MemoryValidator:
    """Validates candidate memory items against privacy, security, and schema invariants."""

    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """Check whether text contains sensitive PII, account data, or credentials."""
        if SECRET_KEYWORDS.search(text):
            return True
        if ACCOUNT_KEYWORDS.search(text):
            return True
        if PAN_REGEX.search(text):
            return True
        if AADHAAR_REGEX.search(text):
            return True
        if PHONE_REGEX.search(text):
            return True
        # Check card number patterns (excluding typical years like 2024, 2025)
        for match in CARD_REGEX.finditer(text):
            digits = re.sub(r"\D", "", match.group(0))
            if 13 <= len(digits) <= 19:
                return True
        return False

    @classmethod
    def is_transient_market_data(cls, text: str) -> bool:
        """Check whether text contains transient live market prices or order execution details."""
        return bool(TRANSIENT_MARKET_PATTERNS.search(text))

    @classmethod
    def validate_candidate(
        cls,
        user_id: str,
        memory_type: MemoryType,
        key: str,
        value: Any,
        current_user_memory_count: int = 0,
        is_update: bool = False,
    ) -> tuple[bool, str | None]:
        """
        Validate candidate memory.
        Returns:
            (is_valid: bool, rejection_reason: str | None)
        """
        if not user_id or not user_id.strip():
            return False, "Persistent memory strictly requires an explicit, non-empty user_id."

        if not key or not key.strip():
            return False, "Memory key cannot be empty."

        if len(key) > MAX_KEY_LENGTH:
            return False, f"Memory key exceeds maximum length of {MAX_KEY_LENGTH} characters."

        # Serialize value for inspection
        val_str = value if isinstance(value, str) else json.dumps(value)

        if not val_str.strip():
            return False, "Memory value cannot be empty."

        if len(val_str) > MAX_VALUE_LENGTH:
            return False, f"Memory value exceeds maximum length of {MAX_VALUE_LENGTH} characters."

        if not is_update and current_user_memory_count >= MAX_USER_MEMORIES:
            return False, f"User memory quota reached ({MAX_USER_MEMORIES} records maximum)."

        combined_text = f"{key} {val_str}"

        # PII and Credential Check
        if cls.contains_sensitive_data(combined_text):
            return False, "Candidate rejected: Contains sensitive financial data, credentials, or PII."

        # Transient market price check
        if cls.is_transient_market_data(combined_text):
            return False, "Candidate rejected: Live prices and trade transactions must not be stored as memory."

        return True, None


memory_validator = MemoryValidator()
