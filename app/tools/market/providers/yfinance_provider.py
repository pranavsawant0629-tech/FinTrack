"""Yahoo Finance Market Data Provider for Indian Equities (NSE / BSE).

Provides live quotes, 1-month daily historical summaries, and company overviews
with deterministic normalization and zero technical indicators.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Literal
import yfinance as yf

from app.tools.market.clock import IST, MarketClock
from app.tools.market.interfaces import (
    BaseMarketDataProvider,
    MarketDataError,
    ProviderUnavailableError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from app.tools.market.models import (
    CompanyOverview,
    HistoricalPrices,
    MarketQuote,
)

logger = logging.getLogger(__name__)

# Common Index mappings
INDEX_MAP: dict[str, tuple[str, str, Literal["NSE", "BSE"]]] = {
    "NIFTY 50": ("^NSEI", "Nifty 50 Index", "NSE"),
    "NIFTY": ("^NSEI", "Nifty 50 Index", "NSE"),
    "^NSEI": ("^NSEI", "Nifty 50 Index", "NSE"),
    "NIFTY BANK": ("^NSEBANK", "Nifty Bank Index", "NSE"),
    "BANKNIFTY": ("^NSEBANK", "Nifty Bank Index", "NSE"),
    "^NSEBANK": ("^NSEBANK", "Nifty Bank Index", "NSE"),
    "SENSEX": ("^BSESN", "BSE Sensex Index", "BSE"),
    "BSE SENSEX": ("^BSESN", "BSE Sensex Index", "BSE"),
    "^BSESN": ("^BSESN", "BSE Sensex Index", "BSE"),
}


def normalize_indian_symbol(symbol: str, exchange: str = "NSE") -> tuple[str, str, Literal["NSE", "BSE"]]:
    """Normalize input ticker symbol to Yahoo Finance ticker and determine exchange.
    
    Returns:
        tuple[yf_ticker, clean_symbol, exchange]
    """
    cleaned = symbol.strip().upper()

    if cleaned in INDEX_MAP:
        yf_sym, name, ex = INDEX_MAP[cleaned]
        return yf_sym, cleaned, ex

    exch_upper = exchange.strip().upper()
    if exch_upper not in ("NSE", "BSE"):
        exch_upper = "NSE"
    valid_exchange: Literal["NSE", "BSE"] = "BSE" if exch_upper == "BSE" else "NSE"

    if cleaned.endswith(".NS"):
        clean_base = cleaned[:-3]
        return cleaned, clean_base, "NSE"
    if cleaned.endswith(".BO"):
        clean_base = cleaned[:-3]
        return cleaned, clean_base, "BSE"

    if valid_exchange == "BSE":
        return f"{cleaned}.BO", cleaned, "BSE"
    return f"{cleaned}.NS", cleaned, "NSE"


class YahooFinanceProvider(BaseMarketDataProvider):
    """Yahoo Finance implementation for Indian Equities and Indices."""

    def __init__(self, clock: MarketClock | None = None) -> None:
        self.clock = clock or MarketClock()

    @property
    def name(self) -> str:
        return "Yahoo Finance"

    @property
    def is_available(self) -> bool:
        return True

    def get_quote(self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE") -> MarketQuote:
        """Fetch live or latest closing quote for an Indian equity or index."""
        yf_ticker, clean_symbol, valid_exchange = normalize_indian_symbol(symbol, exchange)

        try:
            ticker = yf.Ticker(yf_ticker)
            fast_info = ticker.fast_info
            last_price = fast_info.get("last_price") or fast_info.get("lastPrice")
        except Exception as exc:
            err_msg = str(exc)
            if "429" in err_msg or "Too Many Requests" in err_msg:
                raise RateLimitExceededError(f"Yahoo Finance rate limit exceeded: {exc}") from exc
            if (
                "404" in err_msg
                or "Not Found" in err_msg
                or isinstance(exc, KeyError)
                or "currentTradingPeriod" in err_msg
                or "No data found" in err_msg
            ):
                raise SymbolNotFoundError(f"Symbol '{symbol}' not found on {exchange}") from exc
            raise ProviderUnavailableError(f"Failed to communicate with Yahoo Finance: {exc}") from exc

        # If fast_info didn't have a valid price, check 1d history as fallback
        if last_price is None or (isinstance(last_price, float) and (math.isnan(last_price) or last_price <= 0)):
            try:
                hist_1d = ticker.history(period="5d")
                if not hist_1d.empty:
                    last_price = float(hist_1d["Close"].iloc[-1])  # type: ignore[arg-type]
                else:
                    raise SymbolNotFoundError(f"Symbol '{symbol}' not found or has no trading history")
            except SymbolNotFoundError:
                raise
            except Exception as exc:
                raise SymbolNotFoundError(f"Symbol '{symbol}' not found: {exc}") from exc

        prev_close = fast_info.get("previous_close") or fast_info.get("previousClose")
        if prev_close is None or (isinstance(prev_close, float) and math.isnan(prev_close)):
            prev_close = last_price

        change = round(float(last_price) - float(prev_close), 2)
        change_pct = round((change / float(prev_close)) * 100, 2) if prev_close else 0.0

        currency = fast_info.get("currency") or "INR"
        open_price = fast_info.get("open")
        high_price = fast_info.get("day_high") or fast_info.get("dayHigh")
        low_price = fast_info.get("day_low") or fast_info.get("dayLow")
        volume = fast_info.get("last_volume") or fast_info.get("lastVolume")

        # Resolve clean company name
        company_name = ""
        if clean_symbol in INDEX_MAP:
            company_name = INDEX_MAP[clean_symbol][1]
        else:
            try:
                info = ticker.info or {}
                company_name = info.get("shortName") or info.get("longName") or clean_symbol
            except Exception:
                company_name = clean_symbol

        now_ist = datetime.now(IST)
        session_type = self.clock.get_session(now_ist)

        return MarketQuote(
            symbol=clean_symbol,
            company_name=company_name,
            exchange=valid_exchange,
            currency=currency,
            price=round(float(last_price), 2),
            change=change,
            change_percent=change_pct,
            previous_close=round(float(prev_close), 2) if prev_close else None,
            open=round(float(open_price), 2) if open_price and not math.isnan(open_price) else None,
            high=round(float(high_price), 2) if high_price and not math.isnan(high_price) else None,
            low=round(float(low_price), 2) if low_price and not math.isnan(low_price) else None,
            volume=int(volume) if volume and not math.isnan(volume) else None,
            market_status=session_type,
            market_timestamp=now_ist.isoformat(),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            provider=self.name,
            source_url=f"https://finance.yahoo.com/quote/{yf_ticker}",
        )

    def get_historical_summary(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        exchange: Literal["NSE", "BSE"] = "NSE",
    ) -> HistoricalPrices:
        """Fetch 1-month daily historical OHLCV bars and compute deterministic summary metrics.
        
        Explicitly excludes technical indicators (RSI, MACD, etc.).
        """
        yf_ticker, clean_symbol, _ = normalize_indian_symbol(symbol, exchange)

        try:
            ticker = yf.Ticker(yf_ticker)
            # Strictly bound period to 1mo daily bars
            hist = ticker.history(period="1mo", interval="1d")
        except Exception as exc:
            err_msg = str(exc)
            if "429" in err_msg:
                raise RateLimitExceededError(f"Yahoo Finance rate limit exceeded: {exc}") from exc
            raise ProviderUnavailableError(f"Failed to fetch historical data: {exc}") from exc

        if hist.empty:
            raise SymbolNotFoundError(f"No historical price data found for symbol '{symbol}'")

        # Filter out invalid, non-finite, and incomplete price bars
        valid_mask = (
            hist["Close"].notna()
            & hist["High"].notna()
            & hist["Low"].notna()
            & (hist["Close"] > 0)
            & (hist["High"] > 0)
            & (hist["Low"] > 0)
            & (hist["High"] >= hist["Low"])
        )
        hist = hist[valid_mask]

        if hist.empty:
            raise MarketDataError(
                f"No valid historical price bars available for symbol '{symbol}' after filtering incomplete data"
            )

        start_date = str(hist.index[0])[:10]
        end_date = str(hist.index[-1])[:10]
        start_price = round(float(hist["Close"].iloc[0]), 2)  # type: ignore[arg-type]
        end_price = round(float(hist["Close"].iloc[-1]), 2)  # type: ignore[arg-type]
        period_change = round(end_price - start_price, 2)
        period_change_percent = round((period_change / start_price) * 100, 2) if start_price else 0.0
        period_high = round(float(hist["High"].max()), 2)  # type: ignore[arg-type]
        period_low = round(float(hist["Low"].min()), 2)  # type: ignore[arg-type]

        fast_info = ticker.fast_info
        f_52_high = fast_info.get("year_high") or fast_info.get("fiftyTwoWeekHigh")
        f_52_low = fast_info.get("year_low") or fast_info.get("fiftyTwoWeekLow")

        return HistoricalPrices(
            symbol=clean_symbol,
            period="1mo",
            interval="1d",
            start_date=start_date,
            end_date=end_date,
            start_price=start_price,
            end_price=end_price,
            period_change=period_change,
            period_change_percent=period_change_percent,
            period_high=period_high,
            period_low=period_low,
            fifty_two_week_high=round(float(f_52_high), 2) if f_52_high and not math.isnan(f_52_high) else None,
            fifty_two_week_low=round(float(f_52_low), 2) if f_52_low and not math.isnan(f_52_low) else None,
            provider=self.name,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_company_overview(
        self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE"
    ) -> CompanyOverview:
        """Fetch foundational company profile and fundamental valuation metrics."""
        yf_ticker, clean_symbol, valid_exchange = normalize_indian_symbol(symbol, exchange)

        try:
            ticker = yf.Ticker(yf_ticker)
            info: dict[str, Any] = ticker.info or {}
        except Exception as exc:
            err_msg = str(exc)
            if "429" in err_msg:
                raise RateLimitExceededError(f"Yahoo Finance rate limit exceeded: {exc}") from exc
            raise ProviderUnavailableError(f"Failed to fetch company overview: {exc}") from exc

        if not info or ("shortName" not in info and "longName" not in info and "regularMarketPrice" not in info):
            # Check fast info to see if symbol exists at all
            try:
                if not ticker.fast_info.get("last_price"):
                    raise SymbolNotFoundError(f"Symbol '{symbol}' not found on {exchange}")
            except SymbolNotFoundError:
                raise
            except Exception:
                raise SymbolNotFoundError(f"Symbol '{symbol}' not found on {exchange}")

        pe = info.get("trailingPE")
        f_52_high = info.get("fiftyTwoWeekHigh")
        f_52_low = info.get("fiftyTwoWeekLow")

        return CompanyOverview(
            symbol=clean_symbol,
            company_name=info.get("longName") or info.get("shortName") or clean_symbol,
            exchange=valid_exchange,
            currency="INR",
            sector=info.get("sector") or "",
            industry=info.get("industry") or "",
            market_cap=float(info["marketCap"]) if info.get("marketCap") else None,
            pe_ratio=round(float(pe), 2) if pe is not None and not math.isnan(pe) else None,
            fifty_two_week_high=round(float(f_52_high), 2) if f_52_high and not math.isnan(f_52_high) else None,
            fifty_two_week_low=round(float(f_52_low), 2) if f_52_low and not math.isnan(f_52_low) else None,
            summary=info.get("longBusinessSummary") or "",
            provider=self.name,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )
