"""Lightweight directional hit-rate backtest for FinPulse AI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

EVENT_COLUMNS = [
    "ticker",
    "event_date",
    "headline",
    "sentiment_score",
    "signal_hit",
    "random_hit",
    "naive_hit",
]


@dataclass(frozen=True)
class BacktestConfig:
    lookback_days: int = 90
    forward_trading_days: int = 3
    random_seed: int = 42


def fetch_price_history(ticker: str, lookback_days: int = 90) -> pd.DataFrame:
    """Fetch daily OHLCV price history for one ticker."""
    try:
        import yfinance as yf

        price_df = yf.download(
            ticker,
            period=f"{lookback_days + 20}d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as exc:
        LOGGER.warning("Skipping backtest for %s: yfinance download failed: %s", ticker, exc)
        return pd.DataFrame()

    if price_df.empty:
        LOGGER.warning("Skipping backtest for %s: no price history returned.", ticker)
        return pd.DataFrame()

    if isinstance(price_df.columns, pd.MultiIndex):
        price_df.columns = price_df.columns.get_level_values(0)

    if "Close" not in price_df.columns:
        LOGGER.warning("Skipping backtest for %s: price history has no Close column.", ticker)
        return pd.DataFrame()

    price_df = price_df.reset_index()
    price_df["Date"] = pd.to_datetime(price_df["Date"], utc=True, errors="coerce").dt.tz_convert(None)
    price_df = price_df.dropna(subset=["Date", "Close"])
    price_df = price_df.sort_values("Date").tail(lookback_days + 10).reset_index(drop=True)
    return price_df


def _event_direction(score: float, threshold: float = 0.05) -> int:
    """Map article sentiment to 1, -1, or 0. A lower threshold increases events."""
    if score > threshold:
        return 1
    if score < -threshold:
        return -1
    return 0


def _actual_forward_direction(price_df: pd.DataFrame, event_date: pd.Timestamp, forward_days: int) -> int | None:
    eligible = price_df[price_df["Date"] >= event_date.normalize()]
    if len(eligible) <= forward_days:
        return None

    start_price = float(eligible.iloc[0]["Close"])
    end_price = float(eligible.iloc[forward_days]["Close"])
    forward_return = (end_price / start_price) - 1.0

    if forward_return > 0:
        return 1
    if forward_return < 0:
        return -1
    return 0


def _yesterday_direction(price_df: pd.DataFrame, event_date: pd.Timestamp) -> int | None:
    previous_prices = price_df[price_df["Date"] < event_date.normalize()]
    if len(previous_prices) < 2:
        return None

    yesterday_close = float(previous_prices.iloc[-1]["Close"])
    prior_close = float(previous_prices.iloc[-2]["Close"])
    previous_return = (yesterday_close / prior_close) - 1.0

    if previous_return > 0:
        return 1
    if previous_return < 0:
        return -1
    return 0


def build_backtest_events(
    scored_news_df: pd.DataFrame,
    tickers: Iterable[str],
    config: BacktestConfig | None = None,
) -> pd.DataFrame:
    """Create per-news-event directional outcomes for the last 90 days."""
    config = config or BacktestConfig()
    if scored_news_df.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    rng = np.random.default_rng(config.random_seed)
    events: list[dict[str, object]] = []
    working = scored_news_df.copy()
    working["published_date"] = pd.to_datetime(working["published_date"], utc=True, errors="coerce")
    working = working.dropna(subset=["published_date"])
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=config.lookback_days)
    working = working[working["published_date"] >= cutoff]

    for ticker in tickers:
        ticker_news = working[working["ticker"] == ticker].copy()
        if ticker_news.empty:
            continue

        price_df = fetch_price_history(ticker, config.lookback_days)
        if price_df.empty:
            continue

        for _, article in ticker_news.iterrows():
            signal_direction = _event_direction(float(article.get("sentiment_score", 0.0)))
            if signal_direction == 0:
                continue

            event_date = pd.Timestamp(article["published_date"]).tz_convert(None)
            actual_direction = _actual_forward_direction(price_df, event_date, config.forward_trading_days)
            naive_direction = _yesterday_direction(price_df, event_date)
            if actual_direction is None or naive_direction is None or actual_direction == 0:
                continue

            random_direction = int(rng.choice([-1, 1]))
            events.append(
                {
                    "ticker": ticker,
                    "event_date": event_date.date().isoformat(),
                    "headline": article.get("headline", ""),
                    "sentiment_score": float(article.get("sentiment_score", 0.0)),
                    "signal_hit": int(signal_direction == actual_direction),
                    "random_hit": int(random_direction == actual_direction),
                    "naive_hit": int(naive_direction == actual_direction),
                }
            )

    return pd.DataFrame(events, columns=EVENT_COLUMNS)


def summarize_backtest_events(events_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize event-level hits into side-by-side hit rates by ticker."""
    columns = [
        "ticker",
        "events",
        "sentiment_signal_hit_rate",
        "random_baseline_hit_rate",
        "naive_baseline_hit_rate",
    ]
    if events_df.empty:
        return pd.DataFrame(columns=columns)

    summary = (
        events_df.groupby("ticker")
        .agg(
            events=("ticker", "size"),
            sentiment_signal_hit_rate=("signal_hit", "mean"),
            random_baseline_hit_rate=("random_hit", "mean"),
            naive_baseline_hit_rate=("naive_hit", "mean"),
        )
        .reset_index()
    )
    for column in columns[2:]:
        summary[column] = (summary[column] * 100).round(1)
    return summary[columns]


def run_backtest(
    scored_news_df: pd.DataFrame,
    tickers: Iterable[str],
    config: BacktestConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (summary_df, event_df) for the lightweight hit-rate backtest."""
    events_df = build_backtest_events(scored_news_df, tickers, config)
    return summarize_backtest_events(events_df), events_df
