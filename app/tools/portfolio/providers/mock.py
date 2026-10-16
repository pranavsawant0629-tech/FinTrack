"""
Mock / In-memory portfolio provider for testing and development.
Provides deterministic simulated portfolios without external database requirements.
"""

from __future__ import annotations

from app.tools.portfolio.interfaces import BasePortfolioProvider
from app.tools.portfolio.models import Holding, PortfolioData


def create_demo_portfolio(user_id: str = "demo_user") -> PortfolioData:
    """Create a balanced Indian educational demo portfolio."""
    return PortfolioData(
        user_id=user_id,
        cash_balance=25000.0,
        holdings=[
            Holding(
                symbol="TCS",
                asset_type="equity",
                quantity=10.0,
                average_buy_price=3800.0,
                current_price=4100.0,
                sector="Technology",
            ),
            Holding(
                symbol="RELIANCE",
                asset_type="equity",
                quantity=15.0,
                average_buy_price=2800.0,
                current_price=2950.0,
                sector="Energy",
            ),
            Holding(
                symbol="HDFCBANK",
                asset_type="equity",
                quantity=25.0,
                average_buy_price=1600.0,
                current_price=1650.0,
                sector="Banking",
            ),
            Holding(
                symbol="NIFTYBEES",
                asset_type="etf",
                quantity=100.0,
                average_buy_price=250.0,
                current_price=265.0,
                sector="Index ETF",
            ),
        ],
        updated_at="2026-09-11T12:00:00Z",
    )


class MockPortfolioProvider(BasePortfolioProvider):
    """In-memory thread-isolated mock provider for simulated portfolios."""

    def __init__(self, seed_demo: bool = True) -> None:
        self._storage: dict[str, PortfolioData] = {}
        if seed_demo:
            demo = create_demo_portfolio("demo_user")
            self._storage["demo_user"] = demo

    def get_portfolio(self, user_id: str) -> PortfolioData | None:
        return self._storage.get(user_id)

    def save_portfolio(self, portfolio: PortfolioData) -> bool:
        self._storage[portfolio.user_id] = portfolio
        return True

    def clear(self) -> None:
        self._storage.clear()
