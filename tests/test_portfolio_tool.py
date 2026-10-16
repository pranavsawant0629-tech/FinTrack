"""
Unit tests for the deterministic portfolio calculation tools and accounting metrics.
Verifies cost basis vs. market value separation, cash liquidity accounting,
allocation percentages, concentration risk, and what-if stress tests.
"""

import pytest
from app.tools.portfolio.models import Holding, PortfolioData, PortfolioMetrics
from app.tools.portfolio.providers.mock import MockPortfolioProvider, create_demo_portfolio
from app.tools.portfolio.service import PortfolioService


class TestPortfolioAccounting:
    """Test mathematical accuracy of portfolio accounting metrics."""

    @pytest.fixture
    def sample_portfolio(self):
        return PortfolioData(
            user_id="test_user",
            cash_balance=20000.0,
            holdings=[
                Holding(
                    symbol="TCS",
                    asset_type="equity",
                    quantity=10.0,
                    average_buy_price=3500.0,
                    current_price=4000.0,
                    sector="Technology",
                ),
                Holding(
                    symbol="RELIANCE",
                    asset_type="equity",
                    quantity=20.0,
                    average_buy_price=2500.0,
                    current_price=2700.0,
                    sector="Energy",
                ),
            ],
        )

    def test_cost_basis_distinguished_from_cash(self, sample_portfolio):
        service = PortfolioService()
        metrics: PortfolioMetrics = service.calculate_metrics(sample_portfolio)

        # TCS cost: 10 * 3500 = 35,000; RELIANCE cost: 20 * 2500 = 50,000
        # Total securities cost basis = 85,000 (MUST NOT INCLUDE CASH)
        assert metrics.securities_cost_basis == 85000.0
        assert metrics.cash_balance == 20000.0

        # TCS value: 10 * 4000 = 40,000; RELIANCE value: 20 * 2700 = 54,000
        # Total securities market value = 94,000
        assert metrics.securities_market_value == 94000.0

        # Total portfolio value = 94,000 + 20,000 = 114,000
        assert metrics.total_portfolio_value == 114000.0

    def test_unrealized_pnl_math(self, sample_portfolio):
        service = PortfolioService()
        metrics: PortfolioMetrics = service.calculate_metrics(sample_portfolio)

        # Gain = 94,000 - 85,000 = 9,000
        assert metrics.unrealized_pnl == 9000.0
        # Gain % = (9,000 / 85,000) * 100 = 10.59%
        assert metrics.unrealized_pnl_pct == round((9000.0 / 85000.0) * 100, 2)

    def test_asset_allocation_sums_to_100(self, sample_portfolio):
        service = PortfolioService()
        metrics: PortfolioMetrics = service.calculate_metrics(sample_portfolio)

        total_val = metrics.total_portfolio_value  # 114,000
        # Cash: 20,000 / 114,000 * 100 = 17.54%
        assert "cash" in metrics.asset_allocation
        assert metrics.asset_allocation["cash"] == round((20000.0 / total_val) * 100, 2)

        # Equities: 94,000 / 114,000 * 100 = 82.46%
        assert "equity" in metrics.asset_allocation
        assert metrics.asset_allocation["equity"] == round((94000.0 / total_val) * 100, 2)

        total_pct = sum(metrics.asset_allocation.values())
        assert abs(total_pct - 100.0) < 0.1

    def test_sector_allocation(self, sample_portfolio):
        service = PortfolioService()
        metrics: PortfolioMetrics = service.calculate_metrics(sample_portfolio)

        # Total securities = 94,000
        # Tech: 40,000 / 94,000 * 100 = 42.55%
        # Energy: 54,000 / 94,000 * 100 = 57.45%
        assert metrics.sector_allocation["Technology"] == round((40000.0 / 94000.0) * 100, 2)
        assert metrics.sector_allocation["Energy"] == round((54000.0 / 94000.0) * 100, 2)

    def test_concentration_and_diversification(self, sample_portfolio):
        service = PortfolioService()
        metrics: PortfolioMetrics = service.calculate_metrics(sample_portfolio)

        # Top holding is RELIANCE (54,000 / 114,000 = 47.37%)
        assert metrics.top_holding_symbol == "RELIANCE"
        assert metrics.top_holding_concentration_pct == round((54000.0 / 114000.0) * 100, 2)
        assert "High Concentration Risk" in metrics.diversification_assessment

    def test_empty_portfolio_accounting(self):
        service = PortfolioService()
        empty = PortfolioData(user_id="empty_user", cash_balance=10000.0, holdings=[])
        metrics = service.calculate_metrics(empty)

        assert metrics.securities_cost_basis == 0.0
        assert metrics.securities_market_value == 0.0
        assert metrics.cash_balance == 10000.0
        assert metrics.total_portfolio_value == 10000.0
        assert metrics.unrealized_pnl == 0.0
        assert metrics.unrealized_pnl_pct == 0.0
        assert metrics.asset_allocation == {"cash": 100.0}


class TestWhatIfSimulations:
    """Test deterministic price shock what-if simulations."""

    @pytest.fixture
    def portfolio(self):
        return PortfolioData(
            user_id="test_sim",
            cash_balance=10000.0,
            holdings=[
                Holding(symbol="TCS", quantity=10.0, average_buy_price=3000.0, current_price=4000.0),
                Holding(symbol="INFY", quantity=20.0, average_buy_price=1500.0, current_price=1800.0),
            ],
        )

    def test_single_holding_shock(self, portfolio):
        service = PortfolioService()
        # Original: TCS = 40k, INFY = 36k, Cash = 10k => Total = 86k
        # Simulate TCS +10% => TCS becomes 44k (+4k) => Total = 90k
        res = service.simulate_what_if(portfolio, target_symbol="TCS", change_pct=10.0)

        assert res.original_portfolio_value == 86000.0
        assert res.simulated_portfolio_value == 90000.0
        assert res.portfolio_delta_value == 4000.0
        assert res.portfolio_delta_pct == round((4000.0 / 86000.0) * 100, 2)
        assert len(res.impacted_holdings) == 1
        assert res.impacted_holdings[0].symbol == "TCS"
        assert res.impacted_holdings[0].simulated_price == 4400.0

    def test_broad_market_shock(self, portfolio):
        service = PortfolioService()
        # Simulate broad market -5%
        # TCS drops 5% (40k -> 38k, delta -2k)
        # INFY drops 5% (36k -> 34.2k, delta -1.8k)
        # Cash unchanged (10k)
        # Total: 86k -> 82.2k (delta -3.8k)
        res = service.simulate_what_if(portfolio, target_symbol=None, change_pct=-5.0, broad_market=True)

        assert res.original_portfolio_value == 86000.0
        assert res.simulated_portfolio_value == 82200.0
        assert res.portfolio_delta_value == -3800.0
        assert len(res.impacted_holdings) == 2


class TestProviderIsolation:
    """Test that mock provider isolates portfolios by user_id."""

    def test_user_isolation(self):
        provider = MockPortfolioProvider(seed_demo=False)
        p1 = PortfolioData(user_id="user_A", cash_balance=5000.0, holdings=[])
        p2 = PortfolioData(user_id="user_B", cash_balance=15000.0, holdings=[])

        provider.save_portfolio(p1)
        provider.save_portfolio(p2)

        res_a = provider.get_portfolio("user_A")
        res_b = provider.get_portfolio("user_B")

        assert res_a is not None and res_a.cash_balance == 5000.0
        assert res_b is not None and res_b.cash_balance == 15000.0
        assert provider.get_portfolio("unknown_user") is None
