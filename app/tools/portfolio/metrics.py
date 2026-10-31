"""
Deterministic Risk-Adjusted Return Metrics for FinTrack.

Implements mathematically rigorous Sharpe and Sortino ratio calculations:
- Periodic decimal return series
- Explicit, caller-provided periodic risk-free rate (Rf) and Minimum Acceptable Return (MAR)
- Arithmetic mean and sample standard deviation (N - 1)
- Downside semi-deviation using Lower Partial Moment (LPM) of degree 2 with N denominator
- Single consistent annualization convention:
    Annualized Return = Periodic Mean * Frequency
    Annualized Volatility = Periodic Std Dev * sqrt(Frequency)
    Annualized Downside Dev = Periodic Downside Dev * sqrt(Frequency)
    Annualized Ratio = Periodic Ratio * sqrt(Frequency)
- Safe handling of zero variance and zero downside deviation (returns None with status code)
"""

from __future__ import annotations

import math
from typing import Literal
from pydantic import BaseModel, Field


FrequencyType = Literal["daily", "weekly", "monthly", "annual"]

FREQUENCY_MULTIPLIERS: dict[FrequencyType, int] = {
    "daily": 252,
    "weekly": 52,
    "monthly": 12,
    "annual": 1,
}


class RiskAdjustedMetricsResult(BaseModel):
    """Deterministic result of Sharpe and Sortino ratio evaluation."""
    frequency: FrequencyType
    frequency_multiplier: int
    observation_count: int
    periodic_mean_return: float
    annualized_mean_return: float
    periodic_std_dev: float
    annualized_std_dev: float
    periodic_downside_dev: float
    annualized_downside_dev: float
    risk_free_rate_periodic: float
    mar_periodic: float
    periodic_sharpe_ratio: float | None = None
    annualized_sharpe_ratio: float | None = None
    sharpe_status: str = Field(
        default="ok",
        description="'ok' or 'undefined_zero_variance' when standard deviation is zero",
    )
    periodic_sortino_ratio: float | None = None
    annualized_sortino_ratio: float | None = None
    sortino_status: str = Field(
        default="ok",
        description="'ok' or 'undefined_zero_downside' when no returns fall below MAR",
    )
    methodology_notes: list[str] = Field(default_factory=list)


