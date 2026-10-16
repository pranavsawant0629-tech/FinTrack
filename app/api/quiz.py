"""
FastAPI router for the Quiz & Challenge Agent.
Exposes GET /agents/quiz/questions, POST /agents/quiz/submit, and POST /agents/quiz/ask.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.quiz.agent import QuizAgent
from app.memory.service import memory_service
from app.tools.quiz.models import QuizSubmission
from app.tools.quiz.service import QuizService

router = APIRouter()
_quiz_service = QuizService()
_quiz_agent = QuizAgent(service=_quiz_service, memory_service=memory_service)


class QuizQueryRequest(BaseModel):
    query: str
    user_id: str | None = None


class SubmissionItem(BaseModel):
    question_id: str
    selected_option: str


class QuizSubmitRequest(BaseModel):
    submissions: list[SubmissionItem]
    user_id: str | None = None


@router.get("/questions")
def get_quiz_questions(topic: str | None = None, difficulty: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve multiple-choice questions for financial self-assessment."""
    questions = _quiz_service.get_questions(topic=topic, difficulty=difficulty, limit=limit)
    return [q.to_user_dict() for q in questions]


@router.post("/submit")
def submit_quiz_answers(payload: QuizSubmitRequest) -> dict[str, Any]:
    """Deterministically grade quiz answers and record Phase 5 educational progress."""
    subs = [QuizSubmission(question_id=s.question_id, selected_option=s.selected_option) for s in payload.submissions]
    result = _quiz_service.evaluate_answers(
        submissions=subs,
        user_id=payload.user_id,
        memory_service=memory_service,
    )
    return result.to_dict()


@router.post("/ask")
def ask_quiz(payload: QuizQueryRequest) -> dict[str, Any]:
    """Query the Quiz & Knowledge Challenge Tutor."""
    res = _quiz_agent.ask(query=payload.query, user_id=payload.user_id)
    return res.to_dict()
