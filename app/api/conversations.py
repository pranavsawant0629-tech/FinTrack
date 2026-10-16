"""
FastAPI REST router for Conversation Persistence & Chat History.
Provides CRUD and transactional turn endpoints with strict server-side ownership isolation.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from app.conversations.models import (
    AddMessageRequest,
    Conversation,
    ConversationDetailResponse,
    ConversationSummary,
    CreateConversationRequest,
    Message,
    SendTurnRequest,
    SendTurnResponse,
    UpdateConversationRequest,
)
from app.conversations.service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations & History"])


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: CreateConversationRequest) -> Conversation:
    """Create a new persistent conversation."""
    return conversation_service.create_conversation(
        user_id=payload.user_id,
        title=payload.title,
        domain=payload.domain,
    )


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    user_id: str = Query(..., description="Owner user ID to filter conversations"),
    domain: str | None = Query(default=None, description="Optional domain to filter conversations"),
) -> list[ConversationSummary]:
    """List all conversations belonging to the specified user, optionally filtered by domain."""
    return conversation_service.list_conversations(user_id=user_id, domain=domain)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="Owner user ID verifying access"),
) -> ConversationDetailResponse:
    """
    Get full conversation details and ordered messages.
    Rejects requests with 403 if the conversation belongs to another user.
    """
    return conversation_service.get_conversation_detail(
        conversation_id=conversation_id,
        user_id=user_id,
    )


@router.post("/send", response_model=SendTurnResponse)
def send_turn(payload: SendTurnRequest) -> SendTurnResponse:
    """
    Execute a conversational turn:
    - Auto-creates conversation on first message if conversation_id is None.
    - Persists user message.
    - Supplies bounded preceding history from DB to the central orchestrator.
    - Persists assistant response (or failed turn state).
    - Preserves conversation integrity and prevents orphaned messages on failure.
    """
    return conversation_service.send_turn(
        user_id=payload.user_id,
        query=payload.query,
        conversation_id=payload.conversation_id,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        domain=payload.domain,
    )


@router.post("/{conversation_id}/messages", response_model=Message)
def add_message(
    conversation_id: str,
    payload: AddMessageRequest,
) -> Message:
    """Persist a message into the conversation with ownership check."""
    return conversation_service.add_message(
        conversation_id=conversation_id,
        user_id=payload.user_id,
        role=payload.role,
        content=payload.content,
        msg_status=payload.status,
        metadata=payload.metadata,
    )


@router.patch("/{conversation_id}", response_model=Conversation)
def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
) -> Conversation:
    """Update conversation title or metadata with ownership check."""
    return conversation_service.update_title(
        conversation_id=conversation_id,
        user_id=payload.user_id,
        title=payload.title,
    )


@router.delete("", response_model=dict[str, Any])
def clear_user_conversations(
    user_id: str = Query(..., description="Owner user ID verifying deletion"),
) -> dict[str, Any]:
    """Clear all persistent conversations and history for a user."""
    clean_user = user_id.strip()
    if not clean_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must not be empty",
        )
    count = conversation_service.clear_user_conversations(user_id=clean_user)
    return {"status": "cleared", "user_id": clean_user, "deleted_count": count}


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="Owner user ID verifying deletion"),
) -> dict[str, Any]:
    """Delete a conversation and cascade delete its messages with ownership check."""
    conversation_service.delete_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
    )
    return {"status": "deleted", "conversation_id": conversation_id}
