"""
Unit tests for Cryptocurrency Tools and Provider Layer (app.tools.crypto).
"""

import pytest
from app.tools.crypto.interfaces import BaseCryptoProvider, CryptoAssetNotFoundError
from app.tools.crypto.models import CryptoQuote
from app.tools.crypto.providers.coingecko_provider import CoinGeckoProvider
from app.tools.crypto.service import CryptoDataService


@pytest.fixture
def provider():
    return CoinGeckoProvider(allow_offline_fallback=True)


@pytest.fixture
def crypto_service(provider):
    return CryptoDataService(provider=provider, cache_ttl=10.0)


def test_coingecko_provider_btc_quote(provider: BaseCryptoProvider):
    quote = provider.get_quote("BTC")
    assert isinstance(quote, CryptoQuote)
    assert quote.symbol == "BTC"
    assert quote.name == "Bitcoin"
    assert quote.price_usd > 0.0
    assert quote.provider in ("CoinGecko", "CoinGecko-Sandbox")
    assert quote.freshness_status in ("realtime", "cached_fallback")


def test_coingecko_provider_eth_quote(provider: BaseCryptoProvider):
    quote = provider.get_quote("ETH")
    assert quote.symbol == "ETH"
    assert quote.name == "Ethereum"
    assert quote.price_usd > 0.0


def test_coingecko_provider_unsupported_symbol(provider: BaseCryptoProvider):
    with pytest.raises(CryptoAssetNotFoundError):
        provider.get_quote("NON_EXISTENT_COIN_XYZ_123")


def test_crypto_service_caching(crypto_service: CryptoDataService):
    q1 = crypto_service.get_quote("BTC")
    q2 = crypto_service.get_quote("BTC")
    # Same instance from cache
    assert q1.market_timestamp == q2.market_timestamp
    assert q1.price_usd == q2.price_usd


def test_crypto_provenance_creation(crypto_service: CryptoDataService):
    quote = crypto_service.get_quote("SOL")
    prov = crypto_service.create_provenance(quote)
    assert prov.symbol == "SOL"
    assert prov.price_usd > 0.0
    assert prov.provider in ("CoinGecko", "CoinGecko-Sandbox")


def test_coingecko_provider_default_offline_disabled():
    from unittest.mock import patch
    from app.tools.crypto.interfaces import CryptoProviderError

    prod_provider = CoinGeckoProvider()  # Default allow_offline_fallback is False
    assert prod_provider._allow_offline_fallback is False

    with patch("httpx.Client.get", side_effect=Exception("Simulated network outage")):
        with pytest.raises(CryptoProviderError) as exc_info:
            prod_provider.get_quote("BTC")
        assert "unavailable or rate-limited" in str(exc_info.value)


def test_coingecko_provider_fallback_timestamp_is_static():
    from unittest.mock import patch

    test_provider = CoinGeckoProvider(allow_offline_fallback=True)
    with patch("httpx.Client.get", side_effect=Exception("Simulated network outage")):
        quote = test_provider.get_quote("BTC")
        assert quote.market_timestamp == "2024-01-01T00:00:00Z"
        assert quote.retrieved_at == "2024-01-01T00:00:00Z"
        assert quote.freshness_status == "cached_fallback"
        assert quote.provider == "CoinGecko-Sandbox"

