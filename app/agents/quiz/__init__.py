"""
Quiz agent package.
"""

from app.agents.quiz.agent import QuizAgent, QuizAgentResult
from app.agents.quiz.prompts import QUIZ_DISCLAIMER, QUIZ_TUTOR_SYSTEM_PROMPT

__all__ = [
    "QuizAgent",
    "QuizAgentResult",
    "QUIZ_DISCLAIMER",
    "QUIZ_TUTOR_SYSTEM_PROMPT",
]
