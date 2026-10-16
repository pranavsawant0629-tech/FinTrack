"""
Deterministic Emergency Fund Adequacy Calculator for Finova AI.

Formulas & Assumptions:
- Target Fund T = monthly_expenses * target_months (default 6 months)
- Funding Gap = max(0, Target - current_savings)
- Months Covered = current_savings / monthly_expenses
"""

from __future__ import annotations
from typing import Any


def calculate_emergency_fund(
    monthly_expenses: float,
    current_savings: float = 0.0,
    target_months: float = 6.0,
) -> dict[str, Any]:
    """Calculate emergency fund adequacy and funding gap deterministically."""
    if monthly_expenses <= 0:
        raise ValueError("Monthly expenses must be greater than zero.")
    if current_savings < 0:
        raise ValueError("Current savings cannot be negative.")
    if target_months <= 0:
        raise ValueError("Target months must be positive.")

    target_fund = round(monthly_expenses * target_months, 2)
    funding_gap = round(max(0.0, target_fund - current_savings), 2)
    months_covered = round(current_savings / monthly_expenses, 1)

    return {
        "type": "emergency_fund",
        "title": "Emergency Fund Adequacy Analysis",
        "monthly_expenses": round(monthly_expenses, 2),
        "target_months": round(target_months, 1),
        "target_fund": target_fund,
        "current_savings": round(current_savings, 2),
        "funding_gap": funding_gap,
        "months_covered": months_covered,
    }
