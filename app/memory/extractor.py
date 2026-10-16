"""
Deterministic candidate extractor for the Finova AI Memory Layer.
Identifies explicit user statements regarding learning levels, goals, interests,
and pedagogical preferences without LLM speculation.
"""

from __future__ import annotations

import re
from typing import NamedTuple
from app.memory.models import MemoryType


class ExtractedCandidate(NamedTuple):
    memory_type: MemoryType
    key: str
    value: str


# Regex matchers for explicit declarations
BEGINNER_PATTERNS = [
    re.compile(r"\b(?:i\s+am|i'm|i\s+am\s+a|i'm\s+a)\s+(?!not\b)\s*beginner\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+am|i'm)\s+(?!not\b)\s*new\s+to\s+(?:investing|finance|trading|markets?)\b", re.IGNORECASE),
    re.compile(r"\b(?:explain\s+like\s+i'm\s+new|no\s+financial\s+background)\b", re.IGNORECASE),
    re.compile(r"\b(?:prefer|want|have)\s+beginner[- ](?:level|experience|knowledge)\b", re.IGNORECASE),
]

INTERMEDIATE_PATTERNS = [
    re.compile(r"\b(?:i\s+am|i'm|i\s+am\s+an|i'm\s+an)\s+intermediate\b", re.IGNORECASE),
    re.compile(r"\b(?:some|moderate)\s+experience\s+with\s+(?:stocks|investing|trading)\b", re.IGNORECASE),
    re.compile(r"\b(?:prefer|want|have)\s+intermediate[- ](?:level|experience|knowledge)\b", re.IGNORECASE),
]

ADVANCED_PATTERNS = [
    re.compile(r"\b(?:i\s+am|i'm|i\s+am\s+an|i'm\s+an)\s+advanced\b", re.IGNORECASE),
    re.compile(r"\b(?:experienced|professional|expert)\s+(?:trader|investor)\b", re.IGNORECASE),
    re.compile(r"\b(?:prefer|want|have)\s+advanced[- ](?:level|experience|knowledge)\b", re.IGNORECASE),
]

GOAL_PATTERNS = [
    re.compile(r"\b(?:my\s+goal\s+is\s+to|i\s+want\s+to\s+learn|aiming\s+to\s+learn)\s+([a-z0-9\s\-]+?)(?:\.|$|,|and\b)", re.IGNORECASE),
    re.compile(r"\b(?:preparing\s+for\s+(?:a|an)?\s*)([a-z0-9\s\-]+?\s*(?:exam|certification|test))", re.IGNORECASE),
    re.compile(r"\b(?:focus\s+on\s+)(long[- ]term\s+wealth(?:\s+accumulation)?|retirement\s+planning|value\s+investing)", re.IGNORECASE),
]

INTEREST_PATTERNS = [
    re.compile(r"\b(?:interested\s+in|curious\s+about)\s+([a-z0-9\s\-]+?)(?:\.|$|,|and\b)", re.IGNORECASE),
    re.compile(r"\b(?:want\s+to\s+focus\s+on)\s+([a-z0-9\s\-]+?)(?:\.|$|,|and\b)", re.IGNORECASE),
]

PREFERENCE_PATTERNS = [
    (re.compile(r"\b(?:prefer|like)\s+concise\s+(?:answers|explanations?)\b", re.IGNORECASE), "explanation_style", "concise"),
    (re.compile(r"\b(?:prefer|like)\s+detailed\s+(?:answers|explanations?)\b", re.IGNORECASE), "explanation_style", "detailed"),
    (re.compile(r"\b(?:use|prefer)\s+(?:simple\s+)?analogies\b", re.IGNORECASE), "pedagogy_style", "analogies"),
    (re.compile(r"\b(?:use|prefer)\s+bullet\s+points?\b", re.IGNORECASE), "format_style", "bullet_points"),
    (re.compile(r"\bavoid\s+jargon\b", re.IGNORECASE), "vocabulary_style", "simple_no_jargon"),
]


class MemoryExtractor:
    """Extracts explicit, deterministic memory candidates from user input."""

    @classmethod
    def is_pure_transient_query(cls, text: str) -> bool:
        """Identifies transient market quotes or calculations that must never produce persistent memories."""
        lower = text.lower().strip()
        if any(w in lower for w in ["trading at", "price of", "calculate", "how much will", "split for"]):
            # Unless there is an explicit declaration like "I am a beginner and what is..."
            if not any(decl in lower for decl in ["i am ", "i'm ", "my goal", "i prefer", "preparing for"]):
                return True
        return False

    @classmethod
    def extract_candidates(cls, text: str) -> list[ExtractedCandidate]:
        """
        Extract memory candidates from explicit user statements.
        Returns a list of ExtractedCandidate tuples.
        """
        if not text or not text.strip():
            return []

        if cls.is_pure_transient_query(text):
            return []

        candidates: list[ExtractedCandidate] = []
        cleaned = text.strip()

        # 1. Learning Level
        if any(p.search(cleaned) for p in BEGINNER_PATTERNS):
            candidates.append(ExtractedCandidate("LEARNING_LEVEL", "learning_level", "beginner"))
        elif any(p.search(cleaned) for p in INTERMEDIATE_PATTERNS):
            candidates.append(ExtractedCandidate("LEARNING_LEVEL", "learning_level", "intermediate"))
        elif any(p.search(cleaned) for p in ADVANCED_PATTERNS):
            candidates.append(ExtractedCandidate("LEARNING_LEVEL", "learning_level", "advanced"))

        # 2. Learning Goals
        for pattern in GOAL_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                goal_val = match.group(1).strip().lower()
                # Exclude trivial/generic words
                if len(goal_val) > 3 and goal_val not in ["something", "finance", "it", "this"]:
                    candidates.append(ExtractedCandidate("LEARNING_GOAL", "primary_goal", goal_val))
                    break

        # 3. Interests
        for pattern in INTEREST_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                topic = match.group(1).strip().lower()
                if len(topic) > 3 and topic not in ["something", "everything", "finance", "this"]:
                    candidates.append(ExtractedCandidate("INTEREST", f"interest_{topic.replace(' ', '_')[:20]}", topic))

        # 4. Preferences
        for pattern, pref_key, pref_val in PREFERENCE_PATTERNS:
            if pattern.search(cleaned):
                candidates.append(ExtractedCandidate("USER_PREFERENCE", pref_key, pref_val))

        return candidates


memory_extractor = MemoryExtractor()
