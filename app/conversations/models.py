"""
Data models and DTOs for persistent conversations and chat history in Finova AI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.router.models import OrchestratorResponse


class Message(BaseModel):
    """A persisted message within a conversation."""
    message_id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: Literal["complete", "failed"] = "complete"
    metadata: dict[str, Any] | None = None


class Conversation(BaseModel):
    """Full representation of a conversation record."""
    conversation_id: str
    user_id: str
    title: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    domain: str | None = "general"


class ConversationSummary(BaseModel):
    """Lightweight summary of a conversation for list/sidebar views."""
    conversation_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    domain: str | None = "general"
    message_count: int = 0


class CreateConversationRequest(BaseModel):
    """Payload for explicitly creating a conversation."""
    user_id: str
    title: str | None = None
    domain: str | None = "general"


class UpdateConversationRequest(BaseModel):
    """Payload for updating conversation metadata, e.g. title."""
    user_id: str
    title: str


class AddMessageRequest(BaseModel):
    """Payload for directly adding a message to a conversation."""
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    status: Literal["complete", "failed"] = "complete"
    metadata: dict[str, Any] | None = None


class SendTurnRequest(BaseModel):
    """Payload for sending a user turn in an existing or new conversation."""
    user_id: str
    conversation_id: str | None = None
    query: str
    domain: str | None = None
    top_k: int | None = None
    score_threshold: float | None = None


class SendTurnResponse(BaseModel):
    """Response returned after processing a conversational turn."""
    conversation_id: str
    user_message: Message
    assistant_message: Message
    orchestrator_response: OrchestratorResponse | None = None


class ConversationDetailResponse(BaseModel):
    """Full conversation details including all ordered messages."""
    conversation: Conversation
    messages: list[Message]


class AssistantMessageMetadata(BaseModel):
    """
    Versioned persistence metadata for successful assistant messages.
    Persists only the fields required for frontend UI reconstruction of rich cards and citations,
    excluding redundant text fields (query, answer, static disclaimer).
    """
    schema_version: int = 1
    grounding_status: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    market_data: dict[str, Any] | None = None
    market_data_list: list[dict[str, Any]] = Field(default_factory=list)
    crypto_data: dict[str, Any] | None = None
    derivatives_data: dict[str, Any] | None = None
    portfolio_data: dict[str, Any] | None = None
    news_data: list[dict[str, Any]] | None = None
    quiz_data: dict[str, Any] | None = None
    onboarding_data: list[dict[str, Any]] | None = None
    grounding_sources: list[str] = Field(default_factory=list)
    domain_detected: str | None = None
    sub_tasks: list[dict[str, Any]] = Field(default_factory=list)
    agent_name: str | None = None
    model_used: str | None = None
    latency_ms: float | None = None
    topic: str | None = None
    related_concepts: list[str] = Field(default_factory=list)
    suggested_next: list[str] = Field(default_factory=list)


class FailedMessageMetadata(BaseModel):
    """Versioned persistence metadata for failed assistant turns."""
    schema_version: int = 1
    failed: bool = True
    error: str


def extract_assistant_metadata(orch_resp: OrchestratorResponse) -> dict[str, Any]:
    """
    Extract the versioned AssistantMessageMetadata payload from OrchestratorResponse.
    Explicitly omits query, answer, and disclaimer to prevent redundant storage.
    """
    dump = orch_resp.model_dump()
    meta = AssistantMessageMetadata(
        schema_version=1,
        grounding_status=dump.get("grounding_status"),
        citations=dump.get("citations", []),
        market_data=dump.get("market_data"),
        market_data_list=dump.get("market_data_list", []),
        crypto_data=dump.get("crypto_data"),
        derivatives_data=dump.get("derivatives_data"),
        portfolio_data=dump.get("portfolio_data"),
        news_data=dump.get("news_data"),
        quiz_data=dump.get("quiz_data"),
        onboarding_data=dump.get("onboarding_data"),
        grounding_sources=dump.get("grounding_sources", []),
        domain_detected=str(dump.get("domain_detected")) if dump.get("domain_detected") else None,
        sub_tasks=dump.get("sub_tasks", []),
        agent_name=dump.get("agent_name"),
        model_used=dump.get("model_used"),
        latency_ms=dump.get("latency_ms"),
        topic=dump.get("topic"),
        related_concepts=dump.get("related_concepts", []),
        suggested_next=dump.get("suggested_next", []),
    )
    return meta.model_dump()


def create_failed_metadata(error_msg: str) -> dict[str, Any]:
    """Create versioned metadata for failed assistant turns."""
    return FailedMessageMetadata(
        schema_version=1,
        failed=True,
        error=error_msg,
    ).model_dump()
