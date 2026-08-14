"""Signal aggregation for FinPulse AI.

This file intentionally shares a name with Python's standard ``signal`` module
because the capstone spec requires ``signal.py``. To avoid breaking libraries
that import the standard module, we first re-export the stdlib signal API, then
define the FinPulse-specific helpers below.
"""

from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path
from typing import Iterable


def _load_stdlib_signal_exports() -> None:
    stdlib_signal_path = Path(sysconfig.get_path("stdlib")) / "signal.py"
    spec = importlib.util.spec_from_file_location("_finpulse_stdlib_signal", stdlib_signal_path)
    if not spec or not spec.loader:
        return

    stdlib_signal = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = stdlib_signal
    spec.loader.exec_module(stdlib_signal)
    for name in dir(stdlib_signal):
        if name.startswith("__") and name not in {"__doc__", "__all__"}:
            continue
        globals().setdefault(name, getattr(stdlib_signal, name))


_load_stdlib_signal_exports()


BULLISH_THRESHOLD = 0.4
BEARISH_THRESHOLD = -0.4


def sentiment_direction(score: float, threshold: float = BULLISH_THRESHOLD) -> str:
    """Convert a numeric sentiment score into positive/negative/neutral."""
    if score > threshold:
        return "positive"
    if score < -threshold:
        return "negative"
    return "neutral"


def signal_from_score(score: float) -> str:
    """Convert an aggregate score into the user-facing directional signal."""
    if score > BULLISH_THRESHOLD:
        return "Bullish"
    if score < BEARISH_THRESHOLD:
        return "Bearish"
    return "Neutral"


def _recency_weights(count: int) -> list[float]:
    """Return descending recency weights for newest-to-oldest rows."""
    if count <= 0:
        return []
    return [1.0 / (index + 1) for index in range(count)]


def _confidence_label(agreement_count: int, directional_count: int) -> str:
    if directional_count == 0:
        return "Low Confidence"
    agreement_ratio = agreement_count / directional_count
    if agreement_ratio >= 0.7 and directional_count >= 3:
        return "High Confidence"
    if agreement_ratio >= 0.5:
        return "Medium Confidence"
    return "Low Confidence"


def _confidence_detail(signal: str, labels: Iterable[str]) -> tuple[str, int, int]:
    all_labels = list(labels)
    article_count = len(all_labels)
    if signal == "Bullish":
        agreement_count = sum(label == "positive" for label in all_labels)
        direction_word = "positive"
    elif signal == "Bearish":
        agreement_count = sum(label == "negative" for label in all_labels)
        direction_word = "negative"
    else:
        neutral_count = sum(label == "neutral" for label in all_labels)
        level = _confidence_label(neutral_count, article_count)
        return f"{neutral_count}/{article_count} articles neutral = {level}", neutral_count, article_count

    level = _confidence_label(agreement_count, article_count)
    return f"{agreement_count}/{article_count} articles {direction_word} = {level}", agreement_count, article_count


def aggregate_article_signals(news_df):
    """Aggregate article sentiment into one row per ticker.

    The input is expected to include ticker, published_date, sentiment_score,
    and sentiment_label columns.
    """
    import pandas as pd

    if news_df.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "article_count",
                "aggregate_score",
                "signal",
                "confidence",
                "agreement_count",
                "directional_article_count",
            ]
        )

    rows: list[dict[str, object]] = []
    working = news_df.copy()
    working["published_date"] = pd.to_datetime(working["published_date"], utc=True, errors="coerce")

    for ticker, ticker_df in working.groupby("ticker"):
        ticker_df = ticker_df.sort_values("published_date", ascending=False).reset_index(drop=True)
        weights = _recency_weights(len(ticker_df))
        weighted_score = (
            (ticker_df["sentiment_score"].astype(float) * weights).sum() / sum(weights)
            if weights
            else 0.0
        )
        signal = signal_from_score(float(weighted_score))
        confidence, agreement_count, directional_count = _confidence_detail(
            signal,
            ticker_df["sentiment_label"].astype(str).str.lower().tolist(),
        )

        rows.append(
            {
                "ticker": ticker,
                "article_count": int(len(ticker_df)),
                "aggregate_score": round(float(weighted_score), 4),
                "signal": signal,
                "confidence": confidence,
                "agreement_count": int(agreement_count),
                "directional_article_count": int(directional_count),
            }
        )

    return pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)


def generate_stock_signals(news_df):
    """Alias kept expressive for app and report usage."""
    return aggregate_article_signals(news_df)
