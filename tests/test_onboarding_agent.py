"""
Tests for the Onboarding & System Help Agent.
Verifies system capability enumeration, API-only memory deletion instructions,
safety disclaimers, and FAQ retrieval.
"""

import pytest

from app.agents.onboarding.agent import OnboardingAgent, OnboardingAgentResult
from app.agents.onboarding.prompts import ONBOARDING_DISCLAIMER


@pytest.fixture
def agent():
    return OnboardingAgent()


class TestOnboardingAgent:
    """Test Onboarding workflows and responses."""

    def test_general_orientation_lists_all_eight_domains(self, agent):
        res = agent.ask("What can Finova AI do?")
        assert isinstance(res, OnboardingAgentResult)
        assert res.topic == "general_orientation"
        assert res.grounding_status == "fully_grounded"
        assert res.capabilities is not None
        assert len(res.capabilities) == 8

        # Check domains present
        domains = [c["domain"] for c in res.capabilities]
        expected_domains = [
            "equity",
            "crypto",
            "personal_finance",
            "derivatives",
            "portfolio",
            "news",
            "quiz",
            "onboarding",
        ]
        assert set(domains) == set(expected_domains)
        assert res.disclaimer == ONBOARDING_DISCLAIMER

    def test_memory_deletion_inquiry_explains_api_only_policy(self, agent):
        queries = [
            "How do I delete my memory?",
            "Can you forget me and clear memory?",
            "How do I remove my data?",
        ]
        for q in queries:
            res = agent.ask(q)
            assert res.topic == "privacy_memory_deletion"
            assert "DELETE /memory" in res.answer
            assert "cannot be deleted via natural language chat" in res.answer
            assert "GET /memory" in res.answer

    def test_specific_capability_lookup(self, agent):
        res = agent.ask("Tell me about your derivatives tools")
        assert res.topic == "capability_derivatives"
        assert "Derivatives & F&O Tutor" in res.answer
        assert "Nifty" in res.answer or "Greeks" in res.answer

    def test_sebi_advisor_faq(self, agent):
        res = agent.ask("Are you a SEBI registered advisor?")
        assert res.topic == "faqs"
        assert "strictly an educational and analytical platform" in res.answer
