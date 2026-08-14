# FinPulse AI

FinPulse AI is an MBA capstone prototype for financial news summarization and sentiment-driven equity signals. It ingests recent equity news through yfinance, summarizes article snippets, scores financial sentiment with FinBERT, aggregates stock-level directional signals, and compares a lightweight historical hit rate against random and naive baselines.

This is a decision-support prototype only. It is not investment advice and does not produce price targets, stop-losses, position sizing, portfolio returns, or buy/sell recommendations.

## Stock Universe

Default tickers:

- AAPL
- TSLA
- NVDA
- MSFT
- GOOGL

## Setup

Use Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The first run downloads Hugging Face models:

- `facebook/bart-large-cnn` for summarization
- `ProsusAI/finbert` for financial sentiment

If model loading fails, the prototype logs a warning and uses simpler text/keyword fallbacks so the app can still be demonstrated.

## Run the Pipeline

```bash
python main.py
```

Optional ticker override:

```bash
python main.py --tickers AAPL NVDA MSFT --max-articles 10
```

Comma-separated ticker input also works:

```bash
python main.py --tickers AAPL,TSLA,NVDA --max-articles 10
```

Generated CSV files are written to `outputs/`:

- `finpulse_articles.csv`
- `finpulse_signals.csv`
- `finpulse_backtest_summary.csv`
- `finpulse_backtest_events.csv`

## Run the Dashboard

```bash
streamlit run streamlit_app.py
```

The dashboard includes:

- Stock selector
- Live article feed with headline, summary, sentiment score, and contributing phrases
- Aggregated Bullish/Bearish/Neutral signal with confidence
- Backtest hit-rate chart against random and naive baselines
- CSV export for the day's summaries and signals

## Backtest Method

For available news events in the last 90 days, the prototype checks whether each sentiment-implied direction matched the stock's actual direction over the following 3 trading days.

It reports:

- Sentiment signal hit rate
- Random coin-flip baseline hit rate
- Naive baseline hit rate using yesterday's price direction

The backtest is intentionally limited to directional hit-rate comparison. It does not simulate profitability, P&L, transaction costs, slippage, liquidity, position sizing, or portfolio construction.

## Limitations

- yfinance news may return sparse feeds, schema variations, or temporary fetch failures.
- News snippets can be short and may not contain the full article context.
- The 90-day event sample can be small, especially when the news provider only exposes recent articles.
- FinBERT scores sentiment, not causality or materiality.
- Keyword explainability is approximate and is not full SHAP/LIME attribution.
- Random baseline results vary by seed and sample size.
- This prototype is for research and decision support only, not live trading.
