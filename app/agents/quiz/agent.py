"""
Quiz Agent for Finova AI.
Coordinates financial literacy quizzes, handles user answers, performs deterministic grading,
and tracks learning progress via Phase 5 memory.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from app.agents.quiz.prompts import QUIZ_DISCLAIMER, QUIZ_TUTOR_SYSTEM_PROMPT
from app.tools.quiz.models import (
    QuizEvaluationResult,
    QuizQuestion,
    QuizSubmission,
)
from app.tools.quiz.service import QuizService

logger = logging.getLogger(__name__)

TOPIC_KEYWORDS = {
    "equity": ["equity", "stock", "shares", "pe ratio", "p/e", "dividend", "valuation"],
    "derivatives": ["derivative", "derivatives", "option", "options", "futures", "call", "put", "strike", "f&o"],
    "personal_finance": ["personal finance", "budget", "50/30/20", "tax", "income tax", "80c", "emergency fund"],
    "crypto": ["crypto", "cryptocurrency", "bitcoin", "vda", "virtual digital asset"],
    "portfolio": ["portfolio", "asset allocation", "diversification", "beta", "rebalancing"],
    "regulations": ["sebi", "rbi", "regulation", "regulations", "scores", "compliance", "rules"],
}


@dataclass(frozen=True)
class QuizAgentResult:
    """Standardized result from the Quiz Agent."""
    query: str
    answer: str
    mode: str
    grounding_status: str
    grounding_sources: list[str]
    disclaimer: str
    questions: list[dict[str, Any]] | None = None
    evaluation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "mode": self.mode,
            "grounding_status": self.grounding_status,
            "grounding_sources": self.grounding_sources,
            "disclaimer": self.disclaimer,
            "questions": self.questions,
            "evaluation": self.evaluation,
        }


class QuizAgent:
    """Agent conducting financial education assessments and knowledge challenges."""

    def __init__(
        self,
        service: QuizService | None = None,
        memory_service: Any = None,
        llm: Any = None,
    ) -> None:
        self._service = service or QuizService()
        self._memory_service = memory_service
        self._llm = llm

    def _detect_topic(self, query: str) -> str | None:
        low = query.lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(k in low for k in keywords):
                return topic
        return None

    def _detect_difficulty(self, query: str) -> str | None:
        low = query.lower()
        if "beginner" in low or "easy" in low or "basic" in low:
            return "beginner"
        if "intermediate" in low or "medium" in low:
            return "intermediate"
        if "advanced" in low or "hard" in low:
            return "advanced"
        return None

    def _parse_submissions(self, query: str) -> list[QuizSubmission]:
        """Extract question ID and option pairs from queries like 'eq_beg_1=A' or 'Answer: A for eq_beg_1'."""
        submissions: list[QuizSubmission] = []
        # Pattern 1: eq_beg_1 = A or eq_beg_1: A
        p1 = re.findall(r"\b([a-zA-Z0-9_]+)\s*[:=]\s*([A-Da-d])\b", query)
        for q_id, opt in p1:
            if self._service.get_question_by_id(q_id):
                submissions.append(QuizSubmission(question_id=q_id, selected_option=opt.upper()))

        if submissions:
            return submissions

        # Pattern 2: Answer: A for eq_beg_1 or Option A for eq_beg_1
        p2 = re.findall(r"\b(?:answer|option|choice)\s*[:]?\s*([A-Da-d])\s*(?:for\s+([a-zA-Z0-9_]+))\b", query, re.IGNORECASE)
        for opt, q_id in p2:
            if self._service.get_question_by_id(q_id):
                submissions.append(QuizSubmission(question_id=q_id, selected_option=opt.upper()))

        return submissions

    def ask(self, query: str, user_id: str | None = None) -> QuizAgentResult:
        """Process quiz requests or answer evaluations."""
        # Check if query is submitting an answer
        submissions = self._parse_submissions(query)
        if submissions:
            eval_res = self._service.evaluate_answers(
                submissions=submissions,
                user_id=user_id,
                memory_service=self._memory_service,
            )
            answer_text = self._format_evaluation_report(eval_res)
            return QuizAgentResult(
                query=query,
                answer=answer_text,
                mode="evaluation",
                grounding_status="fully_grounded",
                grounding_sources=["quiz_service", "sebi_nism_curriculum"],
                disclaimer=QUIZ_DISCLAIMER,
                evaluation=eval_res.to_dict(),
            )

        # Otherwise, present quiz questions
        topic = self._detect_topic(query)
        difficulty = self._detect_difficulty(query)

        questions = self._service.get_questions(topic=topic, difficulty=difficulty, limit=3)
        if not questions:
            # Fallback to any questions
            questions = self._service.get_questions(limit=3)

        answer_text = self._format_questions_presentation(questions, topic=topic)

        return QuizAgentResult(
            query=query,
            answer=answer_text,
            mode="presentation",
            grounding_status="fully_grounded",
            grounding_sources=["quiz_service"],
            disclaimer=QUIZ_DISCLAIMER,
            questions=[q.to_user_dict() for q in questions],
        )

    def _format_questions_presentation(self, questions: list[QuizQuestion], topic: str | None) -> str:
        topic_title = topic.replace("_", " ").title() if topic else "General Financial Education"
        lines: list[str] = [
            f"### 🎯 Finova Knowledge Challenge: {topic_title}",
            "Test your knowledge! Reply with your answer (e.g., `Answer: A for question_id` or `question_id=A`).\n",
        ]

        for idx, q in enumerate(questions, start=1):
            lines.append(f"**Question {idx} (ID: `{q.id}`)** [{q.difficulty.upper()}]")
            lines.append(f"{q.question}\n")
            for opt_key, opt_val in sorted(q.options.items()):
                lines.append(f"- **{opt_key})** {opt_val}")
            lines.append("")

        lines.append(f"*{QUIZ_DISCLAIMER}*")
        return "\n".join(lines)

    def _format_evaluation_report(self, eval_res: QuizEvaluationResult) -> str:
        lines: list[str] = [
            f"### 📊 Quiz Evaluation Report",
            f"**Score:** `{eval_res.correct_count}/{eval_res.total_questions}` ({eval_res.score_percentage}%)\n",
        ]

        for idx, item in enumerate(eval_res.graded_items, start=1):
            status = "✅ Correct" if item.is_correct else f"❌ Incorrect (Correct: **{item.correct_option}**)"
            lines.append(f"**Question {idx} (`{item.question_id}`):** {status}")
            lines.append(f"- **Your Answer:** {item.selected_option}")
            lines.append(f"- **Explanation:** {item.explanation}")
            lines.append(f"- **Reference:** *{item.source_reference}*\n")

        if eval_res.weak_areas:
            lines.append(f"💡 **Recommended Review Topics:** {', '.join(eval_res.weak_areas).title()}")

        lines.append(f"\n*{QUIZ_DISCLAIMER}*")
        return "\n".join(lines)
