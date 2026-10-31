"""
Deterministic Response Composer for Finova AI.

Core Guarantee:
"Numerical outputs originate from validated deterministic tools and are not modified
by the response composer."

Combines results from multiple agents and deterministic tools into a unified,
well-structured markdown response while preserving:
1. Exact numerical values (prices, percentages, volumes, calculation splits)
2. Authoritative SEBI citations and provenance
3. Data freshness, market session states, and source provider attribution
4. Regulatory educational disclaimers
"""

from __future__ import annotations

from typing import Any, Literal
from app.agents.derivatives.prompts import EMPIRICAL_SEBI_FO_RISK_DISCLOSURE
from app.rag.service import Citation
from app.router.models import (
    DEFAULT_DISCLAIMER,
    Domain,
    OrchestratorResponse,
    SubTaskExecutionMetadata,
)
from app.tools.market.models import CompanyOverview, HistoricalPrices, MarketDataProvenance, MarketQuote

# Standard non-speculative market dynamics disclaimer for causal inquiries
CAUSAL_MARKET_EXPLAINER = (
    "> **Market Dynamics Note:** Stock prices fluctuate throughout trading sessions based on "
    "continuous order matching between buyers and sellers, market liquidity, broader market index "
    "trends (such as NIFTY 50 and SENSEX), sector-wide movements, and corporate developments. "
    "Finova AI does not speculate on intraday market rumors or unverified external drivers."
)

# Domain-specific regulatory disclosures and notices
CRYPTO_RISK_NOTICE = (
    "Risk Disclosure (Digital Assets): Cryptocurrencies and digital assets are highly volatile, "
    "speculative, and subject to extreme price volatility and regulatory uncertainty. "
    "They are not legal tender in India and lack statutory investor dispute resolution mechanisms."
)

PORTFOLIO_SIMULATION_NOTICE = (
    "Portfolio Analytics Notice: All portfolio metrics, asset allocation breakdowns, and 'what-if' "
    "stress tests are educational simulations based on user-provided holdings and do not constitute "
    "portfolio rebalancing advice or investment directives."
)


