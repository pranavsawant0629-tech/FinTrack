"""
Deterministic Financial Calculation Tools for Finova AI.
"""

from app.tools.calc.budget import calculate_50_30_20
from app.tools.calc.compounding import calculate_compound_interest, calculate_sip
from app.tools.calc.emergency_fund import calculate_emergency_fund
from app.tools.calc.extended import (
    calculate_cagr,
    calculate_real_return,
    calculate_rule_of_72,
)
from app.tools.calc.parser import parse_indian_number, try_parse_indian_number

__all__ = [
    "calculate_50_30_20",
    "calculate_compound_interest",
    "calculate_emergency_fund",
    "calculate_sip",
    "calculate_cagr",
    "calculate_real_return",
    "calculate_rule_of_72",
    "parse_indian_number",
    "try_parse_indian_number",
]
