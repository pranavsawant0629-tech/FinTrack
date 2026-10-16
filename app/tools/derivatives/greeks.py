"""
Option Greeks catalog and pedagogical explanations.
Provides conceptual definitions, bounds, and practical intuition for option sensitivities.
"""

from __future__ import annotations

from app.tools.derivatives.models import GreeksInfo

GREEKS_CATALOG: dict[str, GreeksInfo] = {
    "delta": GreeksInfo(
        name="Delta",
        symbol="Δ",
        definition="Measures the expected change in option price for a ₹1 change in the underlying stock price.",
        range_or_bound="0.0 to +1.0 for Calls; -1.0 to 0.0 for Puts; exactly 1.0 for Futures.",
        primary_driver="Underlying asset price movement.",
        pedagogical_example="If a NIFTY Call option has a Delta of 0.50, and NIFTY rises by ₹10, the option premium is expected to increase by approximately ₹5 (0.50 × ₹10).",
    ),
    "gamma": GreeksInfo(
        name="Gamma",
        symbol="Γ",
        definition="Measures the rate of change of Delta for a ₹1 change in the underlying stock price (the curvature / acceleration of option price).",
        range_or_bound="Always positive for Long options (both calls and puts); highest for At-The-Money (ATM) options near expiration.",
        primary_driver="Underlying asset price sensitivity relative to strike.",
        pedagogical_example="If Delta is 0.50 and Gamma is 0.05, when the stock rises by ₹1, the new Delta becomes approximately 0.55. Gamma shows how quickly your directional sensitivity changes.",
    ),
    "theta": GreeksInfo(
        name="Theta",
        symbol="Θ",
        definition="Measures the rate of decay in an option's premium over time, assuming all other market variables remain constant (Time Decay).",
        range_or_bound="Typically negative for Long options (buyers lose value over time); positive for Option Sellers.",
        primary_driver="Time to expiration (calendar time passing).",
        pedagogical_example="If an option has a Theta of -₹2.50, holding the contract for one full calendar day without any underlying stock movement will erode roughly ₹2.50 from its premium.",
    ),
    "vega": GreeksInfo(
        name="Vega",
        symbol="ν",
        definition="Measures the sensitivity of an option's price to a 1% change in the underlying asset's Implied Volatility (IV).",
        range_or_bound="Always positive for Long options; increases with longer time to expiration; highest for ATM options.",
        primary_driver="Implied Volatility (market expectation of future price swings).",
        pedagogical_example="If an option has a Vega of ₹1.20 and implied volatility spikes from 15% to 17% (+2%), the option premium increases by approximately ₹2.40 (2 × ₹1.20) even if the stock price doesn't move.",
    ),
    "rho": GreeksInfo(
        name="Rho",
        symbol="ρ",
        definition="Measures the expected change in option premium for a 1% change in the risk-free interest rate (e.g. RBI repo rate).",
        range_or_bound="Positive for Call options; negative for Put options; typically has small impact on short-dated contracts.",
        primary_driver="Risk-free interest rates (Cost of Carry).",
        pedagogical_example="A Call option on a high-value index increases slightly in value when interest rates rise, as buying the call requires less upfront capital than buying the underlying shares directly.",
    ),
}


def get_greek_info(name: str) -> GreeksInfo | None:
    """Look up conceptual information for a specific Greek."""
    cleaned = name.strip().lower()
    return GREEKS_CATALOG.get(cleaned)


def get_all_greeks() -> dict[str, GreeksInfo]:
    """Retrieve complete catalog of standard option Greeks."""
    return GREEKS_CATALOG