def calculate_risk_adjusted_metrics(
    returns: list[float],
    risk_free_rate: float,
    mar: float | None = None,
    frequency: FrequencyType = "monthly",
    is_annual_risk_free_rate: bool = False,
) -> RiskAdjustedMetricsResult:
    """
    Calculate deterministic Sharpe and Sortino ratios for a series of periodic decimal returns.

    Args:
        returns: List of periodic returns as decimals (e.g. [0.02, -0.01, 0.03]).
        risk_free_rate: Risk-free benchmark rate. Must share the observation periodicity of the returns
                        unless is_annual_risk_free_rate=True is explicitly specified.
        mar: Minimum Acceptable Return (per period) for Sortino. Defaults to risk_free_rate if omitted.
        frequency: Observation periodicity ('daily', 'weekly', 'monthly', 'annual').
        is_annual_risk_free_rate: If True, divides risk_free_rate and MAR by the frequency multiplier k
                                  to ensure matching periodicity.

    Returns:
        RiskAdjustedMetricsResult with periodic and annualized metrics.

    Raises:
        ValueError: If fewer than 3 observations are provided, if inputs are non-finite,
                    or if frequency is unrecognized.
    """
    if frequency not in FREQUENCY_MULTIPLIERS:
        raise ValueError(
            f"Invalid frequency: '{frequency}'. Must be one of: {list(FREQUENCY_MULTIPLIERS.keys())}"
        )

    k = FREQUENCY_MULTIPLIERS[frequency]

    if not returns or len(returns) < 3:
        raise ValueError(
            f"Minimum 3 periodic return observations required for computational boundary, got: {len(returns) if returns else 0}. "
            "Note: N >= 3 is an algorithmic implementation constraint for sample degrees of freedom (N - 1 >= 2), "
            "not a claim of real-world statistical significance."
        )

    for idx, r in enumerate(returns):
        if math.isnan(r) or math.isinf(r):
            raise ValueError(f"Non-finite return observation at index {idx}: {r}")

    if math.isnan(risk_free_rate) or math.isinf(risk_free_rate):
        raise ValueError(f"Non-finite risk_free_rate provided: {risk_free_rate}")

    # Ensure matching periodicity
    if is_annual_risk_free_rate:
        rf_periodic = risk_free_rate / float(k)
        mar_periodic = (mar / float(k)) if mar is not None else rf_periodic
    else:
        rf_periodic = float(risk_free_rate)
        mar_periodic = float(mar) if mar is not None else rf_periodic

    if math.isnan(mar_periodic) or math.isinf(mar_periodic):
        raise ValueError(f"Non-finite MAR provided: {mar_periodic}")

    n = len(returns)
    notes: list[str] = [
        f"Sample size N = {n} (implementation constraint N >= 3).",
        f"Frequency: '{frequency}' (k = {k}).",
        f"Periodic Risk-Free Rate Rf = {rf_periodic:.6f}, Periodic MAR = {mar_periodic:.6f}.",
    ]

    # 1. Periodic Arithmetic Mean
    mean_r = sum(returns) / float(n)

    # 2. Sample Standard Deviation (N - 1 degrees of freedom)
    sum_sq_diff = sum((r - mean_r) ** 2 for r in returns)
    variance = sum_sq_diff / float(n - 1)
    std_dev = math.sqrt(variance)

    # 3. Downside Semi-Deviation (LPM degree 2 with N denominator)
    sum_downside_sq = sum(min(0.0, r - mar_periodic) ** 2 for r in returns)
    downside_variance = sum_downside_sq / float(n)
    downside_dev = math.sqrt(downside_variance)

    # 4. Annualized components (consistent arithmetic convention)
    annualized_mean = mean_r * float(k)
    sqrt_k = math.sqrt(float(k))
    annualized_std = std_dev * sqrt_k
    annualized_downside = downside_dev * sqrt_k

    # 5. Sharpe Ratio Evaluation
    periodic_sharpe: float | None = None
    annualized_sharpe: float | None = None
    sharpe_status = "ok"

    if std_dev == 0.0 or math.isclose(std_dev, 0.0, abs_tol=1e-12):
        sharpe_status = "undefined_zero_variance"
        notes.append("Sharpe ratio is undefined because sample standard deviation is zero (zero variance).")
    else:
        periodic_sharpe = (mean_r - rf_periodic) / std_dev
        annualized_sharpe = periodic_sharpe * sqrt_k

    # 6. Sortino Ratio Evaluation
    periodic_sortino: float | None = None
    annualized_sortino: float | None = None
    sortino_status = "ok"

    if downside_dev == 0.0 or math.isclose(downside_dev, 0.0, abs_tol=1e-12):
        sortino_status = "undefined_zero_downside"
        notes.append(
            "Sortino ratio is undefined because downside semi-deviation is zero (no returns fell below MAR)."
        )
    else:
        periodic_sortino = (mean_r - mar_periodic) / downside_dev
        annualized_sortino = periodic_sortino * sqrt_k

    return RiskAdjustedMetricsResult(
        frequency=frequency,
        frequency_multiplier=k,
        observation_count=n,
        periodic_mean_return=round(mean_r, 6),
        annualized_mean_return=round(annualized_mean, 6),
        periodic_std_dev=round(std_dev, 6),
        annualized_std_dev=round(annualized_std, 6),
        periodic_downside_dev=round(downside_dev, 6),
        annualized_downside_dev=round(annualized_downside, 6),
        risk_free_rate_periodic=round(rf_periodic, 6),
        mar_periodic=round(mar_periodic, 6),
        periodic_sharpe_ratio=round(periodic_sharpe, 4) if periodic_sharpe is not None else None,
        annualized_sharpe_ratio=round(annualized_sharpe, 4) if annualized_sharpe is not None else None,
        sharpe_status=sharpe_status,
        periodic_sortino_ratio=round(periodic_sortino, 4) if periodic_sortino is not None else None,
        annualized_sortino_ratio=round(annualized_sortino, 4) if annualized_sortino is not None else None,
        sortino_status=sortino_status,
        methodology_notes=notes,
    )

