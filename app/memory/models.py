"""
Data contracts and Pydantic models for the Finova AI Memory & Personalization Layer.
Defines typed memory records, memory categories, and the unified user PersonalizationProfile.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


# Permitted Persistent Memory Types in Phase 5
MemoryType = Literal[
    "USER_PREFERENCE",
    "LEARNING_LEVEL",
    "LEARNING_GOAL",
    "INTEREST",
    "EDUCATIONAL_PROGRESS",
    "user_preference",
    "learning_level",
    "learning_goal",
    "interest",
    "educational_progress",
]

# Permitted Sources for Persistent Memory (Strictly No Inferred/Speculative LLM Sources)
MemorySource = Literal["explicit_user_statement", "system_default"]


class MemoryRecord(BaseModel):
    """Represents a single validated, typed unit of persistent user memory."""
    memory_id: str = Field(description="Unique identifier for the memory record (UUID4)")
    user_id: str = Field(description="Mandatory application-level user partition identifier")
    memory_type: MemoryType = Field(description="Categorical type of the memory item")
    key: str = Field(description="Unique attribute key within the user partition and memory type")
    value: Any = Field(description="Structured value or string payload")
    source: MemorySource = Field(
        default="explicit_user_statement",
        description="Origin provenance of memory; strictly explicit statements or system defaults",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    created_at: str = Field(description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(description="ISO 8601 UTC last update timestamp")
    expires_at: str | None = Field(default=None, description="Optional ISO 8601 UTC expiration timestamp")

    @field_validator("memory_type", mode="before")
    @classmethod
    def normalize_memory_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v


class PersonalizationProfile(BaseModel):
    """
    Active personalization profile assembled deterministically from active,
    unexpired user memories. Injected into pedagogical agent prompts.
    """
    user_id: str | None = Field(default=None, description="User identifier; None if ephemeral session mode")
    learning_level: Literal["beginner", "intermediate", "advanced"] | None = Field(
        default=None,
        description="Calibrated instructional depth (beginner, intermediate, or advanced)",
    )
    learning_goals: list[str] = Field(
        default_factory=list,
        description="Active educational objectives (e.g. 'options_trading', 'exam_prep')",
    )
    interests: list[str] = Field(
        default_factory=list,
        description="Declared asset or financial topics of interest (e.g. 'crypto', 'etfs')",
    )
    preferences: dict[str, str] = Field(
        default_factory=dict,
        description="User instructional preferences (e.g. 'explanation_style': 'concise')",
    )
    active_memories: list[MemoryRecord] = Field(
        default_factory=list,
        description="Underlying raw memory records contributing to this profile",
    )


def build_personalization_instruction(profile: PersonalizationProfile | None) -> str:
    """
    Build a concise instructional addendum for pedagogical LLM prompts based on user profile.
    Explicitly instructs the LLM to adapt tone/examples while NEVER altering financial facts,
    regulations, or calculations.
    """
    if not profile or not profile.user_id:
        return ""

    parts: list[str] = []
    if profile.learning_level == "beginner":
        parts.append(
            "- **Learner Profile:** Beginner level. Explain concepts using clear intuitive intuition, "
            "simple relatable analogies, and define any technical jargon simply."
        )
    elif profile.learning_level == "intermediate":
        parts.append(
            "- **Learner Profile:** Intermediate level. Provide structured explanations with "
            "practical market mechanics, key metrics, and standard terminology."
        )
    elif profile.learning_level == "advanced":
        parts.append(
            "- **Learner Profile:** Advanced level. Provide technically rigorous, comprehensive explanations "
            "including institutional nuances, quantitative formulas, and market edge cases."
        )

    if profile.learning_goals:
        clean_goals = ", ".join(
            str(g).replace("\r", " ").replace("\n", " ").strip()
            for g in profile.learning_goals[:3]
        )
        parts.append(f"- **Declared Learning Objectives:** {clean_goals}.")

    if profile.preferences:
        pref_items = [
            f"{str(k).replace(chr(13), ' ').replace(chr(10), ' ').strip()}: {str(v).replace(chr(13), ' ').replace(chr(10), ' ').strip()}"
            for k, v in list(profile.preferences.items())[:3]
        ]
        parts.append(f"- **Instructional Preferences:** {', '.join(pref_items)}.")

    if not parts:
        return ""

    header = "\n\n### Learner Personalization Guidelines (Educational Tone Only — Never Alter Financial Facts):\n"
    return header + "\n".join(parts)

