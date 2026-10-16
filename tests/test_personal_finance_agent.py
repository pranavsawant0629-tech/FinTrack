"""
Unit tests for Personal Finance Tutor Agent (app.agents.personal_finance.agent).
Verifies safety guardrail enforcement, deterministic calculation execution,
and pedagogical guidance.
"""

from unittest.mock import MagicMock
import pytest

from app.agents.personal_finance.agent import PersonalFinanceAgent, personal_finance_agent
from app.router.safety import GLOBAL_REFUSAL_MESSAGE


def test_pf_agent_blocks_advisory_inquiry():
    res = personal_finance_agent.ask("Where should I invest my ₹50,000?")
    assert res.grounding_status == "ungrounded"
    assert res.answer == GLOBAL_REFUSAL_MESSAGE
    assert res.calc_data is None


def test_pf_agent_deterministic_50_30_20_calculation():
    res = personal_finance_agent.ask("How does 50/30/20 split for ₹60,000 monthly income?")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["calc_tool"]
    assert res.calc_data is not None
    assert res.calc_data["income"] == 60000.0
    assert res.calc_data["needs"] == 30000.0
    assert res.calc_data["wants"] == 18000.0
    assert res.calc_data["savings"] == 12000.0
    assert "₹30,000.00" in res.answer


def test_pf_agent_emergency_fund_calculation():
    res = personal_finance_agent.ask("Calculate emergency fund target for 25000 monthly expenses")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["calc_tool"]
    assert res.calc_data is not None
    assert res.calc_data["target_fund"] == 150000.0
    assert "₹150,000.00" in res.answer


def test_pf_agent_educational_concept():
    mock_llm = MagicMock()
    mock_llm.model = "qwen2.5:7b-instruct"
    mock_llm.chat.return_value = (
        "The 50/30/20 rule is a budgeting guideline dividing after-tax income into needs, wants, and savings."
    )

    agent = PersonalFinanceAgent(llm=mock_llm)
    res = agent.ask("What is the 50/30/20 budgeting rule?")
    assert res.grounding_status == "ungrounded"
    assert "needs, wants, and savings" in res.answer
    assert mock_llm.chat.call_count == 1


def test_pf_agent_compound_interest_calculation():
    res = personal_finance_agent.ask("Calculate compound interest on ₹10,000 at 8% for 5 years")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["calc_tool"]
    assert res.calc_data is not None
    assert res.calc_data["principal"] == 10000.0
    assert res.calc_data["annual_rate_percent"] == 8.0
    assert res.calc_data["tenure_years"] == 5.0
    assert res.calc_data["maturity_amount"] == 14693.28
    assert res.calc_data["interest_earned"] == 4693.28
    assert "₹14,693.28" in res.answer


def test_pf_agent_sip_calculation():
    res = personal_finance_agent.ask("Calculate SIP returns for monthly ₹5,000 at 12% for 10 years")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["calc_tool"]
    assert res.calc_data is not None
    assert res.calc_data["monthly_investment"] == 5000.0
    assert res.calc_data["annual_return_percent"] == 12.0
    assert res.calc_data["tenure_years"] == 10.0
    assert res.calc_data["total_invested"] == 600000.0
    assert res.calc_data["future_value"] == 1161695.38
    assert res.calc_data["wealth_gain"] == 561695.38
    assert "₹1,161,695.38" in res.answer


def test_pf_agent_missing_inputs_compound_interest():
    res = personal_finance_agent.ask("Calculate compound interest on ₹10,000")
    assert res.grounding_status == "ungrounded"
    assert res.calc_data is None
    assert "Compound Interest Calculation Required Parameters" in res.answer
    assert "Annual Interest Rate" in res.answer
    assert "Investment Tenure" in res.answer


def test_pf_agent_missing_inputs_sip():
    res = personal_finance_agent.ask("Calculate SIP returns for 5000")
    assert res.grounding_status == "ungrounded"
    assert res.calc_data is None
    assert "Systematic Investment Plan (SIP) Required Parameters" in res.answer
    assert "Expected Annual Return Rate" in res.answer
    assert "Investment Tenure" in res.answer


def test_pf_agent_missing_inputs_50_30_20():
    res = personal_finance_agent.ask("Calculate 50/30/20 budget breakdown")
    assert res.grounding_status == "ungrounded"
    assert res.calc_data is None
    assert "specify your monthly net income" in res.answer


def test_pf_agent_invalid_inputs_compound_interest():
    res = personal_finance_agent.ask("Calculate compound interest on ₹-10,000 at 8% for 5 years")
    assert res.grounding_status == "ungrounded"
    assert res.calc_data is None
    assert "Invalid input" in res.answer


def test_pf_agent_invalid_inputs_sip():
    res = personal_finance_agent.ask("Calculate SIP returns for monthly ₹0 at 12% for 5 years")
    assert res.grounding_status == "ungrounded"
    assert res.calc_data is None
    assert "Invalid input" in res.answer

