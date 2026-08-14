"""News ingestion utilities for FinPulse AI.

Fetches recent yfinance news headlines/snippets and returns a tidy DataFrame
that downstream modules can summarize and score.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from html import unescape
from typing import Any, Iterable

import pandas as pd

LOGGER = logging.getLogger(__name__)

DEFAULT_TICKERS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]


def _nested_get(item: Mapping[str, Any], *paths: str) -> Any:
    """Return the first present value from dot-separated mapping paths."""
    for path in paths:
        current: Any = item
        for key in path.split("."):
            if not isinstance(current, Mapping) or key not in current:
                current = None
                break
            current = current[key]
        if current not in (None, ""):
            return current
    return None


def _string_value(value: Any) -> str:
    """Normalize a scalar or yfinance URL mapping to a clean string."""
    if isinstance(value, Mapping):
        value = value.get("url") or value.get("href")
    cleaned = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(unescape(cleaned).split())


def _parse_published_date(value: Any) -> pd.Timestamp:
    """Return a timezone-aware pandas Timestamp from epoch seconds/ms or strings."""
    if value in (None, ""):
        return pd.Timestamp.now(tz="UTC")

    if isinstance(value, (int, float)):
        unit = "ms" if abs(float(value)) > 10_000_000_000 else "s"
        parsed = pd.to_datetime(value, unit=unit, utc=True, errors="coerce")
    else:
        parsed = pd.to_datetime(value, utc=True, errors="coerce")

    if pd.isna(parsed):
        LOGGER.warning("Could not parse yfinance publish timestamp %r; using current UTC time.", value)
        return pd.Timestamp.now(tz="UTC")
    return pd.Timestamp(parsed)


def _coerce_news_items(raw_news: Any) -> list[Mapping[str, Any]]:
    """Normalize possible yfinance news containers into a list of mappings."""
    if isinstance(raw_news, Mapping):
        raw_news = raw_news.get("news") or raw_news.get("items") or raw_news.get("data") or []
    if not isinstance(raw_news, list):
        return []
    return [item for item in raw_news if isinstance(item, Mapping)]


def _map_yfinance_article(ticker: str, article: Mapping[str, Any]) -> dict[str, object] | None:
    """Map flat or nested yfinance article payloads to the FinPulse schema."""
    headline = _string_value(_nested_get(article, "title", "content.title"))
    snippet = _string_value(
        _nested_get(
            article,
            "summary",
            "description",
            "content.summary",
            "content.description",
            "content.snippet",
        )
    )
    if not snippet:
        snippet = headline

    source_url = _string_value(
        _nested_get(
            article,
            "link",
            "url",
            "content.canonicalUrl",
            "content.canonicalUrl.url",
            "content.clickThroughUrl",
            "content.clickThroughUrl.url",
            "clickThroughUrl",
            "clickThroughUrl.url",
        )
    )
    published_raw = _nested_get(
        article,
        "providerPublishTime",
        "publishTime",
        "published",
        "published_at",
        "pubDate",
        "content.providerPublishTime",
        "content.publishTime",
        "content.pubDate",
        "content.displayTime",
    )

    if not headline and not snippet:
        return None

    return {
        "ticker": ticker,
        "headline": headline or snippet,
        "snippet": snippet,
        "published_date": _parse_published_date(published_raw),
        "source_url": source_url,
    }


TICKER_ALIASES: dict[str, list[str]] = {
    "TATAMOTORS.NS": ["TMCV.NS", "TMPV.NS", "TATAMOTORS.BO", "TMCV.BO"],
    "TMPV.NS": ["TMPV.NS", "TMCV.NS", "TATAMOTORS.NS"],
    "TMCV.NS": ["TMCV.NS", "TMPV.NS", "TATAMOTORS.NS"],
    "M&M.NS": ["MM.NS", "M&M.BO", "MM.BO"],
    "LTI.NS": ["LTIM.NS", "LTI.BO", "LTIM.BO", "540005.BO"],
    "MINDTREE.NS": ["LTIM.NS", "LTIM.BO", "540005.BO"],
    "LTIM.NS": ["LTIM.NS", "LTIM.BO", "540005.BO", "LTI.NS"],
    "HDFC.NS": ["HDFCBANK.NS", "HDFCBANK.BO"],
    "IDFCFIRSTB.NS": ["IDFCFIRSTB.NS", "IDFCBK.BO", "IDFCFIRSTB.BO"],
    "BAJAJ-AUTO.NS": ["BAJAJ-AUTO.NS", "BAJAJ_AUTO.NS", "BAJAJ-AUTO.BO"],
    "MCDOWELL-N.NS": ["UNITDSPR.NS", "MCDOWELL-N.BO"],
}


def _get_ticker_candidates(ticker: str) -> list[str]:
    clean = ticker.strip().upper()
    candidates = [clean]
    if clean in TICKER_ALIASES:
        for alias in TICKER_ALIASES[clean]:
            if alias not in candidates:
                candidates.append(alias)
    if clean.endswith(".NS"):
        bo_sym = clean[:-3] + ".BO"
        if bo_sym not in candidates:
            candidates.append(bo_sym)
    elif clean.endswith(".BO"):
        ns_sym = clean[:-3] + ".NS"
        if ns_sym not in candidates:
            candidates.append(ns_sym)
    return candidates


def fetch_yfinance_news(
    ticker: str,
    max_articles: int = 15,
    timeout_seconds: int = 12,
) -> pd.DataFrame:
    """Fetch recent news for one ticker through yfinance with candidate fallbacks.

    Fetch failures are logged and returned as an empty DataFrame so the full
    multi-ticker pipeline can continue running. ``timeout_seconds`` is kept for
    backward compatibility with earlier RSS-based callers.
    """
    ticker = ticker.upper().strip()
    _ = timeout_seconds
    import yfinance as yf

    candidates = _get_ticker_candidates(ticker)
    raw_news = None

    for candidate in candidates:
        try:
            items = yf.Ticker(candidate).news
            if items:
                raw_news = items
                break
        except Exception as exc:
            LOGGER.warning("yfinance news fetch failed for candidate %s: %s", candidate, exc)

    if not raw_news:
        LOGGER.warning("No usable yfinance news articles found for %s across candidates %s.", ticker, candidates)
        return empty_news_frame()

    rows: list[dict[str, object]] = []
    for article in _coerce_news_items(raw_news)[:max_articles]:
        mapped_article = _map_yfinance_article(ticker, article)
        if mapped_article:
            rows.append(mapped_article)

    if not rows:
        LOGGER.warning("Could not map any yfinance news articles for %s.", ticker)
        return empty_news_frame()

    return pd.DataFrame(rows).sort_values("published_date", ascending=False).reset_index(drop=True)


fetch_yahoo_finance_news = fetch_yfinance_news


def fetch_news_for_tickers(
    tickers: Iterable[str],
    max_articles_per_ticker: int = 15,
    timeout_seconds: int = 12,
) -> pd.DataFrame:
    """Fetch and combine yfinance news for multiple tickers."""
    frames = [
        fetch_yfinance_news(
            ticker=ticker,
            max_articles=max_articles_per_ticker,
            timeout_seconds=timeout_seconds,
        )
        for ticker in tickers
    ]
    non_empty_frames = [frame for frame in frames if not frame.empty]
    if not non_empty_frames:
        return empty_news_frame()
    return pd.concat(non_empty_frames, ignore_index=True).sort_values(
        ["ticker", "published_date"],
        ascending=[True, False],
    )


def empty_news_frame() -> pd.DataFrame:
    """Return the canonical empty news DataFrame."""
    return pd.DataFrame(
        columns=["ticker", "headline", "snippet", "published_date", "source_url"]
    )
