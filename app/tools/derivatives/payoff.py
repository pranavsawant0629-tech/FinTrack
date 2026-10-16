"""
Deterministic mathematical calculation engine for derivatives payoffs.

Guarantees:
1. Pure mathematical calculation without LLM involvement.
2. Exact numerical payoff, breakeven, and P&L outputs.
3. Strict parameter validation (raises ValueError on invalid inputs).
"""

from __future__ import annotations

from app.tools.derivatives.models import (
    FuturesPayoffPoint,
    FuturesPayoffResult,
    OptionPayoffPoint,
    OptionPayoffResult,
    OptionPosition,
    OptionType,
)


def calculate_option_payoff(
    option_type: str,
    position: str,
    strike_price: float,
    premium: float,
    spot_range: list[float] | None = None,
) -> OptionPayoffResult:
    """
    Calculate deterministic option payoff and P&L across a schedule of underlying spot prices.

    Args:
        option_type: 'call' or 'put' (case-insensitive)
        position: 'long' or 'short' (case-insensitive)
        strike_price: Strike price K (> 0)
        premium: Premium paid or received (>= 0)
        spot_range: Optional explicit list of spot prices at expiration

    Returns:
        OptionPayoffResult with exact breakeven, max profit/loss, and payoff table.

    Raises:
        ValueError: If strike_price <= 0, premium < 0, or invalid option_type/position.
    """
    opt_type_clean = option_type.strip().lower()
    if opt_type_clean not in ("call", "put"):
        raise ValueError(f"Invalid option_type: '{option_type}'. Must be 'call' or 'put'.")

    pos_clean = position.strip().lower()
    if pos_clean not in ("long", "short"):
        raise ValueError(f"Invalid position: '{position}'. Must be 'long' or 'short'.")

    if strike_price <= 0:
        raise ValueError(f"Strike price must be strictly positive, got: {strike_price}")
    if strike_price > 1e12:
        raise ValueError(f"Strike price exceeds maximum allowable bound (1e12): {strike_price}")

    if premium < 0:
        raise ValueError(f"Option premium cannot be negative, got: {premium}")
    if premium > 1e12:
        raise ValueError(f"Option premium exceeds maximum allowable bound (1e12): {premium}")

    strike = round(float(strike_price), 2)
    prem = round(float(premium), 2)

    # Breakeven Calculation
    if opt_type_clean == "call":
        breakeven = round(strike + prem, 2)
        has_feasible_be = True
    else:  # put
        breakeven = round(strike - prem, 2)
        has_feasible_be = breakeven >= 0.0

    # Max Profit & Max Loss
    if opt_type_clean == "call":
        if pos_clean == "long":
            max_profit: float | str = "Unlimited"
            max_loss: float | str = prem
        else:  # short call
            max_profit = prem
            max_loss = "Unlimited"
    else:  # put
        if pos_clean == "long":
            max_profit = round(strike - prem, 2)
            max_loss = prem
        else:  # short put
            max_profit = prem
            max_loss = round(strike - prem, 2)

    # Generate default discrete spot price schedule if not explicitly provided
    if spot_range is None or len(spot_range) == 0:
        multipliers = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
        spots = sorted(set([round(strike * m, 2) for m in multipliers] + [breakeven]))
    else:
        spots = sorted([round(float(s), 2) for s in spot_range])

    payoff_table: list[OptionPayoffPoint] = []
    for spot in spots:
        if opt_type_clean == "call":
            gross_payoff = max(0.0, round(spot - strike, 2))
        else:
            gross_payoff = max(0.0, round(strike - spot, 2))

        if pos_clean == "long":
            net_pnl = round(gross_payoff - prem, 2)
            pt_payoff = gross_payoff
        else:
            net_pnl = round(prem - gross_payoff, 2)
            pt_payoff = round(-gross_payoff, 2)

        payoff_table.append(
            OptionPayoffPoint(
                spot_price=spot,
                payoff=pt_payoff,
                pnl=net_pnl,
            )
        )

    return OptionPayoffResult(
        option_type=opt_type_clean,  # type: ignore[arg-type]
        position=pos_clean,  # type: ignore[arg-type]
        strike_price=strike,
        premium=prem,
        breakeven_price=breakeven,
        has_feasible_breakeven=has_feasible_be,
        max_profit=max_profit,
        max_loss=max_loss,
        payoff_table=payoff_table,
    )


def calculate_futures_pnl(
    position: str,
    entry_price: float,
    lot_size: int,
    exit_prices: list[float] | None = None,
) -> FuturesPayoffResult:
    """
    Calculate deterministic futures contract P&L across exit/settlement prices.

    Args:
        position: 'long' or 'short' (case-insensitive)
        entry_price: Contract entry / trade price F_0 (> 0)
        lot_size: Number of units per contract lot (> 0)
        exit_prices: Optional list of hypothetical exit prices

    Returns:
        FuturesPayoffResult with breakeven and total P&L table.

    Raises:
        ValueError: If entry_price <= 0, lot_size <= 0, or invalid position.
    """
    pos_clean = position.strip().lower()
    if pos_clean not in ("long", "short"):
        raise ValueError(f"Invalid position: '{position}'. Must be 'long' or 'short'.")

    if entry_price <= 0:
        raise ValueError(f"Entry price must be strictly positive, got: {entry_price}")

    if lot_size <= 0:
        raise ValueError(f"Lot size must be strictly positive, got: {lot_size}")

    entry = round(float(entry_price), 2)
    lot = int(lot_size)

    if exit_prices is None or len(exit_prices) == 0:
        multipliers = [0.90, 0.95, 1.00, 1.05, 1.10]
        exits = [round(entry * m, 2) for m in multipliers]
    else:
        exits = sorted([round(float(p), 2) for p in exit_prices])

    table: list[FuturesPayoffPoint] = []
    for exit_p in exits:
        if pos_clean == "long":
            unit_pnl = round(exit_p - entry, 2)
        else:
            unit_pnl = round(entry - exit_p, 2)

        total = round(unit_pnl * lot, 2)
        table.append(
            FuturesPayoffPoint(
                exit_price=exit_p,
                pnl_per_unit=unit_pnl,
                total_pnl=total,
            )
        )

    return FuturesPayoffResult(
        position=pos_clean,  # type: ignore[arg-type]
        entry_price=entry,
        lot_size=lot,
        breakeven_price=entry,
        payoff_table=table,
    )
