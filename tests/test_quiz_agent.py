"""
Tests for the Quiz & Challenge Agent.
Verifies question retrieval, 100% deterministic grading,
explanation formatting, and Phase 5 memory integration.
"""

from unittest.mock import MagicMock
import pytest

from app.agents.quiz.agent import QuizAgent, QuizAgentResult
from app.agents.quiz.prompts import QUIZ_DISCLAIMER
from app.memory.models import MemoryType
from app.tools.quiz.models import QuizQuestion, QuizSubmission
from app.tools.quiz.service import QuizService


@pytest.fixture
def sample_questions():
    return [
        QuizQuestion(
            id="q_eq_1",
            topic="equity",
            difficulty="beginner",
            question="What is equity?",
            options={"A": "Ownership", "B": "Debt", "C": "Option", "D": "Currency"},
            correct_option="A",
            explanation="Equity represents ownership in a company.",
            source_reference="SEBI",
        ),
        QuizQuestion(
            id="q_deriv_1",
            topic="derivatives",
            difficulty="intermediate",
            question="What is the maximum loss for a call buyer?",
            options={"A": "Unlimited", "B": "Premium paid", "C": "Strike price", "D": "Zero"},
            correct_option="B",
            explanation="The loss is capped at premium paid.",
            source_reference="NISM",
        ),
    ]


@pytest.fixture
def mock_memory_service():
    service = MagicMock()
    return service


@pytest.fixture
def agent(sample_questions, mock_memory_service):
    quiz_service = QuizService(questions=sample_questions)
    return QuizAgent(service=quiz_service, memory_service=mock_memory_service)


class TestQuizAgent:
    """Test Quiz presentation and grading workflows."""

    def test_present_questions_by_topic(self, agent):
        res = agent.ask("Quiz me on equity")
        assert isinstance(res, QuizAgentResult)
        assert res.mode == "presentation"
        assert res.grounding_status == "fully_grounded"
        assert res.questions is not None
        assert len(res.questions) == 1
        assert res.questions[0]["id"] == "q_eq_1"
        assert "What is equity?" in res.answer
        assert res.disclaimer == QUIZ_DISCLAIMER

    def test_evaluate_correct_answer(self, agent, mock_memory_service):
        res = agent.ask("Answer: A for q_eq_1", user_id="user_123")
        assert res.mode == "evaluation"
        assert res.evaluation is not None
        assert res.evaluation["score_percentage"] == 100.0
        assert res.evaluation["correct_count"] == 1
        assert "✅ Correct" in res.answer
        assert "Equity represents ownership in a company" in res.answer

        # Verify Phase 5 memory record call
        assert mock_memory_service.add_memory.called
        call_args = mock_memory_service.add_memory.call_args_list
        # Check that MemoryType is EDUCATIONAL_PROGRESS
        assert any(c.kwargs.get("memory_type") == "EDUCATIONAL_PROGRESS" for c in call_args)

    def test_evaluate_incorrect_answer_identifies_weak_topic(self, agent, mock_memory_service):
        res = agent.ask("q_deriv_1=A", user_id="user_123")
        assert res.mode == "evaluation"
        assert res.evaluation is not None
        assert res.evaluation["score_percentage"] == 0.0
        assert res.evaluation["correct_count"] == 0
        assert "❌ Incorrect (Correct: **B**)" in res.answer
        assert "derivatives" in res.evaluation["weak_areas"]

        # Verify weak topic written to memory
        call_args = mock_memory_service.add_memory.call_args_list
        weak_calls = [c for c in call_args if c.kwargs.get("key") == "weak_topic"]
        assert len(weak_calls) > 0
        assert weak_calls[0].kwargs.get("value") == "derivatives"

    def test_anonymous_quiz_does_not_crash_memory(self, agent, mock_memory_service):
        res = agent.ask("q_eq_1=A", user_id=None)
        assert res.mode == "evaluation"
        assert res.evaluation["score_percentage"] == 100.0
        # Should not write memory when user_id is None
        assert mock_memory_service.add_memory.call_count == 0
