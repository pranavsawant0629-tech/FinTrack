"""
Portfolio service coordinating portfolio retrieval, deterministic accounting metrics,
and what-if simulation stress tests.
"""

from __future__ import annotations

import logging
import math
from app.tools.portfolio.interfaces import BasePortfolioProvider
from app.tools.portfolio.models import (
    PortfolioData,
    PortfolioMetrics,
    WhatIfHoldingImpact,
    WhatIfSimulationResult,
)
from app.tools.portfolio.providers.mock import MockPortfolioProvider, create_demo_portfolio

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service providing portfolio analytics and deterministic simulations."""

    def __init__(self, provider: BasePortfolioProvider | None = None) -> None:
        self.provider = provider or MockPortfolioProvider()

    def get_portfolio(self, user_id: str) -> PortfolioData | None:
        """Fetch portfolio for a specific user partition."""
        return self.provider.get_portfolio(user_id)

    def save_portfolio(self, portfolio: PortfolioData) -> bool:
        """Persist portfolio for a user partition."""
        return self.provider.save_portfolio(portfolio)

    def calculate_metrics(
        self,
        portfolio: PortfolioData,
        exchange_rates: dict[str, float] | None = None,
    ) -> PortfolioMetrics:
        """
        Calculate deterministic financial metrics with rigorous separation of
        invested capital (cost basis) and uninvested cash liquidity.

        Currency & Conversion Specification:
        - Base portfolio reporting currency is portfolio.currency (defaults to "INR").
        - If all holdings match the base currency, exchange_rates is optional.
        - If any holding currency differs from base currency:
          * exchange_rates must be provided as an explicit dictionary mapping source currency -> base currency.
          * Rate definition: 1 unit of source_currency = exchange_rates[source_currency] base_currency units.
            (Formula: converted_val = local_val * rate)
          * Every non-base currency in holdings must be explicitly present in exchange_rates.
          * Rates must be finite, strictly positive (> 0) numbers. Zero, negative, NaN, infinite,
            or non-numeric rates raise ValueError.
          * If base currency is present in exchange_rates, its rate must be exactly 1.0.
          * Live rates are NEVER fetched; rates are NEVER guessed or assumed.
        """
        portfolio_currency = (portfolio.currency or "INR").strip().upper()

        # Normalize exchange rates dictionary if provided
        norm_rates: dict[str, float] = {}
        if exchange_rates is not None:
            if not isinstance(exchange_rates, dict):
                raise ValueError(f"exchange_rates must be a dictionary, got: {type(exchange_rates).__name__}")
            for curr_code, rate_val in exchange_rates.items():
                if not isinstance(curr_code, str):
                    raise ValueError(f"Exchange rate currency key must be a string, got: {type(curr_code).__name__}")
                clean_curr = curr_code.strip().upper()
                if (
                    isinstance(rate_val, bool)
                    or not isinstance(rate_val, (int, float))
                    or math.isnan(rate_val)
                    or math.isinf(rate_val)
                    or rate_val <= 0.0
                ):
                    raise ValueError(
                        f"Invalid exchange rate for currency '{clean_curr}': {rate_val}. "
                        "Exchange rates must be finite, strictly positive (> 0) numbers."
                    )
                norm_rates[clean_curr] = float(rate_val)

            # Validate base currency rate if provided
            if portfolio_currency in norm_rates and norm_rates[portfolio_currency] != 1.0:
                raise ValueError(
                    f"Invalid exchange rate for base currency '{portfolio_currency}': {norm_rates[portfolio_currency]}. "
                    "The exchange rate of base currency to itself must be exactly 1.0."
                )

        # Validate and convert holdings: (holding, conv_cost_basis, conv_market_value)
        converted_holdings: list[tuple[Holding, float, float]] = []
        for h in portfolio.holdings:
            h_curr = (h.currency or "INR").strip().upper()
            if h_curr == portfolio_currency:
                rate = 1.0
            else:
                if exchange_rates is None:
                    raise ValueError(
                        f"Mixed currency detected: holding '{h.symbol}' currency '{h_curr}' "
                        f"does not match portfolio base currency '{portfolio_currency}'. "
                        f"Mixed currencies require explicit exchange-rate conversion mappings."
                    )
                if h_curr not in norm_rates:
                    raise ValueError(
                        f"Missing explicit exchange rate for non-base currency '{h_curr}'. "
                        f"Base currency is '{portfolio_currency}'. Every non-base currency must have a valid rate in exchange_rates."
                    )
                rate = norm_rates[h_curr]

            conv_cost = round(h.cost_basis * rate, 2)
            conv_value = round(h.market_value * rate, 2)
            converted_holdings.append((h, conv_cost, conv_value))

        securities_cost = round(sum(ch[1] for ch in converted_holdings), 2)
        securities_value = round(sum(ch[2] for ch in converted_holdings), 2)
        cash = round(portfolio.cash_balance, 2)
        total_val = round(securities_value + cash, 2)

        unrealized_pnl = round(securities_value - securities_cost, 2)
        unrealized_pnl_pct = (
            round((unrealized_pnl / securities_cost) * 100, 2)
            if securities_cost > 0
            else 0.0
        )

        # Asset Allocation (% of total portfolio value including cash)
        # Aggregate raw market values first to prevent iterative rounding drift
        asset_alloc: dict[str, float] = {}
        if total_val > 0:
            raw_asset_values: dict[str, float] = {}
            if cash > 0:
                raw_asset_values["cash"] = cash

            for h, _, conv_val in converted_holdings:
                raw_asset_values[h.asset_type] = raw_asset_values.get(h.asset_type, 0.0) + conv_val

            for a_type, raw_val in raw_asset_values.items():
                asset_alloc[a_type] = round((raw_val / total_val) * 100, 2)
        else:
            asset_alloc["cash"] = 100.0

        # Sector Allocation (% of securities market value)
        # Aggregate raw market values first to prevent iterative rounding drift
        sector_alloc: dict[str, float] = {}
        if securities_value > 0:
            raw_sector_values: dict[str, float] = {}
            for h, _, conv_val in converted_holdings:
                raw_sector_values[h.sector] = raw_sector_values.get(h.sector, 0.0) + conv_val

            for sec, raw_val in raw_sector_values.items():
                sector_alloc[sec] = round((raw_val / securities_value) * 100, 2)

        # Top Holding Concentration
        top_symbol = ""
        top_conc = 0.0
        if converted_holdings and total_val > 0:
            sorted_holdings = sorted(converted_holdings, key=lambda x: x[2], reverse=True)
            top_symbol = sorted_holdings[0][0].symbol
            top_conc = round((sorted_holdings[0][2] / total_val) * 100, 2)

        # Diversification Assessment
        if top_conc > 40.0:
            diversification = f"High Concentration Risk: Top asset ({top_symbol}) represents {top_conc:.1f}% of total portfolio value."
        elif top_conc > 25.0:
            diversification = f"Moderate Concentration: Top asset ({top_symbol}) represents {top_conc:.1f}% of total portfolio value."
        elif len(portfolio.holdings) >= 3:
            diversification = f"Well Diversified: Balanced allocation with top asset at {top_conc:.1f}% of total portfolio value."
        else:
            diversification = "Limited Diversification: Few holdings in simulated portfolio."

        return PortfolioMetrics(
            currency=portfolio_currency,
            securities_cost_basis=securities_cost,
            securities_market_value=securities_value,
            cash_balance=cash,
            total_portfolio_value=total_val,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            asset_allocation=asset_alloc,
            sector_allocation=sector_alloc,
            top_holding_symbol=top_symbol,
            top_holding_concentration_pct=top_conc,
            diversification_assessment=diversification,
        )

    def simulate_what_if(
        self,
        portfolio: PortfolioData,
        target_symbol: str | None,
        change_pct: float,
        broad_market: bool = False,
        exchange_rates: dict[str, float] | None = None,
    ) -> WhatIfSimulationResult:
        """
        Execute a deterministic price shock simulation on target holdings without mutating stored data.
        """
        orig_metrics = self.calculate_metrics(portfolio, exchange_rates=exchange_rates)
        orig_val = orig_metrics.total_portfolio_value
        portfolio_currency = (portfolio.currency or "INR").strip().upper()

        norm_rates: dict[str, float] = {}
        if exchange_rates is not None:
            norm_rates = {k.strip().upper(): float(v) for k, v in exchange_rates.items()}

        impacted: list[WhatIfHoldingImpact] = []
        simulated_securities_val = 0.0

        for h in portfolio.holdings:
            h_curr = (h.currency or "INR").strip().upper()
            rate = 1.0 if h_curr == portfolio_currency else norm_rates[h_curr]
            conv_market_val = round(h.market_value * rate, 2)

            is_target = broad_market or (target_symbol is not None and h.symbol.upper() == target_symbol.upper())
            if is_target:
                sim_price = round(h.current_price * (1.0 + (change_pct / 100.0)), 2)
                sim_val_local = round(h.quantity * sim_price, 2)
                sim_val_base = round(sim_val_local * rate, 2)
                delta = round(sim_val_base - conv_market_val, 2)
                impacted.append(
                    WhatIfHoldingImpact(
                        symbol=h.symbol,
                        original_price=h.current_price,
                        simulated_price=sim_price,
                        price_change_pct=change_pct,
                        value_delta=delta,
                    )
                )
                simulated_securities_val += sim_val_base
            else:
                simulated_securities_val += conv_market_val

        sim_total_val = round(simulated_securities_val + portfolio.cash_balance, 2)
        portfolio_delta = round(sim_total_val - orig_val, 2)
        portfolio_delta_pct = (
            round((portfolio_delta / orig_val) * 100, 2)
            if orig_val > 0
            else 0.0
        )

        target_desc = "broad market (all equity/ETF holdings)" if broad_market or not target_symbol else f"{target_symbol.upper()}"
        sign = "+" if change_pct > 0 else ""
        desc = f"Simulated {sign}{change_pct:.1f}% price shock on {target_desc}"

        return WhatIfSimulationResult(
            scenario_description=desc,
            original_portfolio_value=orig_val,
            simulated_portfolio_value=sim_total_val,
            portfolio_delta_value=portfolio_delta,
            portfolio_delta_pct=portfolio_delta_pct,
            impacted_holdings=impacted,
        )


portfolio_service = PortfolioService()
