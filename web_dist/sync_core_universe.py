"""Sync real news, FinBERT sentiment, trading confluence, and historical benchmarks for core NSE stocks."""

import sys
import os
import json
import time
import pandas as pd

sys.path.insert(0, "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI")
import streamlit_app
from ingest import fetch_news_for_tickers
from sentiment import add_sentiment_scores
from signals import generate_stock_signals
from nse_universe import NSE_COMPANIES

TARGET_TICKERS = [
    "TATAMOTORS.NS",
    "AMBUJACEM.NS",
    "BEL.NS",
    "INDUSINDBK.NS",
    "WIPRO.NS",
    "MARUTI.NS",
    "BAJFINANCE.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "ADANIENT.NS",
    "TATASTEEL.NS",
    "M&M.NS",
    "COALINDIA.NS",
]

def format_time_ago(ts):
    if not ts or pd.isna(ts):
        return "recently"
    try:
        parsed = pd.to_datetime(ts, utc=True)
        now = pd.Timestamp.now(tz="UTC")
        diff_sec = int((now - parsed).total_seconds())
        if diff_sec < 60:
            return "just now"
        if diff_sec < 3600:
            return f"{diff_sec // 60}m ago"
        if diff_sec < 86400:
            return f"{diff_sec // 3600}h ago"
        return f"{diff_sec // 86400}d ago"
    except Exception:
        return "recently"

