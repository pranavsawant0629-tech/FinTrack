"""
Deterministic 50/30/20 Budgeting Calculator for Finova AI.

Formula & Assumptions:
Input is monthly net (post-tax) income I > 0.
- Needs (50%): Essential expenses (housing, utilities, groceries, transport).
- Wants (30%): Discretionary spending (dining, entertainment, hobbies).
- Savings & Debt Repayment (20%): Emergency fund, investments, extra debt payoff.
"""

from __future__ import annotations
from typing import Any


def calculate_50_30_20(income: float) -> dict[str, Any]:
    """Calculate the 50/30/20 budget breakdown for a given monthly net income."""
    if income <= 0:
        raise ValueError("Monthly income must be greater than zero.")

    needs = round(income * 0.50, 2)
    wants = round(income * 0.30, 2)
    savings = round(income * 0.20, 2)

    return {
        "type": "budget_50_30_20",
        "title": "50/30/20 Budget Breakdown",
        "income": round(income, 2),
        "needs": needs,
        "wants": wants,
        "savings": savings,
        "needs_pct": 50.0,
        "wants_pct": 30.0,
        "savings_pct": 20.0,
    }
