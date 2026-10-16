"""
Repository of system capabilities, orientation guides, and privacy FAQs for Finova AI.
"""

from __future__ import annotations

from typing import Any

from app.tools.onboarding.models import CapabilityItem, FAQItem

CAPABILITIES: list[CapabilityItem] = [
    CapabilityItem(
        domain="equity",
        name="Equity Research & Valuation",
        description="Explains equity concepts, valuation models (DCF, Graham Number), and live market metrics.",
        example_prompts=[
            "What is the current price and P/E ratio of TCS?",
            "Calculate Graham Number for Infosys",
            "Explain how Discounted Cash Flow (DCF) works",
        ],
    ),
    CapabilityItem(
        domain="crypto",
        name="Crypto & VDA Literacy",
        description="Provides objective education on Virtual Digital Assets (VDAs), high volatility risks, and India's flat 30% tax rules.",
        example_prompts=[
            "What is Bitcoin and how does blockchain work?",
            "How is cryptocurrency taxed in India under Section 115BBH?",
            "What are the risks of trading crypto compared to equity?",
        ],
    ),
    CapabilityItem(
        domain="personal_finance",
        name="Personal Finance & Wealth Planning",
        description="Guides budgeting (50/30/20), emergency funds, tax-saving instruments (80C), and deterministic SIP/PPF calculations.",
        example_prompts=[
            "How should I budget my ₹50,000 monthly salary?",
            "Calculate SIP maturity for ₹5,000/month for 10 years at 12%",
            "Compare PPF vs ELSS for Section 80C tax saving",
        ],
    ),
    CapabilityItem(
        domain="derivatives",
        name="Derivatives & F&O Tutor",
        description="Simulates exact payoff diagrams, breakevens, and option Greeks, highlighting SEBI's 9-in-10 retail risk warning.",
        example_prompts=[
            "Show payoff table for Nifty 24500 Call at ₹120 premium",
            "Explain Delta, Theta, and Gamma in options trading",
            "What does SEBI say about retail trader profitability in F&O?",
        ],
    ),
    CapabilityItem(
        domain="portfolio",
        name="Portfolio Analytics & Stress Testing",
        description="Analyzes simulated portfolio diversification, asset and sector weights, and models 'what-if' market decline shocks.",
        example_prompts=[
            "What is my current portfolio value and asset allocation?",
            "How diversified is my portfolio?",
            "What if TCS falls 15%?",
        ],
    ),
    CapabilityItem(
        domain="news",
        name="Market News & Regulatory Intelligence",
        description="Summarizes verified live financial news and official SEBI/RBI circulars with strict freshness and source attribution.",
        example_prompts=[
            "What is the latest news for Reliance?",
            "Show recent SEBI circulars on derivatives",
            "What did RBI announce in the latest MPC meeting?",
        ],
    ),
    CapabilityItem(
        domain="quiz",
        name="Knowledge Challenges & Quizzes",
        description="Conducts interactive multiple-choice financial quizzes with 100% deterministic grading and SEBI/NISM explanations.",
        example_prompts=[
            "Quiz me on equity valuation",
            "Test my knowledge on derivatives and options",
            "Give me a beginner quiz on personal finance",
        ],
    ),
    CapabilityItem(
        domain="onboarding",
        name="System Orientation & Privacy Help",
        description="Explains Finova AI capabilities, privacy and data retention policies, and API-only memory management.",
        example_prompts=[
            "What can Finova AI do?",
            "How do I delete my saved memory or preferences?",
            "Is Finova AI a SEBI-registered advisor?",
        ],
    ),
]

FAQS: list[FAQItem] = [
    FAQItem(
        id="faq_advisory",
        category="safety",
        question="Is Finova AI a SEBI-registered financial adviser?",
        answer="No. Finova AI is strictly an educational and analytical platform designed for financial literacy. Finova AI does NOT provide personalized investment advice, stock recommendations, or trading directives. Consult a SEBI-registered Investment Adviser (RIA) for personalized financial planning.",
    ),
    FAQItem(
        id="faq_trade_execution",
        category="safety",
        question="Can Finova AI place orders or execute trades in my brokerage account?",
        answer="No. Finova AI does not execute trades, place orders, hold client funds, or connect to brokerage execution APIs. All portfolio and derivative simulations are strictly educational and analytical.",
    ),
    FAQItem(
        id="faq_memory_privacy",
        category="privacy",
        question="How does Finova AI store my preferences and learning progress?",
        answer="When you provide a user ID, Finova AI stores explicit preferences (such as learning level and educational goals) in an isolated local database partition. We never store government identifiers (such as PAN or Aadhaar) or sensitive financial credentials. If no user ID is provided, sessions are completely ephemeral.",
    ),
    FAQItem(
        id="faq_memory_deletion",
        category="privacy",
        question="How do I delete or manage my stored memory?",
        answer="To inspect, export, or delete your persistent memories, use Finova AI's authenticated REST API endpoints: GET /memory?user_id=... (to inspect), DELETE /memory/{memory_id}?user_id=... (to delete a single record), or DELETE /memory?user_id=... (to completely clear all records for your user ID). Finova AI does not execute permanent memory deletion via conversational chat commands to prevent accidental data loss.",
    ),
]


class OnboardingRepository:
    """Repository providing access to system capabilities and FAQs."""

    def get_all_capabilities(self) -> list[CapabilityItem]:
        return CAPABILITIES

    def get_capability_by_domain(self, domain: str) -> CapabilityItem | None:
        clean = domain.strip().lower()
        for cap in CAPABILITIES:
            if cap.domain == clean:
                return cap
        return None

    def get_faqs(self, category: str | None = None) -> list[FAQItem]:
        if not category:
            return FAQS
        clean = category.strip().lower()
        return [f for f in FAQS if f.category.lower() == clean]

    def search_faqs(self, query: str) -> list[FAQItem]:
        low = query.lower()
        matched: list[FAQItem] = []
        for faq in FAQS:
            if any(term in low for term in faq.question.lower().split()):
                matched.append(faq)
            elif any(term in low for term in faq.answer.lower().split()):
                matched.append(faq)
        return matched or FAQS[:2]


onboarding_repository = OnboardingRepository()
