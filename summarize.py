"""Summarization layer for FinPulse AI."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)
BART_MODEL_NAME = "facebook/bart-large-cnn"
MIN_WORDS_TO_SUMMARIZE = 40


class DirectBartSummarizer:
    """Small callable wrapper used when pipeline('summarization') is unavailable."""

    def __init__(self, tokenizer: Any, model: Any):
        self.tokenizer = tokenizer
        self.model = model
        self.model.eval()

    def __call__(self, text: str, max_length: int, min_length: int, do_sample: bool, truncation: bool):
        import torch

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=1024,
            truncation=truncation,
        )
        with torch.no_grad():
            summary_ids = self.model.generate(
                **inputs,
                max_length=max_length,
                min_length=min_length,
                do_sample=do_sample,
                num_beams=4,
            )
        summary_text = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return [{"summary_text": summary_text}]


@lru_cache(maxsize=1)
def load_summarizer():
    """Load and cache the Hugging Face BART summarization pipeline."""
    try:
        from transformers import pipeline

        return pipeline("summarization", model=BART_MODEL_NAME)
    except Exception as pipeline_exc:
        LOGGER.warning("BART pipeline task unavailable: %s", pipeline_exc)

    if os.getenv("FINPULSE_ENABLE_DIRECT_BART", "").strip() != "1":
        LOGGER.warning(
            "Direct BART model load skipped. Use transformers<5 for the pipeline path, "
            "or set FINPULSE_ENABLE_DIRECT_BART=1 to force direct loading."
        )
        return None

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(BART_MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(BART_MODEL_NAME)
        return DirectBartSummarizer(tokenizer, model)
    except Exception as exc:
        LOGGER.warning("BART summarizer unavailable; snippets will be used directly: %s", exc)
        return None


def _clean_text(text: object) -> str:
    return " ".join(str(text or "").replace("\n", " ").split())


def _fallback_bullets(text: str, max_bullets: int = 3) -> str:
    """Create simple bullet-style text without a model."""
    if not text:
        return ""
    sentences = [segment.strip() for segment in text.replace(";", ".").split(".") if segment.strip()]
    selected = sentences[:max_bullets] or [text]
    return "\n".join(f"- {sentence}" for sentence in selected)


def summarize_text(text: object, min_words: int = MIN_WORDS_TO_SUMMARIZE) -> str:
    """Summarize one snippet into 2-3 bullets, with short-text and model fallbacks."""
    cleaned = _clean_text(text)
    if not cleaned:
        return ""

    if len(cleaned.split()) < min_words:
        return cleaned

    summarizer = load_summarizer()
    if summarizer is None:
        return _fallback_bullets(cleaned)

    try:
        result = summarizer(
            cleaned,
            max_length=95,
            min_length=30,
            do_sample=False,
            truncation=True,
        )
        summary_text = result[0]["summary_text"]
        return _fallback_bullets(summary_text)
    except Exception as exc:
        LOGGER.warning("Summarization failed; using original snippet fallback: %s", exc)
        return _fallback_bullets(cleaned)


def add_summaries(news_df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the news DataFrame with a summary column."""
    if news_df.empty:
        output = news_df.copy()
        output["summary"] = []
        return output

    output = news_df.copy()
    output["summary"] = output["snippet"].apply(summarize_text)
    return output
