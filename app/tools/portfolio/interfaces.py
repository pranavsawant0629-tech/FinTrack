"""
Replaceable provider abstraction for user portfolio data.
Decouples Portfolio Tutor from live brokerage databases and TradeWise infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from app.tools.portfolio.models import PortfolioData


class BasePortfolioProvider(ABC):
    """Abstract interface for storing and retrieving user portfolio holdings."""

    @abstractmethod
    def get_portfolio(self, user_id: str) -> PortfolioData | None:
        """
        Retrieve portfolio data for a specific user ID.
        Returns None if no portfolio exists for the user.
        """
        ...

    @abstractmethod
    def save_portfolio(self, portfolio: PortfolioData) -> bool:
        """
        Persist simulated portfolio data for a specific user.
        Returns True on success, False on failure.
        """
        ...
