"""Command-line runner for the FinPulse AI prototype."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from backtest import BacktestConfig, run_backtest
from ingest import DEFAULT_TICKERS, fetch_news_for_tickers
from sentiment import add_explainability, add_sentiment_scores
from signals import generate_stock_signals
from summarize import add_summaries

DISCLAIMER = (
    "Decision-support only, not investment advice. FinPulse AI does not generate "
    "price targets, stop-losses, or buy/sell recommendations."
)


def run_pipeline(
    tickers: list[str] | None = None,
    max_articles_per_ticker: int = 15,
    output_dir: str | Path = "outputs",
) -> dict[str, pd.DataFrame]:
    """Run ingestion, summarization, sentiment, signal generation, and backtest."""
    tickers = normalize_tickers(tickers or DEFAULT_TICKERS)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logging.info("Fetching yfinance news for %s", ", ".join(tickers))
    news_df = fetch_news_for_tickers(tickers, max_articles_per_ticker=max_articles_per_ticker)
    if news_df.empty:
        logging.warning("No news articles were available. Outputs will be empty.")

    summarized_df = add_summaries(news_df)
    scored_df = add_sentiment_scores(summarized_df)
    explained_df = add_explainability(scored_df)
    signals_df = generate_stock_signals(explained_df)
    backtest_summary_df, backtest_events_df = run_backtest(
        explained_df,
        tickers,
        BacktestConfig(),
    )

    explained_df.to_csv(output_path / "finpulse_articles.csv", index=False)
    signals_df.to_csv(output_path / "finpulse_signals.csv", index=False)
    backtest_summary_df.to_csv(output_path / "finpulse_backtest_summary.csv", index=False)
    backtest_events_df.to_csv(output_path / "finpulse_backtest_events.csv", index=False)

    return {
        "articles": explained_df,
        "signals": signals_df,
        "backtest_summary": backtest_summary_df,
        "backtest_events": backtest_events_df,
    }


def normalize_tickers(raw_tickers: list[str]) -> list[str]:
    """Normalize space-separated and comma-separated ticker CLI input."""
    tickers: list[str] = []
    for raw_ticker in raw_tickers:
        tickers.extend(part.strip().upper() for part in raw_ticker.split(",") if part.strip())
    return tickers or DEFAULT_TICKERS


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FinPulse AI capstone prototype.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Ticker symbols to analyze. Accepts spaces or commas, e.g. AAPL TSLA or AAPL,TSLA.",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=15,
        help="Maximum yfinance news articles per ticker.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for generated CSV outputs.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = _parse_args()
    results = run_pipeline(args.tickers, args.max_articles, args.output_dir)

    print("\nFinPulse AI")
    print(DISCLAIMER)
    print(f"\nArticles pulled: {len(results['articles'])}")
    if not results["articles"].empty:
        article_preview = results["articles"][
            ["ticker", "headline", "summary", "sentiment_label", "sentiment_score"]
        ].head(6)
        print("\nArticle Preview")
        print(article_preview.to_string(index=False, max_colwidth=90))
    print("\nSignals")
    print(results["signals"].to_string(index=False) if not results["signals"].empty else "No signals generated.")
    print("\nBacktest Summary")
    print(
        results["backtest_summary"].to_string(index=False)
        if not results["backtest_summary"].empty
        else "No eligible backtest events generated."
    )
    print(f"\nCSV outputs saved to: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
