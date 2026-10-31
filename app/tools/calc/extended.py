"""
Deterministic Extended Financial Mathematics Engine for FinTrack.

Implements mathematically rigorous, deterministic calculations for:
1. Compound Annual Growth Rate (CAGR)
2. Real (Inflation-Adjusted) Return via the Fisher Equation
3. Rule of 72 Doubling Time Estimation vs. Exact Logarithmic Tenure
"""

from __future__ import annotations

import math
from typing import Any


def calculate_cagr(
    initial_value: float,
    final_value: float,
    tenure_years: float,
) -> dict[str, Any]:
    """
    Calculate deterministic Compound Annual Growth Rate (CAGR).

    Formula:
        CAGR = (final_value / initial_value) ** (1 / tenure_years) - 1.0

    Preconditions & Validation:
        - initial_value must be strictly positive (> 0).
        - final_value must be non-negative (>= 0).
        - tenure_years must be strictly positive (> 0).
        - tenure_years must be at least 1 day (>= 1/365).

    Returns:
        dict with cagr_percent, total_growth_percent, absolute_gain, and metadata.

    Raises:
        ValueError: If any input fails mathematical preconditions.
    """
    if math.isnan(initial_value) or math.isinf(initial_value) or initial_value <= 0:
        raise ValueError(
            f"Initial investment value must be strictly positive and finite, got: {initial_value}"
        )

    if math.isnan(final_value) or math.isinf(final_value) or final_value < 0:
        raise ValueError(
            f"Final investment value cannot be negative or non-finite, got: {final_value}"
        )

    if math.isnan(tenure_years) or math.isinf(tenure_years) or tenure_years <= 0:
        raise ValueError(
            f"Tenure in years must be strictly positive and finite, got: {tenure_years}"
        )

    if tenure_years < (1.0 / 365.0):
        raise ValueError(
            f"Tenure must be at least 1 day (1/365 years) for meaningful CAGR calculation, got: {tenure_years}"
        )

    init_val = float(initial_value)
    fin_val = float(final_value)
    tenure = float(tenure_years)

    if fin_val == 0.0:
        cagr = -1.0
        cagr_pct = -100.0
    else:
        cagr = (fin_val / init_val) ** (1.0 / tenure) - 1.0
        cagr_pct = round(cagr * 100.0, 2)

    total_growth_pct = round(((fin_val - init_val) / init_val) * 100.0, 2)
    absolute_gain = round(fin_val - init_val, 2)

    return {
        "type": "cagr_calculation",
        "title": "Compound Annual Growth Rate (CAGR)",
        "initial_value": round(init_val, 2),
        "final_value": round(fin_val, 2),
        "tenure_years": round(tenure, 4),
        "cagr_percent": cagr_pct,
        "cagr_decimal": round(cagr, 6),
        "total_growth_percent": total_growth_pct,
        "absolute_gain": absolute_gain,
    }


def calculate_real_return(
    nominal_return_pct: float,
    inflation_rate_pct: float,
) -> dict[str, Any]:
    """
    Calculate deterministic Inflation-Adjusted (Real) Return using the Fisher Equation.

    Formula:
        1 + r_real = (1 + r_nominal) / (1 + i)
        r_real = ((1 + r_nominal / 100) / (1 + inflation / 100)) - 1.0

    Preconditions & Validation:
        - inflation_rate_pct cannot be <= -100% (causes division by zero / singularity).
        - nominal_return_pct cannot be < -100% (total loss exceeding 100% is invalid).
        - inputs must be finite numbers.

    Returns:
        dict with exact real return, linear approximation, and purchasing power difference.

    Raises:
        ValueError: If inputs violate financial boundaries.
    """
    if (
        math.isnan(nominal_return_pct)
        or math.isinf(nominal_return_pct)
        or nominal_return_pct < -100.0
    ):
        raise ValueError(
            f"Nominal return cannot be less than -100% or non-finite, got: {nominal_return_pct}"
        )

    if (
        math.isnan(inflation_rate_pct)
        or math.isinf(inflation_rate_pct)
        or inflation_rate_pct <= -100.0
    ):
        raise ValueError(
            f"Inflation rate cannot be -100% or lower (causes singularity / division by zero), got: {inflation_rate_pct}"
        )

    r_nom = float(nominal_return_pct) / 100.0
    inf = float(inflation_rate_pct) / 100.0

    # Exact Fisher Equation
    r_real = ((1.0 + r_nom) / (1.0 + inf)) - 1.0
    real_return_pct = round(r_real * 100.0, 2)

    # Simplified linear approximation for comparison
    approx_return_pct = round(nominal_return_pct - inflation_rate_pct, 2)
    dispersion = round(real_return_pct - approx_return_pct, 2)

    return {
        "type": "real_return_calculation",
        "title": "Inflation-Adjusted (Real) Return",
        "nominal_return_percent": round(nominal_return_pct, 2),
        "inflation_rate_percent": round(inflation_rate_pct, 2),
        "real_return_percent": real_return_pct,
        "real_return_decimal": round(r_real, 6),
        "linear_approximation_percent": approx_return_pct,
        "approximation_error_percent": dispersion,
        "formula": "Exact Fisher Equation: (1 + r_nominal) / (1 + inflation) - 1",
    }


def calculate_rule_of_72(annual_rate_pct: float) -> dict[str, Any]:
    """
    Calculate approximate doubling time via the Rule of 72 alongside exact logarithmic tenure.

    Formulas:
        t_approx = 72.0 / annual_rate_pct
        t_exact = ln(2.0) / ln(1.0 + annual_rate_pct / 100.0)

    Preconditions & Validation:
        - annual_rate_pct must be strictly positive (> 0). Negative and zero rates cannot double capital.
        - annual_rate_pct must be <= 1000.0%.

    Returns:
        dict with approximate doubling time, exact compounding doubling time, and variance.

    Raises:
        ValueError: If annual_rate_pct <= 0 or non-finite.
    """
    if (
        math.isnan(annual_rate_pct)
        or math.isinf(annual_rate_pct)
        or annual_rate_pct <= 0.0
    ):
        raise ValueError(
            f"Annual rate must be strictly positive for Rule of 72 doubling calculation, got: {annual_rate_pct}"
        )

    if annual_rate_pct > 1000.0:
        raise ValueError(
            f"Annual rate exceeds maximum reasonable threshold (1000%), got: {annual_rate_pct}"
        )

    rate = float(annual_rate_pct)
    approx_years = round(72.0 / rate, 2)

    # Exact compound growth doubling time
    exact_years = round(math.log(2.0) / math.log(1.0 + (rate / 100.0)), 2)
    discrepancy_years = round(abs(approx_years - exact_years), 2)

    return {
        "type": "rule_of_72_calculation",
        "title": "Rule of 72 Doubling Time Estimation",
        "annual_rate_percent": round(rate, 2),
        "approximate_doubling_years": approx_years,
        "exact_doubling_years": exact_years,
        "estimation_discrepancy_years": discrepancy_years,
        "pedagogical_note": (
            "The Rule of 72 is an educational mental-model heuristic. "
            "For rigorous planning, FinTrack also computes the exact logarithmic compound tenure."
        ),
    }

