"""Script to precompute all real historical comparison data (1Y, 3Y, 5Y, ALL) and fetch live news for FinPulse."""

import os
import sys
import json
import pandas as pd
import numpy as np

sys.path.insert(0, "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI")
import streamlit_app
import ingest
import sentiment
import company_profiles

TICKERS = ["POWERGRID.NS", "NTPC.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "NMDC.NS"]
TF_MAP = {"1Y": "1y", "3Y": "3y", "5Y": "5y", "ALL": "max"}

def format_relative_time(dt_val):
    parsed = pd.to_datetime(dt_val, utc=True, errors="coerce")
    if pd.isna(parsed):
        return "recently"
    now = pd.Timestamp.now(tz="UTC")
    diff = now - parsed
    total_seconds = int(diff.total_seconds())
    if total_seconds < 0:
        return "just now"
    if total_seconds < 60:
        return f"{total_seconds}s ago" if total_seconds > 0 else "just now"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    years = days // 365
    return f"{years}y ago"

def sample_df(df, step=1):
    if step <= 1 or len(df) <= step:
        return df
    indices = list(range(0, len(df) - 1, step))
    if indices[-1] != len(df) - 1:
        indices.append(len(df) - 1)
    return df.iloc[indices]

def build_data():
    existing_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/app_data.json"
    with open(existing_path) as f:
        app_data = json.load(f)

    for ticker in TICKERS:
        print(f"Processing {ticker}...")
        stock_obj = app_data["stocks"].setdefault(ticker, {})
        timeframes_data = {}

        for tf_label, period in TF_MAP.items():
            print(f"  Fetching comparison {tf_label} ({period})...")
            try:
                comp_df = streamlit_app.fetch_benchmark_comparison_data(ticker, period)
            except Exception as e:
                print(f"    Error: {e}")
                comp_df = pd.DataFrame()

            if not comp_df.empty and len(comp_df) >= 2:
                # Downsample if needed
                step = 1
                if tf_label == "3Y":
                    step = 2
                elif tf_label == "5Y":
                    step = 3
                elif tf_label == "ALL":
                    step = 8

                sampled = sample_df(comp_df, step)
                start_dt = comp_df["Date"].iloc[0]
                start_date_str = start_dt.strftime("%d %b %Y") if hasattr(start_dt, "strftime") else str(start_dt)[:10]

                stock_ret = float(comp_df["stock_return_pct"].iloc[-1])
                nifty_ret = float(comp_df["nifty_return_pct"].iloc[-1])
                alpha = stock_ret - nifty_ret

                timeframes_data[tf_label] = {
                    "start_date": start_date_str,
                    "stock_return": round(stock_ret, 1),
                    "nifty_return": round(nifty_ret, 1),
                    "alpha": round(alpha, 1),
                    "dates": [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10] for d in sampled["Date"]],
                    "stock_returns": [round(float(v), 2) for v in sampled["stock_return_pct"]],
                    "nifty_returns": [round(float(v), 2) for v in sampled["nifty_return_pct"]],
                    "stock_closes": [round(float(v), 2) for v in sampled["stock_close"]],
                    "nifty_closes": [round(float(v), 1) for v in sampled["nifty_close"]],
                }

        stock_obj["timeframes"] = timeframes_data
        if "1Y" in timeframes_data:
            stock_obj["comparison"] = timeframes_data["1Y"]

        # Fetch live news articles
        print(f"  Fetching live news for {ticker}...")
        try:
            news_df = ingest.fetch_news_for_tickers([ticker], max_articles_per_ticker=8)
            if not news_df.empty:
                scored_df = sentiment.add_sentiment_scores(news_df)
                articles_list = []
                for _, row in scored_df.iterrows():
                    headline = str(row.get("headline", "")).strip()
                    if not headline or "Stock Price, News, Quote & History - Yahoo" in headline:
                        continue
                    pub_dt = row.get("published_date")
                    rel_t = format_relative_time(pub_dt)
                    s_label = str(row.get("sentiment_label", "neutral")).lower()
                    if s_label not in ("positive", "negative", "neutral"):
                        s_label = "neutral"
                    s_score = float(row.get("sentiment_score", 0.0) or 0.0)

                    articles_list.append({
                        "headline": headline,
                        "source_url": str(row.get("source_url", "")).strip(),
                        "published_date": pub_dt.isoformat() if hasattr(pub_dt, "isoformat") else str(pub_dt),
                        "time_ago": rel_t,
                        "sentiment_label": s_label,
                        "sentiment_score": round(s_score, 2),
                    })
                if articles_list:
                    stock_obj["articles"] = articles_list
                    print(f"    Added {len(articles_list)} articles")
        except Exception as e:
            print(f"    Error fetching news: {e}")

    output_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/app_data.json"
    with open(output_path, "w") as f:
        json.dump(app_data, f, indent=2, default=str)
    print(f"Successfully wrote data to {output_path}")

if __name__ == "__main__":
    build_data()
