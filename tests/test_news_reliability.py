"""
Deterministic unit tests for News Reliability in FinTrack.
Tests:
- Conservative URL canonicalization (stripping tracking query params only)
- Headline normalization and cross-provider deduplication
- Mixed timestamp parsing (RFC 2822, ISO-8601, and unparseable dates)
- Chronological ordering (dated articles newest-first, undated articles last)
- Symbol-aware word boundary matching in RSS feeds (no false positives for short symbols like IT, BEL, ON)
- Strict truthfulness on network outage and stale cache semantics
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from app.tools.news.models import NewsArticle, NewsFreshness, NewsSourceType
from app.tools.news.providers.mock import MockNewsProvider
from app.tools.news.providers.rss_provider import (
    PublicRSSNewsProvider,
    matches_ticker_symbol,
    normalize_rss_pub_date,
)
from app.tools.news.service import (
    NewsService,
    canonicalize_url,
    deduplicate_articles,
    deduplicate_and_sort_articles,
    normalize_headline,
    sort_articles_by_date,
)


class TestURLCanonicalization:
    def test_strips_tracking_parameters_only(self):
        url = "https://example.com/markets/story?utm_source=twitter&utm_medium=social&article_id=12345&ref=homepage"
        canonical = canonicalize_url(url)
        assert "utm_source" not in canonical
        assert "utm_medium" not in canonical
        assert "ref" not in canonical
        # Substantive parameter must be preserved
        assert "article_id=12345" in canonical
        assert canonical.startswith("https://example.com/markets/story")

    def test_preserves_clean_url_without_params(self):
        url = "https://www.sebi.gov.in/legal/circulars/sep-2026/circular_1.html"
        assert canonicalize_url(url) == url

    def test_strips_fragment(self):
        url = "https://rbi.org.in/press/release_123.html#section-two"
        assert canonicalize_url(url) == "https://rbi.org.in/press/release_123.html"

    def test_handles_empty_or_malformed_url(self):
        assert canonicalize_url("") == ""
        assert canonicalize_url("   ") == ""
        assert canonicalize_url("not-a-valid-url") == "not-a-valid-url"


class TestHeadlineNormalization:
    def test_normalizes_casing_and_punctuation(self):
        h1 = "SEBI Mandates T+0 Settlement for Top 500 Equities!"
        h2 = "sebi mandates t0 settlement for top 500 equities"
        assert normalize_headline(h1) == normalize_headline(h2)

    def test_collapses_excessive_whitespace(self):
        h = "  RBI   Repo   Rate   Announcement   "
        assert normalize_headline(h) == "rbi repo rate announcement"


class TestTimestampNormalizationAndSorting:
    def test_parses_rfc2822_date(self):
        rfc_date = "Wed, 14 Oct 2026 12:30:00 GMT"
        normalized = normalize_rss_pub_date(rfc_date)
        assert normalized == "2026-10-14T12:30:00+00:00"

    def test_parses_iso8601_date(self):
        iso_date = "2026-10-14T18:00:00+05:30"
        normalized = normalize_rss_pub_date(iso_date)
        # Should be converted to UTC ISO format
        assert normalized.startswith("2026-10-14T12:30:00")

    def test_unknown_date_preserved_as_empty_never_fabricated(self):
        assert normalize_rss_pub_date(None) == ""
        assert normalize_rss_pub_date("") == ""
        assert normalize_rss_pub_date("invalid-date-string") == ""

    def test_sorts_dated_newest_first_and_undated_last(self):
        art_older = NewsArticle(
            id="1",
            title="Older Article",
            summary="",
            url="https://news.com/1",
            source="Test",
            source_type=NewsSourceType.MARKET,
            published_at="2026-10-10T10:00:00+00:00",
        )
        art_newer = NewsArticle(
            id="2",
            title="Newer Article",
            summary="",
            url="https://news.com/2",
            source="Test",
            source_type=NewsSourceType.MARKET,
            published_at="2026-10-14T10:00:00+00:00",
        )
        art_undated = NewsArticle(
            id="3",
            title="Undated Notice",
            summary="",
            url="https://news.com/3",
            source="Test",
            source_type=NewsSourceType.REGULATORY,
            published_at="",
        )

        sorted_arts = sort_articles_by_date([art_older, art_undated, art_newer])
        assert sorted_arts[0].id == "2"  # Newer first
        assert sorted_arts[1].id == "1"  # Older second
        assert sorted_arts[2].id == "3"  # Undated at end


class TestArticleDeduplication:
    def test_deduplicates_by_canonical_url(self):
        art1 = NewsArticle(
            id="1",
            title="Market Rally Continues",
            summary="Nifty hits record high",
            url="https://example.com/story?utm_source=rss",
            source="Source A",
            source_type=NewsSourceType.MARKET,
            published_at="2026-10-14T10:00:00+00:00",
        )
        art2 = NewsArticle(
            id="2",
            title="Market Rally Continues",
            summary="Nifty hits record high",
            url="https://example.com/story?utm_source=twitter&ref=share",
            source="Source B",
            source_type=NewsSourceType.MARKET,
            published_at="2026-10-14T10:00:00+00:00",
        )

        deduped = deduplicate_articles([art1, art2])
        assert len(deduped) == 1
        assert deduped[0].id == "1"

    def test_deduplicates_syndicated_articles_by_normalized_headline(self):
        art1 = NewsArticle(
            id="1",
            title="SEBI issues fresh guidelines on algorithmic trading systems",
            summary="New circular released",
            url="https://source-a.com/article1",
            source="Source A",
            source_type=NewsSourceType.REGULATORY,
            published_at="2026-10-14T12:00:00+00:00",
        )
        art2 = NewsArticle(
            id="2",
            title="SEBI Issues Fresh Guidelines On Algorithmic Trading Systems!",
            summary="Syndicated wire report",
            url="https://source-b.com/syndicated-story",
            source="Source B",
            source_type=NewsSourceType.REGULATORY,
            published_at="2026-10-14T11:00:00+00:00",
        )

        deduped = deduplicate_articles([art1, art2])
        assert len(deduped) == 1
        assert deduped[0].id == "1"


class TestRSSWordBoundaryTickerMatching:
    def test_matches_isolated_ticker(self):
        assert matches_ticker_symbol("IT", "Circular regarding IT infrastructure audit")
        assert matches_ticker_symbol("BEL", "Defense ministry awards contract to BEL")
        assert matches_ticker_symbol("TCS", "TCS announces quarterly dividend")

    def test_does_not_match_substring_words(self):
        # "IT" inside infrastructure, security, initiative
        assert not matches_ticker_symbol("IT", "Security audit for critical infrastructure")
        # "BEL" inside label
        assert not matches_ticker_symbol("BEL", "New packaging label requirements")
        # "ON" inside announcement
        assert not matches_ticker_symbol("ON", "Official announcement of policy")

    def test_handles_tickers_with_punctuation(self):
        assert matches_ticker_symbol("M&M", "M&M vehicle sales surge in September")
        assert matches_ticker_symbol("M&M.NS", "Earnings call update for M&M")
        assert not matches_ticker_symbol("M&M", "AMM&MB corporate structure")

    def test_handles_exchange_suffixes(self):
        assert matches_ticker_symbol("RELIANCE.NS", "Reliance quarterly revenue growth")
        assert matches_ticker_symbol("INFY.BO", "Infosys (INFY) signs strategic cloud partnership")


class TestNewsServiceReliability:
    def test_get_macro_news_deduplication_and_sorting(self):
        art_older = NewsArticle(
            id="1",
            title="RBI Monetary Policy Committee Review",
            summary="Rates held unchanged",
            url="https://rbi.org/mpc?utm_source=feed",
            source="RBI",
            source_type=NewsSourceType.MACRO,
            published_at="2026-10-10T10:00:00+00:00",
        )
        art_newer = NewsArticle(
            id="2",
            title="SEBI Circular on Cybersecurity Framework",
            summary="Updated reporting guidelines",
            url="https://sebi.gov.in/circular?utm_campaign=regulatory",
            source="SEBI",
            source_type=NewsSourceType.REGULATORY,
            published_at="2026-10-14T12:00:00+00:00",
        )
        # Duplicate of art_newer with different URL params
        art_newer_dup = NewsArticle(
            id="3",
            title="SEBI Circular on Cybersecurity Framework",
            summary="Duplicate entry",
            url="https://sebi.gov.in/circular?utm_source=portal",
            source="SEBI Wire",
            source_type=NewsSourceType.REGULATORY,
            published_at="2026-10-14T12:00:00+00:00",
        )

        mock_provider = MagicMock()
        mock_provider.name = "MockLiveFeed"
        mock_provider.fetch_macro_news.return_value = [art_older, art_newer, art_newer_dup]

        service = NewsService(providers=[mock_provider], allow_mock=False)
        res = service.get_macro_news(limit=5)

        assert len(res.articles) == 2  # Duplicate dropped
        assert res.articles[0].id == "2"  # Newer article first
        assert res.articles[1].id == "1"  # Older article second

    def test_truthful_failure_when_providers_raise(self):
        failing_provider = MagicMock()
        failing_provider.name = "failing_provider"
        failing_provider.fetch_ticker_news.side_effect = RuntimeError("Connection timeout")

        service = NewsService(providers=[failing_provider], allow_mock=False)
        res = service.get_ticker_news("INFY")

        assert len(res.articles) == 0
        assert res.provider == "none"
        assert "No verified recent news could be retrieved" in (res.error_message or "")
