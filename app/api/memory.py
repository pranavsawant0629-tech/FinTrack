"""
FastAPI router for User Memory & Personalization.
Exposes CRUD and Right-to-be-Forgotten endpoints for TradeWise.
"""

from typing import Literal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.memory.models import MemoryRecord, MemoryType, PersonalizationProfile
from app.memory.service import memory_service
from app.memory.validator import MemoryValidationError

router = APIRouter(prefix="/memory", tags=["User Memory"])


class CreateMemoryRequest(BaseModel):
    user_id: str = Field(..., description="TradeWise application-level user identity")
    memory_type: MemoryType = Field(..., description="Category of memory")
    key: str = Field(..., max_length=64, description="Memory identifier key")
    value: str = Field(..., max_length=512, description="Memory value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    ttl_seconds: int | None = Field(default=None, description="Optional time-to-live in seconds")


class UpdateProfileRequest(BaseModel):
    user_id: str = Field(..., description="TradeWise application-level user identity")
    learning_level: Literal["beginner", "intermediate", "advanced"] | None = Field(default=None)
    learning_goals: list[str] | None = Field(default=None)
    interests: list[str] | None = Field(default=None)
    preferences: dict[str, str] | None = Field(default=None)


class MemoryListResponse(BaseModel):
    user_id: str
    memories: list[MemoryRecord]
    count: int


class MemoryDeleteResponse(BaseModel):
    status: str
    memory_id: str


class MemoryClearResponse(BaseModel):
    status: str
    user_id: str
    deleted_count: int


@router.get("/profile", response_model=PersonalizationProfile)
def get_user_profile(
    user_id: str = Query(..., description="User identity for profile retrieval"),
) -> PersonalizationProfile:
    """Retrieve unified pedagogical learner profile (learning level, goals, interests, preferences)."""
    if not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must not be empty",
        )
    return memory_service.retrieve_profile(user_id=user_id)


@router.post("/profile", response_model=PersonalizationProfile)
def update_user_profile(payload: UpdateProfileRequest) -> PersonalizationProfile:
    """Update a user's learning preferences and personalization profile with safety validation."""
    if not payload.user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must not be empty",
        )
    try:
        return memory_service.update_profile(
            user_id=payload.user_id,
            learning_level=payload.learning_level,
            learning_goals=payload.learning_goals,
            interests=payload.interests,
            preferences=payload.preferences,
        )
    except MemoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {exc}",
        )


@router.get("", response_model=MemoryListResponse)
def list_memories(
    user_id: str = Query(..., description="TradeWise application-level user identity"),
    memory_type: MemoryType | None = Query(default=None, description="Optional filter by memory category"),
) -> MemoryListResponse:
    """Retrieve all active memories for a given user, optionally filtered by memory_type."""
    if not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must not be empty",
        )
    memories = memory_service.get_user_memories(user_id=user_id, memory_type=memory_type)
    return MemoryListResponse(user_id=user_id, memories=memories, count=len(memories))


@router.post("", response_model=MemoryRecord, status_code=status.HTTP_201_CREATED)
def create_memory(payload: CreateMemoryRequest) -> MemoryRecord:
    """Explicitly create or update a user memory record with safety and quota validation."""
    if not payload.user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must not be empty",
        )
    try:
        record = memory_service.create_explicit_memory(
            user_id=payload.user_id,
            memory_type=payload.memory_type,
            key=payload.key,
            value=payload.value,
            confidence=payload.confidence,
            ttl_seconds=payload.ttl_seconds,
        )
        return record
    except MemoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory persistence failed: {exc}",
        )


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
def delete_memory(
    memory_id: str,
    user_id: str = Query(..., description="TradeWise user identity for ownership validation"),
) -> MemoryDeleteResponse:
    """Delete an individual memory record by ID for a user."""
    # Verify the memory exists and belongs to the user
    existing = memory_service.store.get(user_id=user_id, memory_id=memory_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory record '{memory_id}' not found for user '{user_id}'",
        )
    deleted = memory_service.delete_memory(user_id=user_id, memory_id=memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to delete memory record '{memory_id}'",
        )
    return MemoryDeleteResponse(status="deleted", memory_id=memory_id)


@router.delete("", response_model=MemoryClearResponse)
def clear_user_memories(
    user_id: str = Query(..., description="TradeWise user identity to forget completely"),
) -> MemoryClearResponse:
    """Clear all persistent memories for a user (Right to be Forgotten)."""
    if not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must not be empty",
        )
    count = memory_service.clear_user(user_id)
    return MemoryClearResponse(status="cleared", user_id=user_id, deleted_count=count)
