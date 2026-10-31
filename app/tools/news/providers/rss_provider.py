"""
Public RSS news provider for Indian regulatory and macro updates (SEBI & RBI).
Uses standard library xml.etree.ElementTree and httpx.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import httpx

from app.tools.news.interfaces import BaseNewsProvider
from app.tools.news.models import NewsArticle, NewsFreshness, NewsSourceType

logger = logging.getLogger(__name__)


def normalize_rss_pub_date(raw_date: str | None) -> str:
    """Normalize RSS publication date string (RFC 2822 or ISO-8601) to ISO-8601 UTC.

    If unparseable or absent, returns empty string "" (unknown).
    Never replaces an unknown publication date with the current time.
    """
    if not raw_date or not raw_date.strip():
        return ""
    text = raw_date.strip()
    # 1. Try RFC 2822 (standard for RSS 2.0 pubDate)
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass

    # 2. Try ISO-8601
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass

    return ""


def matches_ticker_symbol(symbol: str, text: str) -> bool:
    """Symbol-aware matching with appropriate word boundaries.

    Escapes special characters in symbol and prevents false positive
    matches on short symbols (e.g., 'IT', 'BEL', 'ON') inside longer words.
    """
    if not symbol or not text:
        return False

    clean_sym = symbol.strip().upper()
    for suffix in (".NS", ".BO"):
        if clean_sym.endswith(suffix):
            clean_sym = clean_sym[:-len(suffix)]
    if clean_sym.startswith("^"):
        clean_sym = clean_sym[1:]
    clean_sym = clean_sym.strip()
    if not clean_sym:
        return False

    escaped = re.escape(clean_sym)
    # Ensure boundary: cannot be preceded or followed by alphanumeric characters
    pattern = rf"(?:^|(?<=[^A-Za-z0-9])){escaped}(?=$|[^A-Za-z0-9])"
    return bool(re.search(pattern, text, re.IGNORECASE))



class PublicRSSNewsProvider(BaseNewsProvider):
    """Fetches official regulatory announcements from SEBI and RBI RSS feeds."""

    FEEDS = {
        "SEBI": {
            "url": "https://www.sebi.gov.in/sebirss.xml",
            "source_type": NewsSourceType.REGULATORY,
        },
        "RBI": {
            "url": "https://rbi.org.in/pressreleases_rss.xml",
            "source_type": NewsSourceType.MACRO,
        },
    }

    def __init__(self, timeout: float = 5.0) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "public_rss"

    def fetch_ticker_news(self, symbol: str, limit: int = 5) -> list[NewsArticle]:
        """RSS feeds are macro/regulatory, but we can filter by symbol/keyword."""
        all_news = self.fetch_macro_news(limit=limit * 3)
        matched = [
            a for a in all_news
            if matches_ticker_symbol(symbol, a.title) or matches_ticker_symbol(symbol, a.summary)
        ]
        return matched[:limit]

    def fetch_macro_news(self, limit: int = 5) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for source_name, cfg in self.FEEDS.items():
            feed_url = cfg["url"]
            source_type = cfg["source_type"]
            try:
                with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                    resp = client.get(feed_url)
                    if resp.status_code == 200:
                        parsed = self._parse_rss_xml(resp.content, source_name=source_name, source_type=source_type)
                        articles.extend(parsed)
            except Exception as exc:
                logger.warning("Failed to fetch RSS from %s (%s): %s", source_name, feed_url, exc)
                continue

        # Sort newest first if dates are parseable or keep order
        return articles[:limit]

    def is_healthy(self) -> bool:
        try:
            with httpx.Client(timeout=3.0, follow_redirects=True) as client:
                resp = client.get(self.FEEDS["SEBI"]["url"])
                return resp.status_code == 200
        except Exception:
            return False

    def _parse_rss_xml(self, xml_bytes: bytes, source_name: str, source_type: NewsSourceType) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        try:
            root = ET.fromstring(xml_bytes)
            # Find channel items (standard RSS 2.0)
            items = root.findall(".//item")
            for idx, item in enumerate(items):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_date_elem = item.find("pubDate")

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Regulatory Circular"
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else title
                pub_date_raw = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else None
                pub_date = normalize_rss_pub_date(pub_date_raw)

                # Clean simple HTML tags from description if present
                clean_desc = desc.replace("<p>", "").replace("</p>", "").replace("<br>", " ").replace("<b>", "").replace("</b>", "")

                articles.append(
                    NewsArticle(
                        id=f"{source_name.lower()}_{idx}_{abs(hash(title)) % 100000}",
                        title=title,
                        summary=clean_desc,
                        url=link,
                        source=source_name,
                        source_type=source_type,
                        published_at=pub_date,
                        symbol=None,
                        freshness=NewsFreshness.REALTIME,
                    )
                )
        except Exception as e:
            logger.debug("Failed to parse RSS XML from %s: %s", source_name, e)
        return articles
