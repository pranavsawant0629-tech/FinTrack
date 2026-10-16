"""
Unit tests for deterministic Personal Finance calculation tools (app.tools.calc).
Verifies mathematical precision and error handling for 50/30/20, compounding, SIP, and emergency fund.
"""

import pytest
from app.tools.calc.budget import calculate_50_30_20
from app.tools.calc.compounding import calculate_compound_interest, calculate_sip
from app.tools.calc.emergency_fund import calculate_emergency_fund


def test_calculate_50_30_20_precision():
    res = calculate_50_30_20(50000.0)
    assert res["income"] == 50000.0
    assert res["needs"] == 25000.0
    assert res["wants"] == 15000.0
    assert res["savings"] == 10000.0
    assert res["needs_pct"] == 50.0
    assert res["wants_pct"] == 30.0
    assert res["savings_pct"] == 20.0


def test_calculate_50_30_20_invalid_income():
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_50_30_20(0.0)
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_50_30_20(-500.0)


def test_calculate_compound_interest_precision():
    # 100,000 at 10% annual for 2 years compounded annually
    # A = 100000 * (1.1)^2 = 121,000
    res = calculate_compound_interest(principal=100000.0, annual_rate_pct=10.0, tenure_years=2.0)
    assert res["maturity_amount"] == 121000.0
    assert res["interest_earned"] == 21000.0


def test_calculate_sip_precision():
    # 5,000 monthly for 1 year at 12% expected annual return
    # Monthly rate i = 0.01, k = 12 months
    # Formula: 5000 * ((1.01^12 - 1) / 0.01) * 1.01 = ~64,047.16
    res = calculate_sip(monthly_investment=5000.0, annual_return_pct=12.0, tenure_years=1.0)
    assert res["total_invested"] == 60000.0
    assert res["future_value"] > 60000.0
    assert res["wealth_gain"] > 0.0
    assert round(res["future_value"], 0) == 64047.0


def test_calculate_emergency_fund_precision():
    # Monthly expenses: 30,000, 6 months target = 180,000
    res = calculate_emergency_fund(monthly_expenses=30000.0, current_savings=60000.0, target_months=6.0)
    assert res["target_fund"] == 180000.0
    assert res["funding_gap"] == 120000.0
    assert res["months_covered"] == 2.0


def test_calculate_emergency_fund_fully_funded():
    # Monthly expenses: 20,000, current savings: 150,000, target 6 months (120,000)
    res = calculate_emergency_fund(monthly_expenses=20000.0, current_savings=150000.0, target_months=6.0)
    assert res["target_fund"] == 120000.0
    assert res["funding_gap"] == 0.0
    assert res["months_covered"] == 7.5
