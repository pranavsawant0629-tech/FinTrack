"""
Unit and integration tests for the Central Orchestrator (app.router.orchestrator).
Verifies safety pre-filtering, fast-path dispatching, Equity Agent delegation,
and staged domain routing in Stage 4A.
"""

from unittest.mock import MagicMock
import pytest

from app.router.orchestrator import CentralOrchestrator, central_orchestrator
from app.router.models import OrchestratorResponse
from app.router.safety import GLOBAL_REFUSAL_MESSAGE


# =====================================================================
# 1. Safety Pre-Filtering Interception
# =====================================================================
def test_orchestrator_blocks_unsafe_equity_query():
    resp = central_orchestrator.ask("Which stock should I buy today?")
    assert isinstance(resp, OrchestratorResponse)
    assert resp.grounding_status == "ungrounded"
    assert resp.answer == GLOBAL_REFUSAL_MESSAGE
    assert resp.domain_detected == "EQUITY"
    assert len(resp.sub_tasks) == 1
    assert resp.sub_tasks[0].status == "filtered"
    assert resp.sub_tasks[0].intent == "advice_refusal"


def test_orchestrator_blocks_unsafe_crypto_query():
    resp = central_orchestrator.ask("Which coin will 10x this month?")
    assert resp.grounding_status == "ungrounded"
    assert resp.answer == GLOBAL_REFUSAL_MESSAGE
    assert resp.domain_detected == "CRYPTO"
    assert resp.sub_tasks[0].status == "filtered"


def test_orchestrator_blocks_unsafe_pf_query():
    resp = central_orchestrator.ask("Where should I invest my ₹50,000?")
    assert resp.grounding_status == "ungrounded"
    assert resp.answer == GLOBAL_REFUSAL_MESSAGE
    assert resp.domain_detected == "PERSONAL_FINANCE"
    assert resp.sub_tasks[0].status == "filtered"


# =====================================================================
# 2. Equity Domain Delegation
# =====================================================================
def test_orchestrator_delegates_market_status():
    resp = central_orchestrator.ask("Is the stock market open today?")
    assert resp.domain_detected == "EQUITY"
    assert resp.grounding_status == "fully_grounded"
    assert resp.grounding_sources == ["live_market_data"]
    assert "stock market (NSE) is currently" in resp.answer
    assert resp.sub_tasks[0].status == "success"


def test_orchestrator_delegates_market_quote():
    resp = central_orchestrator.ask("Current price of Reliance")
    assert resp.domain_detected == "EQUITY"
    assert resp.grounding_status == "fully_grounded"
    assert resp.grounding_sources == ["live_market_data"]
    assert resp.market_data is not None
    assert resp.market_data.symbol == "RELIANCE"
    assert "₹" in resp.answer
    assert resp.sub_tasks[0].status == "success"


# =====================================================================
# 3. Crypto Domain Live Dispatch
# =====================================================================
def test_orchestrator_crypto_dispatch():
    resp = central_orchestrator.ask("What is blockchain?")
    assert resp.domain_detected == "CRYPTO"
    assert resp.sub_tasks[0].status == "success"
    assert len(resp.answer) > 20
    assert resp.sub_tasks[0].domain == "CRYPTO"


# =====================================================================
# 4. Personal Finance Domain Live Dispatch
# =====================================================================
def test_orchestrator_personal_finance_dispatch():
    resp = central_orchestrator.ask("What is the 50/30/20 budgeting rule?")
    assert resp.domain_detected == "PERSONAL_FINANCE"
    assert resp.sub_tasks[0].status == "success"
    assert "50" in resp.answer
    assert "30" in resp.answer
    assert "20" in resp.answer
