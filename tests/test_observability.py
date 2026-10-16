"""Stage 7H: Observability and Auditability Tests.

Validates:
1. Structured RequestTrace generation with complete audit fields.
2. Deterministic PII sanitization in telemetry previews (PAN, Aadhaar, phone, card).
3. Anonymous query identification (user_id=None sets is_anonymous=True).
4. Telemetry trace circular buffer retention and retrieval.
"""

from __future__ import annotations

import pytest

from app.core.telemetry import (
    RequestTrace,
    TelemetryCollector,
    sanitize_pii,
    telemetry_collector,
)


class TestObservability:
    """Stage 7H: Structured telemetry and PII sanitization test suite."""

    @pytest.fixture
    def collector(self) -> TelemetryCollector:
        c = TelemetryCollector(max_history=10)
        c.clear()
        return c

    # =========================================================================
    # 1. PII Redaction in Telemetry
    # =========================================================================
    @pytest.mark.parametrize(
        "raw_text,expected_redaction",
        [
            ("My PAN is ABCDE1234F for demat", "[PAN_REDACTED]"),
            ("Aadhaar 1234 5678 9012 verification", "[AADHAAR_REDACTED]"),
            ("Contact me at +919876543210 please", "[PHONE_REDACTED]"),
            ("Card ending 4532 0150 1234 5678", "[CARD_REDACTED]"),
        ],
    )
    def test_sanitize_pii_masks_identifiers(self, raw_text: str, expected_redaction: str):
        """Telemetry must never contain unmasked PII."""
        sanitized = sanitize_pii(raw_text)
        assert expected_redaction in sanitized
        # Original sensitive substring must not be present
        if expected_redaction == "[PAN_REDACTED]":
            assert "ABCDE1234F" not in sanitized
        elif expected_redaction == "[AADHAAR_REDACTED]":
            assert "1234 5678 9012" not in sanitized
        elif expected_redaction == "[PHONE_REDACTED]":
            assert "+919876543210" not in sanitized

    # =========================================================================
    # 2. Trace Creation & Complete Audit Fields
    # =========================================================================
    def test_record_trace_complete_fields(self, collector: TelemetryCollector):
        """Verify trace record has all structured fields populated accurately."""
        trace = collector.record_trace(
            query="What is an IPO and what is Reliance trading at?",
            user_id="user_test_42",
            safety_is_safe=True,
            domain="EQUITY",
            intent="compound",
            is_compound=True,
            subtask_count=2,
            grounding_status="fully_grounded",
            citation_count=2,
            latency_ms=12.45,
        )

        assert isinstance(trace, RequestTrace)
        assert trace.trace_id != ""
        assert trace.user_id == "user_test_42"
        assert trace.is_anonymous is False
        assert trace.safety_is_safe is True
        assert trace.domain == "EQUITY"
        assert trace.intent == "compound"
        assert trace.is_compound is True
        assert trace.subtask_count == 2
        assert trace.grounding_status == "fully_grounded"
        assert trace.citation_count == 2
        assert trace.latency_ms == 12.45

        # Check in history
        recent = collector.get_recent_traces(limit=10)
        assert len(recent) == 1
        assert recent[0].trace_id == trace.trace_id

    # =========================================================================
    # 3. Anonymous Query Handling
    # =========================================================================
    @pytest.mark.parametrize("empty_user", [None, "", "   "])
    def test_anonymous_query_audit(self, collector: TelemetryCollector, empty_user: str | None):
        """Anonymous queries must be flagged as anonymous with user_id=None."""
        trace = collector.record_trace(
            query="What is inflation?",
            user_id=empty_user,
            safety_is_safe=True,
            domain="GENERAL",
            intent="educational_concept",
            latency_ms=3.5,
        )
        assert trace.is_anonymous is True
        assert trace.user_id is None

    # =========================================================================
    # 4. History Buffer Clamping
    # =========================================================================
    def test_history_buffer_clamping(self, collector: TelemetryCollector):
        """History buffer must maintain max_history size without memory leak."""
        for i in range(15):
            collector.record_trace(
                query=f"Query {i}",
                user_id=f"user_{i}",
                latency_ms=float(i),
            )
        # Max history was configured as 10
        assert len(collector._history) == 10
        recent = collector.get_recent_traces(limit=20)
        assert len(recent) == 10
        # Most recent query should be Query 14
        assert "Query 14" in recent[0].query_preview