class ResponseComposer:
    """Stitches educational text and deterministic tool cards into a unified response."""

    def format_quote_card(self, quote: MarketQuote | MarketDataProvenance) -> str:
        """Deterministically formats an equity quote without altering numerical values."""
        sign = "+" if quote.change > 0 else ""
        lines = [
            f"### 📊 Market Quote: **{quote.company_name or quote.symbol} ({quote.symbol})** on {quote.exchange}",
            f"- **Current / Last Traded Price:** ₹{quote.price:,.2f} ({sign}{quote.change:,.2f}, {sign}{quote.change_percent:.2f}%)",
        ]
        if quote.previous_close is not None:
            lines.append(f"- **Previous Close:** ₹{quote.previous_close:,.2f}")
        if quote.high is not None and quote.low is not None:
            lines.append(f"- **Day Range:** ₹{quote.low:,.2f} - ₹{quote.high:,.2f}")
        if quote.volume is not None:
            lines.append(f"- **Volume:** {quote.volume:,} shares")
        lines.append(f"- **Market Session:** {quote.market_status.replace('_', ' ').title()}")
        lines.append(f"- **Data Freshness:** {quote.freshness_status.replace('_', ' ').title()} (as of {quote.market_timestamp})")
        lines.append(f"- **Provider:** {quote.provider}")
        return "\n".join(lines)

    def format_historical_card(self, hist: HistoricalPrices) -> str:
        """Deterministically formats historical performance without altering numerical values."""
        sign = "+" if hist.period_change > 0 else ""
        lines = [
            f"### 📈 1-Month Performance: **{hist.symbol}** ({hist.start_date} to {hist.end_date})",
            f"- **Starting Price:** ₹{hist.start_price:,.2f}",
            f"- **Ending Price:** ₹{hist.end_price:,.2f}",
            f"- **Net Period Change:** {sign}₹{hist.period_change:,.2f} ({sign}{hist.period_change_percent:.2f}%)",
            f"- **Period Range:** ₹{hist.period_low:,.2f} - ₹{hist.period_high:,.2f}",
        ]
        if hist.fifty_two_week_high and hist.fifty_two_week_low:
            lines.append(f"- **52-Week Range:** ₹{hist.fifty_two_week_low:,.2f} - ₹{hist.fifty_two_week_high:,.2f}")
        lines.append(f"- **Provider:** {hist.provider}")
        return "\n".join(lines)

    def format_overview_card(self, ov: CompanyOverview) -> str:
        """Deterministically formats company fundamentals without altering numerical values."""
        lines = [
            f"### 🏢 Company Profile: **{ov.company_name} ({ov.symbol})**",
        ]
        if ov.sector or ov.industry:
            lines.append(f"- **Sector / Industry:** {ov.sector} | {ov.industry}")
        if ov.market_cap:
            lines.append(f"- **Market Capitalization:** ₹{ov.market_cap:,.0f}")
        if ov.pe_ratio:
            lines.append(f"- **P/E Ratio:** {ov.pe_ratio:.2f}")
        if ov.fifty_two_week_high and ov.fifty_two_week_low:
            lines.append(f"- **52-Week Range:** ₹{ov.fifty_two_week_low:,.2f} - ₹{ov.fifty_two_week_high:,.2f}")
        if ov.summary:
            lines.append(f"\n**Business Summary:**\n{ov.summary}")
        lines.append(f"- **Provider:** {ov.provider}")
        return "\n".join(lines)

    def format_crypto_card(self, crypto_data: dict[str, Any]) -> str:
        """Deterministically formats crypto asset data without altering numerical values."""
        symbol = crypto_data.get("symbol", "").upper()
        name = crypto_data.get("name", symbol)
        price_usd = crypto_data.get("price_usd", 0.0)
        price_inr = crypto_data.get("price_inr")
        change_24h = crypto_data.get("change_24h", 0.0)
        provider = crypto_data.get("provider", "CoinGecko")
        freshness = crypto_data.get("freshness_status", "live")
        timestamp = crypto_data.get("retrieved_at", "")

        sign = "+" if change_24h > 0 else ""
        lines = [
            f"### 🪙 Crypto Quote: **{name} ({symbol})**",
            f"- **Price (USD):** ${price_usd:,.2f} ({sign}{change_24h:.2f}%)",
        ]
        if price_inr is not None:
            lines.append(f"- **Price (INR):** ₹{price_inr:,.2f}")
        lines.append(f"- **Data Freshness:** {freshness.title()} (as of {timestamp})")
        lines.append(f"- **Source Provider:** {provider}")
        return "\n".join(lines)

    def format_finance_calc_card(self, calc_data: dict[str, Any]) -> str:
        """Deterministically formats personal finance calculation outputs."""
        calc_type = calc_data.get("type", "budget")
        lines = [f"### 🧮 Financial Calculation: **{calc_data.get('title', 'Analysis')}**"]

        if calc_type == "budget_50_30_20":
            income = calc_data.get("income", 0.0)
            needs = calc_data.get("needs", 0.0)
            wants = calc_data.get("wants", 0.0)
            savings = calc_data.get("savings", 0.0)
            lines.extend([
                f"- **Monthly Net Income:** ₹{income:,.2f}",
                f"- **Needs (50%):** ₹{needs:,.2f} *(Essentials: housing, groceries, bills)*",
                f"- **Wants (30%):** ₹{wants:,.2f} *(Discretionary: dining, leisure, hobbies)*",
                f"- **Savings & Debt (20%):** ₹{savings:,.2f} *(Emergency fund, investments, loan prepayment)*",
                f"\n*Assumptions & Context: The 50/30/20 guideline is an educational heuristic for post-tax income. Adjustments may be warranted based on fixed living costs, debt obligations, or personal financial goals.*",
            ])
        elif calc_type == "compound_interest":
            p = calc_data.get("principal", 0.0)
            a = calc_data.get("maturity_amount", 0.0)
            gain = calc_data.get("interest_earned", 0.0)
            rate = calc_data.get("annual_rate_percent", 0.0)
            years = calc_data.get("tenure_years", 0)
            lines.extend([
                f"- **Initial Principal:** ₹{p:,.2f}",
                f"- **Annual Interest Rate:** {rate:.2f}%",
                f"- **Tenure:** {years} years",
                f"- **Total Maturity Value:** ₹{a:,.2f}",
                f"- **Total Wealth Generated:** ₹{gain:,.2f}",
                f"\n*Assumptions & Context: Deterministic compound growth projection assuming continuous annual compounding without interim withdrawals. Market investments are subject to volatility and tax implications.*",
            ])
        elif calc_type == "sip_calculation":
            p = calc_data.get("monthly_investment", 0.0)
            rate = calc_data.get("annual_return_percent", 0.0)
            years = calc_data.get("tenure_years", 0)
            invested = calc_data.get("total_invested", 0.0)
            fv = calc_data.get("future_value", 0.0)
            gain = calc_data.get("wealth_gain", 0.0)
            lines.extend([
                f"- **Monthly Investment:** ₹{p:,.2f}",
                f"- **Expected Annual Return:** {rate:.2f}%",
                f"- **Investment Period:** {years} years",
                f"- **Total Amount Invested:** ₹{invested:,.2f}",
                f"- **Estimated Future Value:** ₹{fv:,.2f}",
                f"- **Wealth Gained:** ₹{gain:,.2f}",
                f"\n*Assumptions & Context: SIP calculations assume a constant expected rate of return and periodic compounding. Mutual fund returns are market-linked and not guaranteed; past performance does not indicate future results.*",
            ])
        elif calc_type == "emergency_fund":
            expenses = calc_data.get("monthly_expenses", 0.0)
            target = calc_data.get("target_fund", 0.0)
            current = calc_data.get("current_savings", 0.0)
            gap = calc_data.get("funding_gap", 0.0)
            coverage = calc_data.get("months_covered", 0.0)
            lines.extend([
                f"- **Monthly Expenses:** ₹{expenses:,.2f}",
                f"- **Recommended Target (6 Months):** ₹{target:,.2f}",
                f"- **Current Savings:** ₹{current:,.2f}",
                f"- **Current Coverage:** {coverage:.1f} months",
                f"- **Funding Gap:** ₹{gap:,.2f}",
                f"\n*Assumptions & Context: Based on 6 months of essential living expenses kept in liquid, low-risk instruments (e.g. savings account, liquid funds, sweep FDs) for financial resilience.*",
            ])
        return "\n".join(lines)

    def format_derivatives_card(self, d_data: dict[str, Any]) -> str:
        """Format options / derivatives calculation or payoff card."""
        contract = d_data.get("contract_type", "Option").upper()
        strike = d_data.get("strike_price")
        prem = d_data.get("premium")
        lines = [f"### ⚡ Derivatives Analytics: **{contract}**"]
        if strike is not None:
            lines.append(f"- **Strike Price:** ₹{strike:,.2f}")
        if prem is not None:
            lines.append(f"- **Option Premium:** ₹{prem:,.2f}")
        if "breakeven" in d_data:
            lines.append(f"- **Breakeven Price:** ₹{d_data['breakeven']:,.2f}")
        if "max_profit" in d_data:
            lines.append(f"- **Max Profit:** {d_data['max_profit']}")
        if "max_loss" in d_data:
            lines.append(f"- **Max Loss:** {d_data['max_loss']}")
        return "\n".join(lines)

    def format_portfolio_card(self, p_data: dict[str, Any]) -> str:
        """Format portfolio analytics or what-if card."""
        lines = ["### 💼 Portfolio Analytics & Allocation"]
        metrics = p_data.get("metrics") or p_data
        if "total_portfolio_value" in metrics:
            lines.append(f"- **Total Portfolio Value:** ₹{metrics['total_portfolio_value']:,.2f}")
        if "securities_cost_basis" in metrics:
            lines.append(f"- **Cost Basis:** ₹{metrics['securities_cost_basis']:,.2f}")
        if "cash_balance" in metrics:
            lines.append(f"- **Cash Balance:** ₹{metrics['cash_balance']:,.2f}")
        if "unrealized_pnl" in metrics:
            pnl = metrics['unrealized_pnl']
            sign = "+" if pnl >= 0 else ""
            lines.append(f"- **Unrealized P&L:** {sign}₹{pnl:,.2f} ({sign}{metrics.get('unrealized_pnl_percent', 0.0):.2f}%)")
        return "\n".join(lines)

    def format_news_card(self, articles: list[dict[str, Any]]) -> str:
        """Format retrieved news list."""
        lines = ["### 📰 Retrieved Financial & Regulatory Headlines"]
        for idx, art in enumerate(articles[:3], start=1):
            lines.append(f"{idx}. **{art.get('title', 'News Update')}**")
            freshness_str = f" | Status: {art['freshness']}" if "freshness" in art else ""
            lines.append(f"   *Source: {art.get('source', 'Verified Source')} | Published: {art.get('published_at', '')}{freshness_str}*")
            if art.get("summary"):
                lines.append(f"   {art['summary']}")
        return "\n".join(lines)

    def assemble_disclaimer(
        self,
        base_disclaimer: str = DEFAULT_DISCLAIMER,
        domain_detected: Domain = "EQUITY",
        sub_tasks: list[SubTaskExecutionMetadata] | None = None,
        derivatives_data: dict[str, Any] | None = None,
        crypto_data: dict[str, Any] | None = None,
        portfolio_data: dict[str, Any] | None = None,
    ) -> str:
        """Contextually assemble regulatory disclosures and domain-specific notices without duplicates."""
        parts = [base_disclaimer.strip()] if base_disclaimer and base_disclaimer.strip() else [DEFAULT_DISCLAIMER]

        all_domains = {domain_detected}
        if sub_tasks:
            all_domains.update(t.domain for t in sub_tasks)

        # 1. Derivatives disclosure (empirical SEBI F&O study)
        has_derivatives = "DERIVATIVES" in all_domains or derivatives_data is not None
        if has_derivatives:
            if "89% of individual traders" not in parts[0] and "SEBI research study" not in parts[0]:
                parts.append(EMPIRICAL_SEBI_FO_RISK_DISCLOSURE)

        # 2. Crypto disclosure
        has_crypto = "CRYPTO" in all_domains or crypto_data is not None
        if has_crypto:
            if "Digital Assets" not in parts[0] and "Cryptocurrencies" not in parts[0]:
                parts.append(CRYPTO_RISK_NOTICE)

        # 3. Portfolio simulation notice
        has_portfolio = "PORTFOLIO" in all_domains or portfolio_data is not None
        if has_portfolio:
            if "Portfolio Analytics Notice" not in parts[0] and "educational simulations" not in parts[0]:
                parts.append(PORTFOLIO_SIMULATION_NOTICE)

        return "\n\n".join(parts)

    def compose(
        self,
        query: str,
        educational_text: str | None = None,
        citations: list[Citation] | None = None,
        market_quotes: list[MarketQuote | MarketDataProvenance] | None = None,
        historical_data: HistoricalPrices | None = None,
        overview_data: CompanyOverview | None = None,
        crypto_data: dict[str, Any] | None = None,
        calc_data: dict[str, Any] | None = None,
        derivatives_data: dict[str, Any] | None = None,
        portfolio_data: dict[str, Any] | None = None,
        news_data: list[dict[str, Any]] | None = None,
        quiz_data: dict[str, Any] | None = None,
        onboarding_data: list[dict[str, Any]] | None = None,
        is_causal_query: bool = False,
        domain_detected: Domain = "EQUITY",
        sub_tasks: list[SubTaskExecutionMetadata] | None = None,
        disclaimer: str = DEFAULT_DISCLAIMER,
        model_used: str = "",
        latency_ms: float = 0.0,
        resolved_query: str | None = None,
    ) -> OrchestratorResponse:
        """Compose all available components into a unified OrchestratorResponse."""
        sections: list[str] = []
        grounding_sources: list[str] = []

        # 1. Educational Concept Section (RAG or pedagogical text)
        if educational_text and educational_text.strip():
            sections.append(educational_text.strip())
            if citations and len(citations) > 0:
                grounding_sources.append("sebi_rag")

        # 2. Market Data Section(s)
        primary_quote: MarketDataProvenance | None = None
        market_data_list: list[MarketDataProvenance] = []

        if market_quotes:
            for q in market_quotes:
                sections.append(self.format_quote_card(q))
                prov = q if isinstance(q, MarketDataProvenance) else MarketDataProvenance(
                    symbol=q.symbol,
                    company_name=q.company_name,
                    exchange=q.exchange,
                    currency=q.currency,
                    price=q.price,
                    change=q.change,
                    change_percent=q.change_percent,
                    previous_close=q.previous_close,
                    open=q.open,
                    high=q.high,
                    low=q.low,
                    volume=q.volume,
                    market_status=q.market_status,
                    market_timestamp=q.market_timestamp,
                    retrieved_at=q.retrieved_at,
                    provider=q.provider,
                    source_url=q.source_url,
                    freshness_status=q.freshness_status,
                )
                market_data_list.append(prov)
            primary_quote = market_data_list[0]
            grounding_sources.append("live_market_data")

        if historical_data:
            sections.append(self.format_historical_card(historical_data))
            if "live_market_data" not in grounding_sources:
                grounding_sources.append("live_market_data")

        if overview_data:
            sections.append(self.format_overview_card(overview_data))
            if "live_market_data" not in grounding_sources:
                grounding_sources.append("live_market_data")

        # 3. Crypto Data Section
        if crypto_data:
            sections.append(self.format_crypto_card(crypto_data))
            grounding_sources.append("crypto_data")

        # 4. Personal Finance Calculation Section
        if calc_data:
            sections.append(self.format_finance_calc_card(calc_data))
            grounding_sources.append("calc_tool")

        # 5. Derivatives Section
        if derivatives_data:
            sections.append(self.format_derivatives_card(derivatives_data))
            grounding_sources.append("derivatives_tool")

        # 6. Portfolio Section
        if portfolio_data:
            sections.append(self.format_portfolio_card(portfolio_data))
            grounding_sources.append("portfolio_tool")

        # 7. News Section
        if news_data:
            sections.append(self.format_news_card(news_data))
            grounding_sources.append("news_service")

        # 8. Causal Explainer Note
        if is_causal_query:
            sections.append(CAUSAL_MARKET_EXPLAINER)

        # 9. Explicit Unavailable Information Note for Partial Failures
        failed_tasks = [t for t in (sub_tasks or []) if t.status == "failed"]
        if failed_tasks:
            unavail_notes = []
            for ft in failed_tasks:
                target_desc = f" for '{ft.target}'" if ft.target else ""
                unavail_notes.append(f"- **{ft.domain.title()} ({ft.intent}){target_desc}:** Data or response could not be retrieved at this time.")
            sections.append(
                "> **Unavailable Information Note:**\n"
                + "\n".join(unavail_notes)
            )

        # 10. Assemble complete answer
        combined_answer = "\n\n---\n\n".join(sections) if len(sections) > 1 else (sections[0] if sections else "")

        # Grounding status resolution (Truthful hybrid grounding tracking)
        has_ungrounded_edu = False
        if educational_text and educational_text.strip():
            if not citations or len(citations) == 0:
                has_ungrounded_edu = True
            elif sub_tasks:
                if any(
                    t.domain in ("CRYPTO", "PERSONAL_FINANCE", "GENERAL")
                    and t.intent in ("educational_concept", "unknown")
                    for t in sub_tasks
                ):
                    has_ungrounded_edu = True

        has_grounded = len(grounding_sources) > 0
        has_failed_subtasks = bool(failed_tasks)

        grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
        if has_grounded and (has_ungrounded_edu or has_failed_subtasks):
            grounding_status = "partially_grounded"
        elif has_grounded:
            grounding_status = "fully_grounded"
        else:
            grounding_status = "ungrounded"

        assembled_disclaimer = self.assemble_disclaimer(
            base_disclaimer=disclaimer,
            domain_detected=domain_detected,
            sub_tasks=sub_tasks,
            derivatives_data=derivatives_data,
            crypto_data=crypto_data,
            portfolio_data=portfolio_data,
        )

        return OrchestratorResponse(
            query=query,
            resolved_query=resolved_query,
            answer=combined_answer,
            grounding_status=grounding_status,
            citations=citations or [],
            market_data=primary_quote,
            market_data_list=market_data_list,
            crypto_data=crypto_data,
            derivatives_data=derivatives_data,
            portfolio_data=portfolio_data,
            news_data=news_data,
            quiz_data=quiz_data,
            onboarding_data=onboarding_data,
            grounding_sources=grounding_sources,
            domain_detected=domain_detected,
            sub_tasks=sub_tasks or [],
            agent_name="Finova Orchestrator",
            disclaimer=assembled_disclaimer,
            model_used=model_used,
            latency_ms=latency_ms,
        )


response_composer = ResponseComposer()
