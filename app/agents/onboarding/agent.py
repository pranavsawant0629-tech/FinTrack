"""
Onboarding & System Help Agent for Finova AI.
Provides platform overview, capability discovery, privacy and memory management FAQs.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from app.agents.onboarding.prompts import ONBOARDING_DISCLAIMER, ONBOARDING_SYSTEM_PROMPT
from app.tools.onboarding.models import CapabilityItem, FAQItem
from app.tools.onboarding.repository import OnboardingRepository, onboarding_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OnboardingAgentResult:
    """Standardized result from the Onboarding Agent."""
    query: str
    answer: str
    topic: str
    grounding_status: str
    grounding_sources: list[str]
    disclaimer: str
    capabilities: list[dict[str, Any]] | None = None
    faqs: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "topic": self.topic,
            "grounding_status": self.grounding_status,
            "grounding_sources": self.grounding_sources,
            "disclaimer": self.disclaimer,
            "capabilities": self.capabilities,
            "faqs": self.faqs,
        }


class OnboardingAgent:
    """Agent specialized in user onboarding, feature discovery, and privacy FAQs."""

    def __init__(
        self,
        repository: OnboardingRepository | None = None,
        llm: Any = None,
    ) -> None:
        self._repo = repository or onboarding_repository
        self._llm = llm

    def ask(self, query: str, user_id: str | None = None) -> OnboardingAgentResult:
        low = query.lower()

        # 1. Memory deletion / privacy FAQ check
        if any(term in low for term in ["delete my memory", "clear memory", "forget me", "remove my data", "delete preference"]):
            return self._handle_memory_deletion_query(query)

        # 2. Specific domain / capability question
        for cap in self._repo.get_all_capabilities():
            if cap.domain in low or cap.name.lower() in low:
                return self._handle_specific_capability(query, cap)

        # 3. Privacy / Safety / General FAQ check
        if any(term in low for term in ["privacy", "sebi registered", "advisor", "brokerage", "trade execution", "faq"]):
            return self._handle_faq_query(query)

        # 4. Default: Full system overview & capabilities
        return self._handle_general_orientation(query)

    def _handle_memory_deletion_query(self, query: str) -> OnboardingAgentResult:
        faq = next((f for f in self._repo.get_faqs("privacy") if f.id == "faq_memory_deletion"), None)
        answer = (
            "### 🔒 Managing & Deleting Your Memory\n\n"
            "Finova AI strictly controls persistent memory to protect your privacy and prevent accidental data loss.\n\n"
            "**API-Only Deletion Policy:**\n"
            "Memory records cannot be deleted via natural language chat messages. To inspect or permanently erase stored memories, "
            "use our authenticated REST API:\n\n"
            "- **Inspect Memories:** `GET /memory?user_id=...`\n"
            "- **Delete Specific Record:** `DELETE /memory/{memory_id}?user_id=...`\n"
            "- **Clear All Memories (Right to be Forgotten):** `DELETE /memory?user_id=...`\n\n"
            "If you interact without providing a `user_id`, your session is entirely ephemeral and no long-term memory is persisted.\n\n"
            f"*{ONBOARDING_DISCLAIMER}*"
        )
        return OnboardingAgentResult(
            query=query,
            answer=answer,
            topic="privacy_memory_deletion",
            grounding_status="fully_grounded",
            grounding_sources=["system_architecture", "api_specification"],
            disclaimer=ONBOARDING_DISCLAIMER,
            faqs=[faq.to_dict()] if faq else None,
        )

    def _handle_specific_capability(self, query: str, cap: CapabilityItem) -> OnboardingAgentResult:
        lines: list[str] = [
            f"### 🚀 Finova AI Capability: {cap.name}",
            f"**Domain:** `{cap.domain.upper()}`\n",
            f"{cap.description}\n",
            "**Example Prompts to Try:**",
        ]
        for ex in cap.example_prompts:
            lines.append(f"- *\"{ex}\"*")

        lines.append(f"\n*{ONBOARDING_DISCLAIMER}*")
        return OnboardingAgentResult(
            query=query,
            answer="\n".join(lines),
            topic=f"capability_{cap.domain}",
            grounding_status="fully_grounded",
            grounding_sources=["system_catalog"],
            disclaimer=ONBOARDING_DISCLAIMER,
            capabilities=[cap.to_dict()],
        )

    def _handle_faq_query(self, query: str) -> OnboardingAgentResult:
        faqs = self._repo.search_faqs(query)
        lines: list[str] = [
            "### ❓ Finova AI Frequently Asked Questions\n",
        ]
        for f in faqs:
            lines.append(f"**Q: {f.question}**")
            lines.append(f"{f.answer}\n")

        lines.append(f"*{ONBOARDING_DISCLAIMER}*")
        return OnboardingAgentResult(
            query=query,
            answer="\n".join(lines),
            topic="faqs",
            grounding_status="fully_grounded",
            grounding_sources=["faq_catalog"],
            disclaimer=ONBOARDING_DISCLAIMER,
            faqs=[f.to_dict() for f in faqs],
        )

    def _handle_general_orientation(self, query: str) -> OnboardingAgentResult:
        caps = self._repo.get_all_capabilities()
        lines: list[str] = [
            "### 🌟 Welcome to Finova AI",
            "Finova AI is an India-first, local-first educational intelligence engine designed to make financial literacy "
            "authoritative, accessible, and grounded in official market facts.\n",
            "**Our 8 Specialized Educational Domains:**\n",
        ]

        for idx, c in enumerate(caps, start=1):
            lines.append(f"**{idx}. {c.name}** (`{c.domain}`)")
            lines.append(f"   {c.description}")
            lines.append(f"   *Example:* \"{c.example_prompts[0]}\"\n")

        lines.append(
            "🔒 **Privacy & Safety:** Finova AI does NOT execute trades, does not give personalized financial advice, "
            "and does not store sensitive government IDs. Memory management is strictly handled via authenticated REST APIs.\n"
        )
        lines.append(f"*{ONBOARDING_DISCLAIMER}*")

        return OnboardingAgentResult(
            query=query,
            answer="\n".join(lines),
            topic="general_orientation",
            grounding_status="fully_grounded",
            grounding_sources=["system_catalog"],
            disclaimer=ONBOARDING_DISCLAIMER,
            capabilities=[c.to_dict() for c in caps],
        )
