"""
Portfolio service coordinating portfolio retrieval, deterministic accounting metrics,
and what-if simulation stress tests.
"""

from __future__ import annotations

import logging
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

    def calculate_metrics(self, portfolio: PortfolioData) -> PortfolioMetrics:
        """
        Calculate deterministic financial metrics with rigorous separation of
        invested capital (cost basis) and uninvested cash liquidity.

        Validates currency uniformity across holdings and portfolio base currency.
        """
        portfolio_currency = (portfolio.currency or "INR").strip().upper()

        # Validate currency uniformity
        for h in portfolio.holdings:
            h_curr = (h.currency or "INR").strip().upper()
            if h_curr != portfolio_currency:
                raise ValueError(
                    f"Mixed currency detected: holding '{h.symbol}' currency '{h_curr}' "
                    f"does not match portfolio base currency '{portfolio_currency}'. "
                    f"Mixed currencies require explicit exchange-rate conversion."
                )

        securities_cost = round(sum(h.cost_basis for h in portfolio.holdings), 2)
        securities_value = round(sum(h.market_value for h in portfolio.holdings), 2)
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

            for h in portfolio.holdings:
                raw_asset_values[h.asset_type] = raw_asset_values.get(h.asset_type, 0.0) + h.market_value

            for a_type, raw_val in raw_asset_values.items():
                asset_alloc[a_type] = round((raw_val / total_val) * 100, 2)
        else:
            asset_alloc["cash"] = 100.0

        # Sector Allocation (% of securities market value)
        # Aggregate raw market values first to prevent iterative rounding drift
        sector_alloc: dict[str, float] = {}
        if securities_value > 0:
            raw_sector_values: dict[str, float] = {}
            for h in portfolio.holdings:
                raw_sector_values[h.sector] = raw_sector_values.get(h.sector, 0.0) + h.market_value

            for sec, raw_val in raw_sector_values.items():
                sector_alloc[sec] = round((raw_val / securities_value) * 100, 2)

        # Top Holding Concentration
        top_symbol = ""
        top_conc = 0.0
        if portfolio.holdings and total_val > 0:
            sorted_holdings = sorted(portfolio.holdings, key=lambda x: x.market_value, reverse=True)
            top_symbol = sorted_holdings[0].symbol
            top_conc = round((sorted_holdings[0].market_value / total_val) * 100, 2)

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
    ) -> WhatIfSimulationResult:
        """
        Execute a deterministic price shock simulation on target holdings without mutating stored data.
        """
        orig_metrics = self.calculate_metrics(portfolio)
        orig_val = orig_metrics.total_portfolio_value

        impacted: list[WhatIfHoldingImpact] = []
        simulated_securities_val = 0.0

        for h in portfolio.holdings:
            is_target = broad_market or (target_symbol is not None and h.symbol.upper() == target_symbol.upper())
            if is_target:
                sim_price = round(h.current_price * (1.0 + (change_pct / 100.0)), 2)
                sim_val = round(h.quantity * sim_price, 2)
                delta = round(sim_val - h.market_value, 2)
                impacted.append(
                    WhatIfHoldingImpact(
                        symbol=h.symbol,
                        original_price=h.current_price,
                        simulated_price=sim_price,
                        price_change_pct=change_pct,
                        value_delta=delta,
                    )
                )
                simulated_securities_val += sim_val
            else:
                simulated_securities_val += h.market_value

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
