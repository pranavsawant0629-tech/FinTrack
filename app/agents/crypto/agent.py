"""
Crypto Tutor Agent for Finova AI (Prof. Crypton).

Coordinates:
1. Deterministic safety evaluation (blocks coin shilling, 10x calls, price predictions)
2. Replaceable live crypto price fetching via BaseCryptoProvider / CryptoDataService
3. Grounded pedagogical explanations of blockchain and decentralized finance concepts
4. Response assembly with standardized crypto provenance
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.agents.crypto.prompts import CRYPTO_DISCLAIMER, CRYPTO_TUTOR_SYSTEM_PROMPT
from app.agents.crypto.safety import CryptoSafetyGuardrail, crypto_safety_guardrail
from app.llm.llm_client import LLMClient, llm_client
from app.safety.validator import GLOBAL_REFUSAL_MESSAGE, secondary_safety_validator
from app.tools.crypto.interfaces import CryptoAssetNotFoundError, CryptoProviderError
from app.tools.crypto.models import CryptoProvenance
from app.tools.crypto.service import CryptoDataService, crypto_data_service

logger = logging.getLogger(__name__)


class CryptoAgentResult(BaseModel):
    """Response contract for the Crypto Tutor Agent."""
    query: str
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    crypto_data: dict[str, Any] | None = None
    grounding_sources: list[Literal["sebi_rag", "live_market_data", "crypto_data", "calc_tool"]] = Field(
        default_factory=list
    )
    agent_name: str = "Crypto Tutor (Prof. Crypton)"
    disclaimer: str = CRYPTO_DISCLAIMER
    model_used: str = ""
    latency_ms: float = 0.0


class CryptoAgent:
    """Specialized tutor agent for cryptocurrency and blockchain education."""

    def __init__(
        self,
        safety: CryptoSafetyGuardrail | None = None,
        crypto_service: CryptoDataService | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.safety = safety or crypto_safety_guardrail
        self.crypto_service = crypto_service or crypto_data_service
        self.llm = llm or llm_client

    def _extract_crypto_symbol(self, query: str) -> str | None:
        """Extract canonical crypto symbol from query text."""
        from app.router.classifier import CRYPTO_ALIASES
        upper = query.upper()
        for alias, canonical in sorted(CRYPTO_ALIASES.items(), key=lambda x: -len(x[0])):
            import re
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                return canonical
        return None

    def ask(
        self,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
        personalization: Any | None = None,
    ) -> CryptoAgentResult:
        """Execute the Crypto Tutor pipeline."""
        t0 = time.perf_counter()

        # Step 0: Universal Secondary Safety & Input Sanitization
        try:
            sec_safety = secondary_safety_validator.validate(query)
            if not sec_safety.is_safe:
                latency = round((time.perf_counter() - t0) * 1000, 2)
                return CryptoAgentResult(
                    query=query,
                    answer=sec_safety.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                    grounding_status="ungrounded",
                    crypto_data=None,
                    grounding_sources=[],
                    agent_name="Crypto Tutor (Prof. Crypton)",
                    disclaimer=CRYPTO_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )
            # Enforce sanitized input across all downstream processing
            query = sec_safety.sanitized_text
        except Exception as exc:
            logger.critical("Universal safety validation failed in CryptoAgent: %s", exc, exc_info=True)
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return CryptoAgentResult(
                query=query,
                answer=GLOBAL_REFUSAL_MESSAGE,
                grounding_status="ungrounded",
                crypto_data=None,
                grounding_sources=[],
                agent_name="Crypto Tutor (Prof. Crypton)",
                disclaimer=CRYPTO_DISCLAIMER,
                model_used="deterministic_guardrail",
                latency_ms=latency,
            )

        # Step 1: Safety Check
        safety_res = self.safety.evaluate(query)
        if not safety_res.is_safe:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return CryptoAgentResult(
                query=query,
                answer=safety_res.refusal_message or "",
                grounding_status="ungrounded",
                crypto_data=None,
                grounding_sources=[],
                agent_name="Crypto Tutor (Prof. Crypton)",
                disclaimer=CRYPTO_DISCLAIMER,
                model_used="deterministic_guardrail",
                latency_ms=latency,
            )

        symbol = self._extract_crypto_symbol(query)
        is_price_query = any(w in query.lower() for w in ["price", "quote", "trading at", "how much is", "worth", "value", "cost"])

        # Step 2: Live Crypto Quote Routing
        if symbol and (is_price_query or query.strip().upper() == symbol):
            try:
                quote = self.crypto_service.get_quote(symbol)
                prov = self.crypto_service.create_provenance(quote)
                sign = "+" if quote.change_24h > 0 else ""
                quote_text = (
                    f"### 🪙 **{quote.name} ({quote.symbol})** Market Data:\n\n"
                    f"- **Current Price (USD):** ${quote.price_usd:,.2f} ({sign}{quote.change_24h:.2f}%)\n"
                )
                if quote.price_inr:
                    quote_text += f"- **Current Price (INR):** ₹{quote.price_inr:,.2f}\n"
                quote_text += (
                    f"- **Data Freshness:** {quote.freshness_status.title()} (as of {quote.market_timestamp})\n"
                    f"- **Source Provider:** {quote.provider}\n\n"
                    f"*Note: Digital asset prices are highly volatile and change continuously.*"
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                return CryptoAgentResult(
                    query=query,
                    answer=quote_text,
                    grounding_status="fully_grounded",
                    crypto_data=prov.model_dump(),
                    grounding_sources=["crypto_data"],
                    agent_name="Crypto Tutor (Prof. Crypton)",
                    disclaimer=CRYPTO_DISCLAIMER,
                    model_used="deterministic_tools",
                    latency_ms=latency,
                )
            except CryptoAssetNotFoundError:
                latency = round((time.perf_counter() - t0) * 1000, 2)
                return CryptoAgentResult(
                    query=query,
                    answer=(
                        f"### 🪙 Market Data Notice: **{symbol}**\n\n"
                        f"Cryptocurrency asset **{symbol}** could not be found or is not supported for real-time tracking.\n"
                        f"Finova AI does not estimate or simulate live cryptocurrency prices."
                    ),
                    grounding_status="ungrounded",
                    crypto_data=None,
                    grounding_sources=[],
                    agent_name="Crypto Tutor (Prof. Crypton)",
                    disclaimer=CRYPTO_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )
            except CryptoProviderError as exc:
                logger.warning("Crypto provider error for %s: %s", symbol, exc)
                latency = round((time.perf_counter() - t0) * 1000, 2)
                return CryptoAgentResult(
                    query=query,
                    answer=(
                        f"### 🪙 Market Data Notice: **{symbol}**\n\n"
                        f"Real-time market data for **{symbol}** is temporarily unavailable due to upstream provider connectivity or rate-limiting.\n"
                        f"Finova AI does not estimate or simulate live cryptocurrency prices. Please try again shortly."
                    ),
                    grounding_status="ungrounded",
                    crypto_data=None,
                    grounding_sources=[],
                    agent_name="Crypto Tutor (Prof. Crypton)",
                    disclaimer=CRYPTO_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )
            except Exception as exc:
                logger.warning("Failed to retrieve crypto quote for %s: %s", symbol, exc)
                latency = round((time.perf_counter() - t0) * 1000, 2)
                return CryptoAgentResult(
                    query=query,
                    answer=(
                        f"### 🪙 Market Data Notice: **{symbol}**\n\n"
                        f"Real-time market data for **{symbol}** is temporarily unavailable due to an unexpected error.\n"
                        f"Finova AI does not estimate or simulate live cryptocurrency prices. Please try again shortly."
                    ),
                    grounding_status="ungrounded",
                    crypto_data=None,
                    grounding_sources=[],
                    agent_name="Crypto Tutor (Prof. Crypton)",
                    disclaimer=CRYPTO_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )

        # Step 3: Pedagogical Concept Generation (Prof. Crypton)
        model_name = str(getattr(self.llm, "model", "qwen2.5:7b-instruct"))
        sys_prompt = CRYPTO_TUTOR_SYSTEM_PROMPT
        if personalization:
            from app.memory.models import build_personalization_instruction
            inst = build_personalization_instruction(personalization)
            if inst:
                sys_prompt = CRYPTO_TUTOR_SYSTEM_PROMPT + inst

        try:
            explanation = self.llm.chat(
                message=query,
                system=sys_prompt,
                temperature=0.1,
            )
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return CryptoAgentResult(
                query=query,
                answer=explanation.strip(),
                grounding_status="ungrounded",
                crypto_data=None,
                grounding_sources=[],
                agent_name="Crypto Tutor (Prof. Crypton)",
                disclaimer=CRYPTO_DISCLAIMER,
                model_used=model_name,
                latency_ms=latency,
            )
        except Exception as exc:
            logger.error("LLM inference error in CryptoAgent: %s", exc)
            fallback_text = (
                "Cryptocurrency and blockchain systems operate as decentralized, peer-to-peer digital ledgers "
                "secured by cryptography. They carry significant market volatility and regulatory considerations."
            )
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return CryptoAgentResult(
                query=query,
                answer=fallback_text,
                grounding_status="ungrounded",
                crypto_data=None,
                grounding_sources=[],
                agent_name="Crypto Tutor (Prof. Crypton)",
                disclaimer=CRYPTO_DISCLAIMER,
                model_used="fallback",
                latency_ms=latency,
            )


crypto_agent = CryptoAgent()
