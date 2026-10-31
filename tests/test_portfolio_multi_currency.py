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
        """Mixed currencies without explicit exchange_rates mapping must be rejected."""
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

    def test_mixed_currency_with_valid_explicit_exchange_rates(self):
        """Mixed currencies convert deterministically when explicit mappings are supplied."""
        portfolio = PortfolioData(
            user_id="multi_user",
            currency="INR",
            cash_balance=20000.0,
            holdings=[
                Holding(
                    symbol="TCS",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=3500.0,
                    current_price=4000.0,
                    sector="Technology",
                    currency="INR",
                ),
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=150.0,
                    current_price=200.0,
                    sector="Technology",
                    currency="USD",
                ),
            ],
        )
        # 1 USD = 80.0 INR
        exchange_rates = {"USD": 80.0}
        metrics = portfolio_service.calculate_metrics(portfolio, exchange_rates=exchange_rates)

        assert metrics.currency == "INR"
        assert metrics.cash_balance == 20000.0
        # TCS: cost = 35000, value = 40000
        # AAPL: cost = 1500 USD * 80 = 120000 INR, value = 2000 USD * 80 = 160000 INR
        assert metrics.securities_cost_basis == 155000.0  # 35000 + 120000
        assert metrics.securities_market_value == 200000.0  # 40000 + 160000
        assert metrics.total_portfolio_value == 220000.0  # 200000 + 20000 cash
        assert metrics.unrealized_pnl == 45000.0  # 200000 - 155000
        assert metrics.unrealized_pnl_pct == round((45000.0 / 155000.0) * 100, 2)
        assert metrics.top_holding_symbol == "AAPL"  # 160,000 INR > 40,000 INR
        assert metrics.sector_allocation["Technology"] == 100.0

    def test_mixed_currency_usd_base_with_foreign_holdings(self):
        """USD base portfolio with EUR holdings converts properly."""
        portfolio = PortfolioData(
            user_id="usd_eur_user",
            currency="USD",
            cash_balance=1000.0,
            holdings=[
                Holding(
                    symbol="MSFT",
                    asset_type="equity",
                    quantity=5.0,
                    average_buy_price=300.0,
                    current_price=400.0,
                    sector="Technology",
                    currency="USD",
                ),
                Holding(
                    symbol="SAP",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=100.0,
                    current_price=120.0,
                    sector="Technology",
                    currency="EUR",
                ),
            ],
        )
        # 1 EUR = 1.10 USD
        exchange_rates = {"EUR": 1.10}
        metrics = portfolio_service.calculate_metrics(portfolio, exchange_rates=exchange_rates)
        assert metrics.currency == "USD"
        # MSFT: cost 1500, value 2000 USD
        # SAP: cost 1000 EUR * 1.1 = 1100 USD, value 1200 EUR * 1.1 = 1320 USD
        assert metrics.securities_cost_basis == 2600.0  # 1500 + 1100
        assert metrics.securities_market_value == 3320.0  # 2000 + 1320
        assert metrics.total_portfolio_value == 4320.0  # 3320 + 1000

    def test_missing_exchange_rate_raises_value_error(self):
        """Missing rate for a non-base currency in holdings must raise ValueError."""
        portfolio = PortfolioData(
            user_id="missing_rate_user",
            currency="INR",
            cash_balance=5000.0,
            holdings=[
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=5.0,
                    average_buy_price=150.0,
                    current_price=200.0,
                    currency="USD",
                ),
                Holding(
                    symbol="SONY",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=10000.0,
                    current_price=12000.0,
                    currency="JPY",
                ),
            ],
        )
        # Only USD rate supplied, JPY missing
        with pytest.raises(ValueError, match="Missing explicit exchange rate for non-base currency 'JPY'"):
            portfolio_service.calculate_metrics(portfolio, exchange_rates={"USD": 83.5})

    def test_invalid_exchange_rates_raise_value_error(self):
        """Rejects zero, negative, NaN, infinite, and non-numeric exchange rates."""
        portfolio = PortfolioData(
            user_id="invalid_rate_user",
            currency="INR",
            cash_balance=1000.0,
            holdings=[
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=5.0,
                    average_buy_price=150.0,
                    current_price=200.0,
                    currency="USD",
                ),
            ],
        )
        invalid_rates = [0.0, -80.0, float("nan"), float("inf"), "80.0", True]
        for bad_rate in invalid_rates:
            with pytest.raises(ValueError, match="Invalid exchange rate"):
                portfolio_service.calculate_metrics(portfolio, exchange_rates={"USD": bad_rate})  # type: ignore[dict-item]

    def test_base_currency_in_exchange_rates_must_be_one(self):
        """If base currency is specified in exchange_rates, it must be exactly 1.0."""
        portfolio = PortfolioData(
            user_id="base_rate_user",
            currency="INR",
            cash_balance=1000.0,
            holdings=[
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=5.0,
                    average_buy_price=150.0,
                    current_price=200.0,
                    currency="USD",
                ),
            ],
        )
        with pytest.raises(ValueError, match="The exchange rate of base currency to itself must be exactly 1.0"):
            portfolio_service.calculate_metrics(portfolio, exchange_rates={"USD": 83.5, "INR": 1.25})

    def test_mixed_currency_in_simulation_with_exchange_rates(self):
        """What-if simulation works deterministically with explicit exchange rates."""
        portfolio = PortfolioData(
            user_id="sim_multi_user",
            currency="INR",
            cash_balance=10000.0,
            holdings=[
                Holding(
                    symbol="AAPL",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=100.0,
                    current_price=100.0,
                    currency="USD",
                ),
            ],
        )
        # 10 shares @ 100 USD = 1000 USD * 80 = 80,000 INR
        # Cash = 10,000 INR -> Total = 90,000 INR
        exchange_rates = {"USD": 80.0}
        sim = portfolio_service.simulate_what_if(
            portfolio,
            target_symbol="AAPL",
            change_pct=10.0,
            exchange_rates=exchange_rates,
        )
        # +10% shock: price = 110 USD -> 1100 USD * 80 = 88,000 INR
        # Sim total = 88000 + 10000 = 98000 INR. Delta = 8000 INR
        assert sim.original_portfolio_value == 90000.0
        assert sim.simulated_portfolio_value == 98000.0
        assert sim.portfolio_delta_value == 8000.0

    def test_mixed_currency_in_simulation_raises_value_error_without_rates(self):
        """What-if simulation raises ValueError when mixed currency rates are omitted."""
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

