"""
Quiz Service for Finova AI.
Coordinates question retrieval, 100% deterministic grading, and records
educational progress strictly via Phase 5 MemoryType.EDUCATIONAL_PROGRESS.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.memory.models import MemorySource, MemoryType
from app.tools.quiz.models import (
    QuizEvaluationResult,
    QuizGradedItem,
    QuizQuestion,
    QuizSubmission,
)

logger = logging.getLogger(__name__)

DEFAULT_QUESTIONS_FILE = Path("data/quiz/questions.json")


class QuizService:
    """Provides curated educational quizzes and deterministic grading."""

    def __init__(
        self,
        questions_path: Path | str = DEFAULT_QUESTIONS_FILE,
        questions: list[QuizQuestion] | None = None,
    ) -> None:
        if questions is not None:
            self._questions = questions
        else:
            self._questions = self._load_questions(Path(questions_path))

    def _load_questions(self, path: Path) -> list[QuizQuestion]:
        if not path.exists():
            logger.warning("Quiz questions file not found at %s. Initializing empty.", path)
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            return [
                QuizQuestion(
                    id=item["id"],
                    topic=item["topic"],
                    difficulty=item["difficulty"],
                    question=item["question"],
                    options=item["options"],
                    correct_option=item["correct_option"],
                    explanation=item["explanation"],
                    source_reference=item.get("source_reference", "Finova Educational Material"),
                )
                for item in raw_data
            ]
        except Exception as exc:
            logger.error("Failed to parse quiz questions from %s: %s", path, exc)
            return []

    def get_questions(
        self,
        topic: str | None = None,
        difficulty: str | None = None,
        limit: int = 5,
    ) -> list[QuizQuestion]:
        """Retrieve questions filtered by topic and/or difficulty."""
        filtered = self._questions

        if topic and topic.strip().lower() != "all":
            clean_topic = topic.strip().lower()
            filtered = [q for q in filtered if q.topic.lower() == clean_topic]

        if difficulty:
            clean_diff = difficulty.strip().lower()
            filtered = [q for q in filtered if q.difficulty.lower() == clean_diff]

        return filtered[:limit]

    def get_question_by_id(self, question_id: str) -> QuizQuestion | None:
        for q in self._questions:
            if q.id == question_id:
                return q
        return None

    def evaluate_answers(
        self,
        submissions: list[QuizSubmission],
        user_id: str | None = None,
        memory_service: Any = None,
    ) -> QuizEvaluationResult:
        """
        Deterministically evaluate submissions and record educational progress
        strictly within Phase 5 schema (MemoryType.EDUCATIONAL_PROGRESS).
        """
        if not submissions:
            return QuizEvaluationResult(
                total_questions=0,
                correct_count=0,
                score_percentage=0.0,
                topic="none",
                graded_items=[],
                weak_areas=[],
            )

        graded_items: list[QuizGradedItem] = []
        correct_count = 0
        topics_seen: set[str] = set()
        weak_topics: set[str] = set()

        for sub in submissions:
            q = self.get_question_by_id(sub.question_id)
            if not q:
                continue

            topics_seen.add(q.topic)
            is_correct = sub.selected_option.strip().upper() == q.correct_option.strip().upper()
            if is_correct:
                correct_count += 1
            else:
                weak_topics.add(q.topic)

            graded_items.append(
                QuizGradedItem(
                    question_id=q.id,
                    question_text=q.question,
                    selected_option=sub.selected_option.strip().upper(),
                    correct_option=q.correct_option.strip().upper(),
                    is_correct=is_correct,
                    explanation=q.explanation,
                    source_reference=q.source_reference,
                )
            )

        total = len(graded_items)
        score_pct = round((correct_count / total) * 100.0, 1) if total > 0 else 0.0
        primary_topic = list(topics_seen)[0] if len(topics_seen) == 1 else "multi_topic"

        result = QuizEvaluationResult(
            total_questions=total,
            correct_count=correct_count,
            score_percentage=score_pct,
            topic=primary_topic,
            graded_items=graded_items,
            weak_areas=sorted(list(weak_topics)),
        )

        # Record progress to Phase 5 memory if user_id and memory_service provided
        if user_id and memory_service is not None:
            self._record_memory_progress(user_id, result, memory_service)

        return result

    def _record_memory_progress(
        self,
        user_id: str,
        result: QuizEvaluationResult,
        memory_service: Any,
    ) -> None:
        """Record progress strictly using Phase 5 MemoryType.EDUCATIONAL_PROGRESS."""
        try:
            # 1. Record score
            memory_service.add_memory(
                user_id=user_id,
                memory_type="EDUCATIONAL_PROGRESS",
                key=f"quiz_score_{result.topic}",
                value=f"{result.score_percentage}% ({result.correct_count}/{result.total_questions})",
                source="explicit_user_statement",
            )

            # 2. Record weak topic if score < 60%
            if result.score_percentage < 60.0 and result.weak_areas:
                for weak in result.weak_areas:
                    memory_service.add_memory(
                        user_id=user_id,
                        memory_type="EDUCATIONAL_PROGRESS",
                        key="weak_topic",
                        value=weak,
                        source="explicit_user_statement",
                    )
            # 3. Record mastery if >= 80%
            elif result.score_percentage >= 80.0:
                memory_service.add_memory(
                    user_id=user_id,
                    memory_type="EDUCATIONAL_PROGRESS",
                    key="completed_topic",
                    value=result.topic,
                    source="explicit_user_statement",
                )
        except Exception as exc:
            logger.warning("Failed to record quiz progress to memory: %s", exc)