def run():
    app_data_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/app_data.json"
    with open(app_data_path) as f:
        app_data = json.load(f)

    stocks_dict = app_data.setdefault("stocks", {})
    ticker_to_name = {v: k for k, v in NSE_COMPANIES.items()}

    print(f"Syncing real news & benchmarks for {len(TARGET_TICKERS)} core tickers...")
    t0 = time.time()

    for idx, ticker in enumerate(TARGET_TICKERS, 1):
        comp_name = ticker_to_name.get(ticker, ticker.replace(".NS", ""))
        print(f"[{idx}/{len(TARGET_TICKERS)}] Processing {comp_name} ({ticker})...")
        t_start = time.time()

        stock_entry = stocks_dict.setdefault(ticker, {})
        stock_entry["company"] = comp_name
        stock_entry["ticker"] = ticker

        # 1. Fetch & score real news
        try:
            news_df = fetch_news_for_tickers([ticker], max_articles_per_ticker=4)
            if not news_df.empty:
                scored_df = add_sentiment_scores(news_df)
                sig_df = generate_stock_signals(scored_df)
                sig_row = sig_df.iloc[0] if not sig_df.empty else None

                articles = []
                bullish_factors = []
                bearish_factors = []

                for _, r in scored_df.iterrows():
                    lbl = str(r.get("sentiment_label", "neutral")).lower()
                    hd = str(r.get("headline", "Market update"))
                    url = str(r.get("source_url", "") or "")
                    sc = float(r.get("sentiment_score", 0.0) or 0.0)
                    time_ago = format_time_ago(r.get("published_date"))

                    articles.append({
                        "headline": hd,
                        "source_url": url,
                        "published_date": str(r.get("published_date", "")),
                        "time_ago": time_ago,
                        "sentiment_label": lbl,
                        "sentiment_score": round(sc, 2)
                    })

                    if lbl == "positive" and len(bullish_factors) < 2:
                        bullish_factors.append(hd[:70] + "..." if len(hd) > 70 else hd)
                    elif lbl == "negative" and len(bearish_factors) < 2:
                        bearish_factors.append(hd[:70] + "..." if len(hd) > 70 else hd)

                if not bullish_factors:
                    bullish_factors.append("Institutional volume interest and technical support")
                if not bearish_factors:
                    bearish_factors.append("Macro sector consolidation and volatility")

                stock_entry["articles"] = articles
                stock_entry["total_articles"] = len(articles)
                stock_entry["key_factors"] = {
                    "bullish": bullish_factors,
                    "bearish": bearish_factors
                }

                if sig_row is not None:
                    raw_sig = str(sig_row.get("signal", "Neutral")).capitalize()
                    stock_entry["signal"] = raw_sig
                    stock_entry["confluence_status"] = str(sig_row.get("confluence_status", "NEUTRAL RANGE"))
                    stock_entry["confluence_class"] = str(sig_row.get("confluence_class", "fp-badge-neutral"))
                    stock_entry["confluence_score"] = round(float(sig_row.get("confluence_score", 0.0) or 0.0), 2)
                    stock_entry["aggregate_score"] = round(float(sig_row.get("aggregate_score", 0.0) or 0.0), 2)
                    stock_entry["agreement_count"] = int(sig_row.get("agreement_count", 2) or 2)
                    stock_entry["trend_direction"] = str(sig_row.get("trend_direction", "NEUTRAL")).upper()
                    stock_entry["trend_z"] = round(float(sig_row.get("trend_z", 0.0) or 0.0), 2)
                    stock_entry["rsi_14"] = round(float(sig_row.get("rsi_14", 50.0) or 50.0), 1)
                    stock_entry["volume_ratio"] = round(float(sig_row.get("volume_ratio", 1.0) or 1.0), 2)
                    stock_entry["nifty_pct"] = round(float(sig_row.get("nifty_pct", 0.0) or 0.0), 2)
                    stock_entry["vix_level"] = round(float(sig_row.get("vix_level", 15.0) or 15.0), 1)
                    stock_entry["vix_regime"] = str(sig_row.get("vix_regime", "Normal"))

                    conf_str = str(sig_row.get("confidence", ""))
                    if "High" in conf_str:
                        stock_entry["confidence"] = "High Confidence"
                        stock_entry["confidence_pct"] = 84
                    elif "Medium" in conf_str:
                        stock_entry["confidence"] = "Medium Confidence"
                        stock_entry["confidence_pct"] = 68
                    else:
                        stock_entry["confidence"] = "Low Confidence"
                        stock_entry["confidence_pct"] = 52

                    reasons = list(sig_row.get("confluence_reasons", []))
                    if not reasons:
                        reasons = [
                            f"{len(articles)} recent financial news articles analyzed for {ticker.replace('.NS', '')}.",
                            f"Technical momentum ({stock_entry['trend_z']:+.2f}z) guides confluence regime.",
                            f"Market conditions: Nifty {stock_entry['nifty_pct']:+.2f}%, VIX {stock_entry['vix_level']}."
                        ]
                    stock_entry["reasons"] = reasons

                # Real summary from top article
                if articles:
                    top_art = articles[0]
                    stock_entry["summary_headline"] = top_art["headline"]
                    snippet = news_df.iloc[0].get("snippet") or news_df.iloc[0].get("summary") or top_art["headline"]
                    stock_entry["summary_body"] = f"{comp_name} ({ticker.replace('.NS', '')}): {snippet}"
        except Exception as e:
            print(f"Error fetching news/signals for {ticker}: {e}")

        # 2. Fetch real benchmark curves for 4 timeframes
        timeframes = {}
        for tf_label, period in [("1Y", "1y"), ("3Y", "3y"), ("5Y", "5y"), ("ALL", "max")]:
            try:
                b_df = streamlit_app.fetch_benchmark_comparison_data(ticker, period)
                if not b_df.empty and len(b_df) >= 2:
                    start_date_str = b_df["Date"].iloc[0].strftime("%d %b %Y")
                    stock_ret = round(float(b_df["stock_return_pct"].iloc[-1]), 1)
                    nifty_ret = round(float(b_df["nifty_return_pct"].iloc[-1]), 1)
                    alpha = round(stock_ret - nifty_ret, 1)

                    timeframes[tf_label] = {
                        "start_date": start_date_str,
                        "stock_return": stock_ret,
                        "nifty_return": nifty_ret,
                        "alpha": alpha,
                        "dates": [d.strftime("%Y-%m-%d") for d in b_df["Date"]],
                        "stock_returns": [round(float(v), 2) for v in b_df["stock_return_pct"]],
                        "nifty_returns": [round(float(v), 2) for v in b_df["nifty_return_pct"]],
                        "stock_closes": [round(float(v), 2) for v in b_df["stock_close"]],
                        "nifty_closes": [round(float(v), 1) for v in b_df["nifty_close"]]
                    }
            except Exception as e:
                print(f"Error fetching benchmark {tf_label} for {ticker}: {e}")

        if timeframes:
            stock_entry["timeframes"] = timeframes
            stock_entry["comparison"] = timeframes.get("1Y", list(timeframes.values())[0])

        print(f"  Finished {ticker} in {time.time()-t_start:.1f}s (Articles: {len(stock_entry.get('articles', []))}, TF: {list(timeframes.keys())})")

    # Save to app_data.json and data.json
    with open(app_data_path, "w") as f:
        json.dump(app_data, f, indent=2, default=str)

    data_json_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/data.json"
    with open(data_json_path, "w") as f:
        json.dump(app_data, f, indent=2, default=str)

    print(f"Done! Updated {len(TARGET_TICKERS)} core stocks in {time.time()-t0:.1f}s.")

if __name__ == "__main__":
    run()
