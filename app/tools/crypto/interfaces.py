"""
Abstract base provider interface and exceptions for Cryptocurrency Data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from app.tools.crypto.models import CryptoQuote


class CryptoProviderError(Exception):
    """Base exception for all cryptocurrency data provider errors."""
    pass


class CryptoAssetNotFoundError(CryptoProviderError):
    """Raised when a requested cryptocurrency symbol cannot be resolved."""
    pass


class BaseCryptoProvider(ABC):
    """Abstract interface for all cryptocurrency data providers.
    
    The Crypto Agent and Crypto Data Service interact strictly through this interface,
    ensuring providers can be swapped or failed-over without modifying agent logic.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True if provider is operational and reachable."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> CryptoQuote:
        """Fetch standardized crypto quote for the given canonical symbol (e.g. 'BTC')."""
        pass
