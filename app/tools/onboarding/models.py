"""
Data models for the Onboarding and System Help Tool.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CapabilityItem:
    """Description of a specialized capability in Finova AI."""
    domain: str
    name: str
    description: str
    example_prompts: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FAQItem:
    """Frequently asked question about Finova AI, privacy, safety, and memory."""
    id: str
    category: str
    question: str
    answer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
