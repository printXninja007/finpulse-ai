"""Financial sentiment scoring with FinBERT plus lightweight fallbacks."""

from __future__ import annotations

import logging
import re
from functools import lru_cache

import pandas as pd

LOGGER = logging.getLogger(__name__)
FINBERT_MODEL_NAME = "ProsusAI/finbert"

POSITIVE_TERMS = {
    "beat",
    "beats",
    "upgrade",
    "upgraded",
    "growth",
    "profit",
    "profits",
    "record",
    "strong",
    "surge",
    "surges",
    "gain",
    "gains",
    "rally",
    "bullish",
    "outperform",
    "expands",
    "higher",
}

NEGATIVE_TERMS = {
    "miss",
    "misses",
    "downgrade",
    "downgraded",
    "loss",
    "losses",
    "weak",
    "decline",
    "declines",
    "drop",
    "drops",
    "fall",
    "falls",
    "lawsuit",
    "probe",
    "bearish",
    "underperform",
    "cuts",
    "lower",
}


@lru_cache(maxsize=1)
def load_finbert():
    """Load and cache the FinBERT sentiment pipeline."""
    try:
        from transformers import pipeline

        return pipeline("sentiment-analysis", model=FINBERT_MODEL_NAME)
    except Exception as exc:
        LOGGER.warning("FinBERT unavailable; keyword fallback sentiment will be used: %s", exc)
        return None


def _clean_text(text: object) -> str:
    return " ".join(str(text or "").replace("\n", " ").split())


def _label_to_signed_score(label: str, confidence: float) -> float:
    label = label.lower()
    if label == "positive":
        return confidence
    if label == "negative":
        return -confidence
    return 0.0


def _keyword_fallback_sentiment(text: str) -> tuple[str, float]:
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower())
    if not words:
        return "neutral", 0.0

    positive_count = sum(word in POSITIVE_TERMS for word in words)
    negative_count = sum(word in NEGATIVE_TERMS for word in words)
    total_hits = positive_count + negative_count

    if total_hits == 0 or positive_count == negative_count:
        return "neutral", 0.0

    raw_score = (positive_count - negative_count) / max(total_hits, 1)
    score = max(min(raw_score * 0.75, 1.0), -1.0)
    label = "positive" if score > 0 else "negative"
    return label, score


def score_sentiment(text: object) -> dict[str, object]:
    """Score one text item from -1 to +1 and return label plus model metadata."""
    cleaned = _clean_text(text)
    if not cleaned:
        return {"sentiment_label": "neutral", "sentiment_score": 0.0, "sentiment_confidence": 0.0}

    finbert = load_finbert()
    if finbert is None:
        label, score = _keyword_fallback_sentiment(cleaned)
        return {
            "sentiment_label": label,
            "sentiment_score": float(score),
            "sentiment_confidence": abs(float(score)),
        }

    try:
        result = finbert(cleaned, truncation=True)[0]
        label = str(result["label"]).lower()
        confidence = float(result["score"])
        return {
            "sentiment_label": label,
            "sentiment_score": _label_to_signed_score(label, confidence),
            "sentiment_confidence": confidence,
        }
    except Exception as exc:
        LOGGER.warning("FinBERT scoring failed; using keyword fallback: %s", exc)
        label, score = _keyword_fallback_sentiment(cleaned)
        return {
            "sentiment_label": label,
            "sentiment_score": float(score),
            "sentiment_confidence": abs(float(score)),
        }


def add_sentiment_scores(news_df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the news DataFrame with FinBERT sentiment columns."""
    if news_df.empty:
        output = news_df.copy()
        for column in ["sentiment_label", "sentiment_score", "sentiment_confidence"]:
            output[column] = []
        return output

    output = news_df.copy()
    scoring_text = (output["headline"].fillna("") + ". " + output["snippet"].fillna("")).str.strip()
    scores = scoring_text.apply(score_sentiment).apply(pd.Series)
    return pd.concat([output.reset_index(drop=True), scores.reset_index(drop=True)], axis=1)


def extract_contributing_phrases(text: object, sentiment_label: object, max_phrases: int = 5) -> list[str]:
    """Extract simple sentiment-bearing phrases for explainability."""
    cleaned = _clean_text(text)
    label = str(sentiment_label or "neutral").lower()
    target_terms = POSITIVE_TERMS if label == "positive" else NEGATIVE_TERMS if label == "negative" else POSITIVE_TERMS | NEGATIVE_TERMS

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    phrases: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(term in lowered for term in target_terms):
            phrases.append(sentence.strip())
        if len(phrases) >= max_phrases:
            break

    if phrases:
        return phrases

    tokens = re.findall(r"[A-Za-z][A-Za-z\-']+", cleaned)
    return tokens[:max_phrases]


def add_explainability(news_df: pd.DataFrame) -> pd.DataFrame:
    """Add simple keyword/sentence explanations for article-level sentiment."""
    if news_df.empty:
        output = news_df.copy()
        output["contributing_phrases"] = []
        return output

    output = news_df.copy()
    output["contributing_phrases"] = output.apply(
        lambda row: extract_contributing_phrases(
            f"{row.get('headline', '')}. {row.get('snippet', '')}",
            row.get("sentiment_label", "neutral"),
        ),
        axis=1,
    )
    return output
