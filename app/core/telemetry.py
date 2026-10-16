"""
Zero-Dependency Structured Telemetry & Auditability Engine for Finova AI.

Provides structured request tracing, latency tracking, grounding metrics,
and automatic PII scrubbing for production auditing without external logging services.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger("finova.telemetry")

# Deterministic PII Redaction Expressions
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
PHONE_PATTERN = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE)


def sanitize_pii(text: str) -> str:
    """Deterministically redact all sensitive financial and personal identifiers."""
    if not text:
        return ""
    # Redact in order of specificity: Cards (13-19) -> Phone (+91/10-digit) -> Aadhaar (12-digit) -> PAN
    sanitized = CARD_PATTERN.sub("[CARD_REDACTED]", text)
    sanitized = PHONE_PATTERN.sub("[PHONE_REDACTED]", sanitized)
    sanitized = AADHAAR_PATTERN.sub("[AADHAAR_REDACTED]", sanitized)
    sanitized = PAN_PATTERN.sub("[PAN_REDACTED]", sanitized)
    return sanitized


class RequestTrace(BaseModel):
    """Immutable structured audit record for a single Finova query invocation."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_iso: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    user_id: str | None = None
    is_anonymous: bool = True
    query_preview: str = Field(description="Sanitized preview of user query")
    safety_is_safe: bool = True
    safety_refusal_reason: str | None = None
    domain: str | None = None
    intent: str | None = None
    is_compound: bool = False
    subtask_count: int = 1
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"] | None = None
    citation_count: int = 0
    latency_ms: float = 0.0

    def to_audit_dict(self) -> dict[str, Any]:
        """Convert trace to a JSON-serializable dictionary."""
        return self.model_dump()


class TelemetryCollector:
    """In-memory telemetry collector and structured audit log dispatcher."""

    def __init__(self, max_history: int = 500) -> None:
        self.max_history = max_history
        self._history: list[RequestTrace] = []

    def record_trace(
        self,
        query: str,
        user_id: str | None = None,
        safety_is_safe: bool = True,
        safety_refusal_reason: str | None = None,
        domain: str | None = None,
        intent: str | None = None,
        is_compound: bool = False,
        subtask_count: int = 1,
        grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"] | None = None,
        citation_count: int = 0,
        latency_ms: float = 0.0,
    ) -> RequestTrace:
        """Create, sanitize, persist, and log an audit trace."""
        cleaned_preview = sanitize_pii(query[:120])
        is_anon = not bool(user_id and user_id.strip())

        trace = RequestTrace(
            user_id=user_id if not is_anon else None,
            is_anonymous=is_anon,
            query_preview=cleaned_preview,
            safety_is_safe=safety_is_safe,
            safety_refusal_reason=safety_refusal_reason,
            domain=domain,
            intent=intent,
            is_compound=is_compound,
            subtask_count=subtask_count,
            grounding_status=grounding_status,
            citation_count=citation_count,
            latency_ms=round(latency_ms, 2),
        )

        self._history.append(trace)
        if len(self._history) > self.max_history:
            self._history.pop(0)

        logger.info("AUDIT_TRACE: %s", json.dumps(trace.to_audit_dict()))
        return trace

    def get_recent_traces(self, limit: int = 50) -> list[RequestTrace]:
        """Retrieve recent traces up to limit."""
        return list(reversed(self._history[-limit:]))

    def clear(self) -> None:
        """Clear historical traces."""
        self._history.clear()


telemetry_collector = TelemetryCollector()
