"""
Unit tests for the QueryDecomposer (app.router.decomposer).
Verifies rule-guided decomposition across multi-intent, cross-domain,
and comparative queries.
"""

import pytest
from app.router.decomposer import QueryDecomposer, query_decomposer


@pytest.fixture
def decomposer():
    return QueryDecomposer()


def test_single_intent_passthrough(decomposer: QueryDecomposer):
    plan = decomposer.decompose("What is an IPO?")
    assert plan.is_compound is False
    assert len(plan.sub_tasks) == 1
    assert plan.sub_tasks[0].domain == "EQUITY"
    assert plan.sub_tasks[0].intent == "educational_concept"


def test_single_quote_passthrough(decomposer: QueryDecomposer):
    plan = decomposer.decompose("Current price of Reliance on NSE")
    assert plan.is_compound is False
    assert len(plan.sub_tasks) == 1
    assert plan.sub_tasks[0].domain == "EQUITY"
    assert plan.sub_tasks[0].intent == "quote"
    assert plan.sub_tasks[0].target_entity == "RELIANCE"


def test_concept_plus_quote_decomposition(decomposer: QueryDecomposer):
    query = "What is an IPO and what is Reliance trading at?"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2

    # Verify task domains and intents
    task_intents = [t.intent for t in plan.sub_tasks]
    assert "educational_concept" in task_intents
    assert "quote" in task_intents

    quote_task = next(t for t in plan.sub_tasks if t.intent == "quote")
    assert quote_task.domain == "EQUITY"
    assert quote_task.target_entity == "RELIANCE"


def test_equity_plus_personal_finance_decomposition(decomposer: QueryDecomposer):
    query = "What is P/E and how should I plan my monthly budget?"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2

    domains = [t.domain for t in plan.sub_tasks]
    assert "EQUITY" in domains
    assert "PERSONAL_FINANCE" in domains


def test_equity_plus_crypto_decomposition(decomposer: QueryDecomposer):
    query = "What is an ETF and tell me Bitcoin price"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2

    domains = [t.domain for t in plan.sub_tasks]
    assert "EQUITY" in domains
    assert "CRYPTO" in domains

    crypto_task = next(t for t in plan.sub_tasks if t.domain == "CRYPTO")
    assert crypto_task.intent == "quote"
    assert crypto_task.target_entity == "BTC"


def test_multi_company_comparative_decomposition(decomposer: QueryDecomposer):
    query = "Compare Reliance and TCS price"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2

    entities = [t.target_entity for t in plan.sub_tasks]
    assert "RELIANCE" in entities
    assert "TCS" in entities
    assert all(t.domain == "EQUITY" for t in plan.sub_tasks)
    assert all(t.intent == "quote" for t in plan.sub_tasks)


def test_empty_query_decomposition(decomposer: QueryDecomposer):
    plan = decomposer.decompose("   ")
    assert plan.is_compound is False
    assert plan.sub_tasks == []


def test_reliance_quote_and_bitcoin_concept_decomposition(decomposer: QueryDecomposer):
    query = "What is Reliance trading at and what is Bitcoin?"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2

    # Verify both intents are captured
    reliance_task = next(t for t in plan.sub_tasks if t.target_entity == "RELIANCE")
    assert reliance_task.domain == "EQUITY"
    assert reliance_task.intent == "quote"

    btc_task = next(t for t in plan.sub_tasks if t.domain == "CRYPTO")
    assert btc_task.intent == "educational_concept"
    assert "bitcoin" in btc_task.query_slice.lower()


def test_three_domain_decomposition(decomposer: QueryDecomposer):
    query = "What is an IPO, what is Bitcoin, and how does 50/30/20 budgeting work?"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 3

    domains = [t.domain for t in plan.sub_tasks]
    assert "EQUITY" in domains
    assert "CRYPTO" in domains
    assert "PERSONAL_FINANCE" in domains

    intents = [t.intent for t in plan.sub_tasks]
    assert all(i == "educational_concept" for i in intents)


def test_equity_plus_personal_finance_calculation_decomposition(decomposer: QueryDecomposer):
    query = "What is Infosys share price and calculate 50/30/20 for 60000"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2

    equity_task = next(t for t in plan.sub_tasks if t.domain == "EQUITY")
    assert equity_task.intent == "quote"
    assert equity_task.target_entity == "INFY"

    pf_task = next(t for t in plan.sub_tasks if t.domain == "PERSONAL_FINANCE")
    assert pf_task.intent == "calculation"


def test_crypto_plus_personal_finance_decomposition(decomposer: QueryDecomposer):
    query = "What is Bitcoin price and what is an emergency fund?"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2

    crypto_task = next(t for t in plan.sub_tasks if t.domain == "CRYPTO")
    assert crypto_task.intent == "quote"
    assert crypto_task.target_entity == "BTC"

    pf_task = next(t for t in plan.sub_tasks if t.domain == "PERSONAL_FINANCE")
    assert pf_task.intent == "educational_concept"


def test_three_domain_quotes_and_calc_decomposition(decomposer: QueryDecomposer):
    query = "Reliance price, Bitcoin price, and calculate 50/30/20 for 50000"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 3

    domains = {t.domain for t in plan.sub_tasks}
    assert domains == {"EQUITY", "CRYPTO", "PERSONAL_FINANCE"}


def test_multi_entity_crypto_comparison_decomposition(decomposer: QueryDecomposer):
    query = "Compare Bitcoin and Ethereum price"
    plan = decomposer.decompose(query)
    assert plan.is_compound is True
    assert len(plan.sub_tasks) == 2
    assert all(t.domain == "CRYPTO" for t in plan.sub_tasks)
    assert all(t.intent == "quote" for t in plan.sub_tasks)
    entities = {t.target_entity for t in plan.sub_tasks}
    assert entities == {"BTC", "ETH"}

