"""
Unit tests for portfolio currency uniformity and allocation rounding precision.
Verifies:
- Uniform INR portfolio calculation (default behavior preserved)
- Uniform USD portfolio calculation
- Rejection of mixed-currency portfolios without explicit exchange-rate conversion
- Elimination of iterative allocation rounding drift
"""

import pytest
from app.tools.portfolio.models import Holding, PortfolioData
from app.tools.portfolio.providers.mock import create_demo_portfolio
from app.tools.portfolio.service import portfolio_service


class TestPortfolioCurrencyValidation:
    """Tests currency validation across portfolio and individual holdings."""

    def test_uniform_inr_portfolio(self):
        """Standard INR portfolio calculates metrics properly."""
        portfolio = PortfolioData(
            user_id="inr_user",
            currency="INR",
            cash_balance=10000.0,
            holdings=[
                Holding(
                    symbol="TCS",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=3500.0,
                    current_price=3800.0,
                    currency="INR",
                ),
                Holding(
                    symbol="INFY",
                    asset_type="equity",
                    quantity=20.0,
                    average_buy_price=1400.0,
                    current_price=1500.0,
                    currency="INR",
                ),
            ],
        )
        metrics = portfolio_service.calculate_metrics(portfolio)
        assert metrics.currency == "INR"
        assert metrics.cash_balance == 10000.0
        assert metrics.securities_market_value == 68000.0  # 38000 + 30000
        assert metrics.total_portfolio_value == 78000.0

    def test_uniform_usd_portfolio(self):
        """Uniform USD portfolio calculates metrics properly in USD."""
        portfolio = PortfolioData(
            user_id="usd_user",
            currency="USD",
            cash_balance=5000.0,
            holdings=[
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=180.0,
                    current_price=220.0,
                    sector="Technology",
                    currency="USD",
                ),
                Holding(
                    symbol="MSFT",
                    asset_type="equity",
                    quantity=5.0,
                    average_buy_price=400.0,
                    current_price=420.0,
                    sector="Technology",
                    currency="USD",
                ),
            ],
        )
        metrics = portfolio_service.calculate_metrics(portfolio)
        assert metrics.currency == "USD"
        assert metrics.cash_balance == 5000.0
        assert metrics.securities_market_value == 4300.0  # 2200 + 2100
        assert metrics.total_portfolio_value == 9300.0
        assert metrics.top_holding_symbol == "AAPL"

    def test_mixed_currency_raises_value_error(self):
        """Mixed currencies (e.g. INR portfolio with USD holding) must be rejected."""
        portfolio = PortfolioData(
            user_id="mixed_user",
            currency="INR",
            cash_balance=10000.0,
            holdings=[
                Holding(
                    symbol="TCS",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=3500.0,
                    current_price=3800.0,
                    currency="INR",
                ),
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=5.0,
                    average_buy_price=180.0,
                    current_price=220.0,
                    currency="USD",
                ),
            ],
        )
        with pytest.raises(ValueError, match="Mixed currency detected"):
            portfolio_service.calculate_metrics(portfolio)

    def test_mixed_currency_in_simulation_raises_value_error(self):
        """What-if simulation also strictly enforces currency uniformity."""
        portfolio = PortfolioData(
            user_id="mixed_sim_user",
            currency="USD",
            cash_balance=1000.0,
            holdings=[
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=5.0,
                    average_buy_price=180.0,
                    current_price=220.0,
                    currency="USD",
                ),
                Holding(
                    symbol="RELIANCE",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=2800.0,
                    current_price=2900.0,
                    currency="INR",
                ),
            ],
        )
        with pytest.raises(ValueError, match="Mixed currency detected"):
            portfolio_service.simulate_what_if(portfolio, target_symbol="AAPL", change_pct=10.0)

    def test_demo_portfolio_currency_preserved(self):
        """Demo portfolio defaults to INR and computes valid metrics."""
        demo = create_demo_portfolio("demo_user")
        metrics = portfolio_service.calculate_metrics(demo)
        assert metrics.currency == "INR"
        assert metrics.total_portfolio_value > 0
        assert "equity" in metrics.asset_allocation


class TestAllocationRoundingPrecision:
    """Tests that aggregation eliminates iterative rounding drift across multiple holdings."""

    def test_no_iterative_rounding_drift_in_asset_allocation(self):
        """Multiple holdings of same asset type aggregate cleanly."""
        holdings = [
            Holding(
                symbol=f"STOCK_{i}",
                asset_type="equity",
                quantity=10.0,
                average_buy_price=100.0,
                current_price=100.0,
                sector="Technology",
                currency="INR",
            )
            for i in range(7)
        ]
        # Total equity value = 7 * 1000 = 7000
        # Cash = 3000 -> Total portfolio = 10000
        portfolio = PortfolioData(
            user_id="test_drift",
            currency="INR",
            cash_balance=3000.0,
            holdings=holdings,
        )
        metrics = portfolio_service.calculate_metrics(portfolio)
        assert metrics.asset_allocation["equity"] == 70.0
        assert metrics.asset_allocation["cash"] == 30.0
        assert metrics.sector_allocation["Technology"] == 100.0

