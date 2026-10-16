"""
Data models for the Quiz and Knowledge Challenge Tool.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class QuizQuestion:
    """Individual financial education quiz question."""
    id: str
    topic: str
    difficulty: str
    question: str
    options: dict[str, str]
    correct_option: str
    explanation: str
    source_reference: str

    def to_user_dict(self) -> dict[str, Any]:
        """User-facing view without exposing the correct answer."""
        return {
            "id": self.id,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "question": self.question,
            "options": self.options,
        }

    def to_full_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuizSubmission:
    """User submission for grading."""
    question_id: str
    selected_option: str


@dataclass(frozen=True)
class QuizGradedItem:
    """Graded result for a single question."""
    question_id: str
    question_text: str
    selected_option: str
    correct_option: str
    is_correct: bool
    explanation: str
    source_reference: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuizEvaluationResult:
    """Summary of a completed quiz evaluation."""
    total_questions: int
    correct_count: int
    score_percentage: float
    topic: str
    graded_items: list[QuizGradedItem]
    weak_areas: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "score_percentage": self.score_percentage,
            "topic": self.topic,
            "graded_items": [i.to_dict() for i in self.graded_items],
            "weak_areas": self.weak_areas,
        }
