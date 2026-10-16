"""
Business logic service for conversation management, access control, and turn execution.
Enforces strict user ownership isolation (IDOR protection) and failure handling.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import HTTPException, status

from app.conversations.models import (
    Conversation,
    ConversationDetailResponse,
    ConversationSummary,
    Message,
    SendTurnResponse,
    create_failed_metadata,
    extract_assistant_metadata,
)
from app.conversations.store import (
    SQLiteConversationStore,
    conversation_store,
    generate_conversation_title,
)
from app.router.orchestrator import CentralOrchestrator, central_orchestrator

logger = logging.getLogger(__name__)


class ConversationService:
    """Service managing conversations, messages, bounded context, and transactional turns."""

    def __init__(
        self,
        store: SQLiteConversationStore | None = None,
        orchestrator: CentralOrchestrator | None = None,
    ) -> None:
        self.store = store or conversation_store
        self.orchestrator = orchestrator or central_orchestrator

    def verify_ownership(self, conversation_id: str, user_id: str) -> Conversation:
        """
        Verify that the conversation exists and belongs strictly to user_id.
        Raises 404 if not found, 403 if belonging to another user.
        """
        conv = self.store.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found",
            )
        if conv.user_id != user_id:
            logger.warning(
                "IDOR direct-access violation: user '%s' attempted to access conversation '%s' owned by '%s'",
                user_id,
                conversation_id,
                conv.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Conversation belongs to another user",
            )
        return conv

    def create_conversation(
        self,
        user_id: str,
        title: str | None = None,
        domain: str | None = "general",
    ) -> Conversation:
        """Explicitly create an empty conversation."""
        return self.store.create_conversation(user_id=user_id, title=title, domain=domain)

    def list_conversations(self, user_id: str, domain: str | None = None) -> list[ConversationSummary]:
        """List conversation summaries for a specific user, optionally filtered by domain."""
        return self.store.list_conversations(user_id=user_id, domain=domain)

    def get_conversation_detail(self, conversation_id: str, user_id: str) -> ConversationDetailResponse:
        """Fetch full conversation and messages with strict ownership check."""
        conv = self.verify_ownership(conversation_id=conversation_id, user_id=user_id)
        messages = self.store.get_messages(conversation_id)
        return ConversationDetailResponse(conversation=conv, messages=messages)

    def update_title(self, conversation_id: str, user_id: str, title: str) -> Conversation:
        """Update conversation title with ownership verification."""
        self.verify_ownership(conversation_id=conversation_id, user_id=user_id)
        updated = self.store.update_title(conversation_id, title)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title cannot be empty",
            )
        return updated

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete conversation and all messages with ownership verification."""
        self.verify_ownership(conversation_id=conversation_id, user_id=user_id)
        return self.store.delete_conversation(conversation_id)

    def clear_user_conversations(self, user_id: str) -> int:
        """Clear all conversations and messages for a user."""
        return self.store.clear_user_conversations(user_id=user_id.strip())

    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        msg_status: str = "complete",
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Directly add a message with ownership verification."""
        self.verify_ownership(conversation_id=conversation_id, user_id=user_id)
        return self.store.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            status=msg_status,
            metadata=metadata,
        )

    def send_turn(
        self,
        user_id: str,
        query: str,
        conversation_id: str | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
        domain: str | None = None,
    ) -> SendTurnResponse:
        """
        Execute an end-to-end conversational turn:
        1. If conversation_id is None, create new conversation record with domain.
           Else, verify ownership and keep the existing conversation's stored domain (immutable).
        2. Persist the user message (complete).
        3. Fetch bounded preceding history from DB for LLM continuation.
        4. Invoke central orchestrator with domain_context.
        5. Persist assistant response (complete on success, failed on error).
        6. Return unified result.
        """
        trimmed_query = query.strip()
        if not trimmed_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty",
            )

        # 1. Resolve or create conversation
        if conversation_id:
            conv = self.verify_ownership(conversation_id=conversation_id, user_id=user_id)
            target_conv_id = conv.conversation_id
            # Invariant: Stored conversation domain is authoritative and immutable!
            # Never overwrite or mutate stored domain based on active UI section.
            target_domain = conv.domain or "general"
        else:
            # Deterministic title from first message; assign domain from selected tutor
            title = generate_conversation_title(trimmed_query)
            target_domain = (domain or "general").strip().lower()
            conv = self.store.create_conversation(user_id=user_id, title=title, domain=target_domain)
            target_conv_id = conv.conversation_id

        # 2. Retrieve bounded history from persistent store BEFORE adding the new user message
        # Bounded to last 6 completed messages to keep local model context tight
        preceding_history = self.store.get_bounded_history(target_conv_id, max_turns=6)

        # 3. Persist the user message
        user_msg = self.store.add_message(
            conversation_id=target_conv_id,
            role="user",
            content=trimmed_query,
            status="complete",
        )

        # 4. Invoke orchestrator with preceding history and domain_context
        try:
            orch_resp = self.orchestrator.ask(
                query=trimmed_query,
                user_id=user_id,
                conversation_history=preceding_history,
                top_k=top_k,
                score_threshold=score_threshold,
                domain_context=target_domain,
            )
            # 5A. Success: Persist assistant message with versioned, non-redundant metadata
            meta = extract_assistant_metadata(orch_resp)
            assistant_msg = self.store.add_message(
                conversation_id=target_conv_id,
                role="assistant",
                content=orch_resp.answer,
                status="complete",
                metadata=meta,
            )
            return SendTurnResponse(
                conversation_id=target_conv_id,
                user_message=user_msg,
                assistant_message=assistant_msg,
                orchestrator_response=orch_resp,
            )
        except Exception as exc:
            logger.error("Orchestrator turn execution failed: %s", exc, exc_info=True)
            # 5B. Failure Handling: Persist failed assistant turn so turn is not orphaned
            failed_error_text = (
                "Finova AI encountered a temporary issue generating a response. "
                "Your inquiry was safely saved, and you can retry."
            )
            failed_meta = create_failed_metadata(str(exc))
            assistant_msg = self.store.add_message(
                conversation_id=target_conv_id,
                role="assistant",
                content=failed_error_text,
                status="failed",
                metadata=failed_meta,
            )
            return SendTurnResponse(
                conversation_id=target_conv_id,
                user_message=user_msg,
                assistant_message=assistant_msg,
                orchestrator_response=None,
            )


conversation_service = ConversationService()
