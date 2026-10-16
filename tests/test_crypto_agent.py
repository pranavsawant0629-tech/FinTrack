"""
Unit tests for the Crypto Tutor Agent (app.agents.crypto.agent).
Verifies safety blocking, deterministic price quoting, and educational explanations.
"""

from unittest.mock import MagicMock
import pytest

from app.agents.crypto.agent import CryptoAgent, crypto_agent
from app.agents.crypto.prompts import CRYPTO_DISCLAIMER
from app.router.safety import GLOBAL_REFUSAL_MESSAGE
from app.tools.crypto.models import CryptoQuote


def test_crypto_agent_blocks_advisory_inquiry():
    res = crypto_agent.ask("Which coin will 10x this year?")
    assert res.grounding_status == "ungrounded"
    assert res.answer == GLOBAL_REFUSAL_MESSAGE
    assert res.crypto_data is None


def test_crypto_agent_live_price_quote():
    from app.tools.crypto.providers.coingecko_provider import CoinGeckoProvider
    from app.tools.crypto.service import CryptoDataService

    test_provider = CoinGeckoProvider(allow_offline_fallback=True)
    test_service = CryptoDataService(provider=test_provider)
    agent = CryptoAgent(crypto_service=test_service)
    res = agent.ask("What is the current price of Bitcoin?")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["crypto_data"]
    assert res.crypto_data is not None
    assert res.crypto_data["symbol"] == "BTC"
    assert res.crypto_data["price_usd"] > 0
    assert "$" in res.answer


def test_crypto_agent_educational_concept():
    mock_llm = MagicMock()
    mock_llm.model = "qwen2.5:7b-instruct"
    mock_llm.chat.return_value = "Blockchain is a distributed, immutable ledger that records transactions across a network."

    agent = CryptoAgent(llm=mock_llm)
    res = agent.ask("What is blockchain?")
    assert res.grounding_status == "ungrounded"
    assert "distributed, immutable ledger" in res.answer
    assert res.crypto_data is None
    assert mock_llm.chat.call_count == 1


def test_crypto_agent_simulated_outage_never_exposes_fallback():
    from app.tools.crypto.interfaces import CryptoProviderError
    from unittest.mock import patch

    mock_crypto_service = MagicMock()
    mock_crypto_service.get_quote.side_effect = CryptoProviderError("CoinGecko service unavailable or rate-limited")

    agent = CryptoAgent(crypto_service=mock_crypto_service)
    res = agent.ask("What is the current price of Bitcoin?")

    assert res.grounding_status == "ungrounded"
    assert res.crypto_data is None
    assert "temporarily unavailable" in res.answer
    assert "does not estimate or simulate" in res.answer
    assert "$64,250" not in res.answer

