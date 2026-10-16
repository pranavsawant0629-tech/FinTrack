"""
Deterministic Compound Interest & SIP Calculators for Finova AI.

Formulas & Assumptions:
1. Compound Interest:
   A = P * (1 + r/n)^(n*t)
   Interest = A - P
   Where:
   - P = Initial Principal (> 0)
   - r = Annual nominal interest rate as decimal (annual_rate_pct / 100)
   - n = Compounding frequency per year (default 1 for annual)
   - t = Investment tenure in years (> 0)

2. SIP (Systematic Investment Plan - Annuity Due):
   M = P * [((1 + i)^k - 1) / i] * (1 + i)
   Where:
   - P = Monthly installment (> 0)
   - i = Periodic monthly rate ((annual_return_pct / 100) / 12)
   - k = Total months (tenure_years * 12)
"""

from __future__ import annotations
from typing import Any


def calculate_compound_interest(
    principal: float,
    annual_rate_pct: float,
    tenure_years: float,
    compounding_frequency: int = 1,
) -> dict[str, Any]:
    """Calculate compound interest and maturity amount deterministically."""
    if principal <= 0:
        raise ValueError("Principal must be greater than zero.")
    if annual_rate_pct <= 0:
        raise ValueError("Annual rate must be greater than zero.")
    if tenure_years <= 0:
        raise ValueError("Tenure must be greater than zero.")
    if compounding_frequency <= 0:
        raise ValueError("Compounding frequency must be positive.")

    r = annual_rate_pct / 100.0
    n = compounding_frequency
    t = tenure_years

    maturity_amount = round(principal * ((1.0 + (r / n)) ** (n * t)), 2)
    interest_earned = round(maturity_amount - principal, 2)

    return {
        "type": "compound_interest",
        "title": "Compound Interest Growth",
        "principal": round(principal, 2),
        "annual_rate_percent": round(annual_rate_pct, 2),
        "tenure_years": t,
        "compounding_frequency": n,
        "maturity_amount": maturity_amount,
        "interest_earned": interest_earned,
    }


def calculate_sip(
    monthly_investment: float,
    annual_return_pct: float,
    tenure_years: float,
) -> dict[str, Any]:
    """Calculate future value of a Systematic Investment Plan (SIP) using annuity due formula."""
    if monthly_investment <= 0:
        raise ValueError("Monthly investment must be greater than zero.")
    if annual_return_pct <= 0:
        raise ValueError("Expected annual return must be greater than zero.")
    if tenure_years <= 0:
        raise ValueError("Tenure must be greater than zero.")

    p = monthly_investment
    i = (annual_return_pct / 100.0) / 12.0
    k = int(tenure_years * 12)

    # Annuity Due: payment at beginning of each month
    future_value = round(p * (((1.0 + i) ** k - 1.0) / i) * (1.0 + i), 2)
    total_invested = round(p * k, 2)
    wealth_gain = round(future_value - total_invested, 2)

    return {
        "type": "sip_calculation",
        "title": "SIP Wealth Accumulation",
        "monthly_investment": round(p, 2),
        "annual_return_percent": round(annual_return_pct, 2),
        "tenure_years": tenure_years,
        "total_invested": total_invested,
        "future_value": future_value,
        "wealth_gain": wealth_gain,
    }
