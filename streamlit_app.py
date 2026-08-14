"""Streamlit dashboard for the FinPulse AI prototype."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backtest import BacktestConfig, run_backtest
from ingest import fetch_news_for_tickers
from nse_universe import NSE_COMPANIES
from sentiment import add_explainability, add_sentiment_scores, load_finbert
from signals import generate_stock_signals
from summarize import add_summaries, load_summarizer

DISCLAIMER = "Decision-support only, not investment advice. No price targets, stop-losses, or buy/sell recommendations."

NAVY = "#14183f"
GREEN = "#11854a"
RED = "#b4232a"
GRAY = "#6b7280"
LIGHT_GRAY = "#f8fafc"
DEFAULT_MAX_ARTICLES = 15


def inject_wireframe_css() -> None:
    """Apply the FinPulse wireframe/sketch-inspired visual system."""
    st.markdown(
        f"""
        <style>
        :root {{
            --fp-navy: {NAVY};
            --fp-green: {GREEN};
            --fp-red: {RED};
            --fp-gray: {GRAY};
            --fp-light: {LIGHT_GRAY};
            --fp-border: 1px solid rgba(20, 24, 63, 0.18);
            --fp-border-strong: 1.5px solid rgba(20, 24, 63, 0.7);
            --fp-radius: 18px;
            --fp-radius-sm: 12px;
            --fp-shadow: 0 18px 46px rgba(20, 24, 63, 0.09);
            --fp-shadow-hover: 0 24px 64px rgba(20, 24, 63, 0.13);
            --fp-mono: "SFMono-Regular", "Menlo", "Consolas", monospace;
            --fp-sans: "Inter", "Segoe UI", system-ui, sans-serif;
        }}

        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(17, 133, 74, 0.08), transparent 34rem),
                radial-gradient(circle at top right, rgba(20, 24, 63, 0.08), transparent 30rem),
                linear-gradient(180deg, #ffffff 0%, #fbfcff 52%, #f7f9fd 100%);
            color: var(--fp-navy);
            font-family: var(--fp-sans);
        }}

        .block-container {{
            max-width: 1440px;
            padding-top: 5rem !important;
            padding-bottom: 3.5rem;
        }}

        header[data-testid="stHeader"] {{
            background: rgba(255, 255, 255, 0.96) !important;
            border-bottom: var(--fp-border) !important;
            backdrop-filter: blur(10px) !important;
            height: 3.2rem !important;
            z-index: 999990 !important;
            position: fixed !important;
        }}

        header[data-testid="stHeader"]::before {{
            content: "FinPulse AI – Real-Time Financial News Summarization and Sentiment Analysis";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            font-family: var(--fp-sans);
            font-size: clamp(0.76rem, 1.15vw, 0.88rem);
            font-weight: 650;
            color: var(--fp-navy);
            padding-left: 2.85rem;
            padding-right: 1.5rem;
            white-space: nowrap;
            overflow: visible;
            pointer-events: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2314183f' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='22 7 13.5 15.5 8.5 10.5 2 17'%3E%3C/polyline%3E%3Cpolyline points='16 7 22 7 22 13'%3E%3C/polyline%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: 1rem center;
            background-size: 18px 18px;
            z-index: 1;
        }}

        section[data-testid="stSidebar"] {{
            display: none;
        }}

        .stButton > button,
        .stDownloadButton > button {{
            border: var(--fp-border);
            border-radius: var(--fp-radius);
            background: #ffffff;
            color: var(--fp-navy);
            font-family: var(--fp-mono);
            box-shadow: 0 8px 24px rgba(20, 24, 63, 0.08);
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            transform: translateY(-1px);
            border-color: rgba(20, 24, 63, 0.65);
            box-shadow: 0 14px 32px rgba(20, 24, 63, 0.12);
        }}

        .stTextInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {{
            border: var(--fp-border);
            border-radius: var(--fp-radius-sm);
            background: rgba(255, 255, 255, 0.88);
            color: var(--fp-navy);
            box-shadow: 0 8px 28px rgba(20, 24, 63, 0.07);
            transition: border-color 150ms ease, box-shadow 150ms ease;
        }}

        .stTextInput input:focus,
        .stSelectbox [data-baseweb="select"] > div:focus-within,
        .stMultiSelect [data-baseweb="select"] > div:focus-within {{
            border-color: rgba(17, 133, 74, 0.75);
            box-shadow: 0 0 0 4px rgba(17, 133, 74, 0.11);
        }}

        .fp-slider-label-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 14px;
            margin-bottom: 6px;
        }}

        .fp-slider-val-box {{
            border: var(--fp-border);
            border-radius: 6px;
            background: #ffffff;
            padding: 2px 10px;
            font-family: var(--fp-mono);
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--fp-navy);
            box-shadow: 0 2px 6px rgba(20, 24, 63, 0.04);
        }}

        .fp-metric-card {{
            border: var(--fp-border);
            border-radius: var(--fp-radius-sm);
            padding: 8px 12px;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(20, 24, 63, 0.03);
            min-height: 72px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            margin-top: 8px;
        }}

        .fp-metric-card-title {{
            font-size: 0.74rem;
            font-weight: 700;
            color: var(--fp-navy);
            margin-bottom: 2px;
        }}

        .fp-metric-card-value {{
            font-size: 1.22rem;
            font-weight: 800;
            color: var(--fp-navy);
            font-family: var(--fp-mono);
            letter-spacing: -0.01em;
            margin: 1px 0;
            line-height: 1.2;
        }}

        .fp-metric-card-sub {{
            font-size: 0.68rem;
            color: var(--fp-gray);
            font-family: var(--fp-mono);
            font-weight: 600;
            margin-top: 1px;
        }}

        .fp-about-card {{
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 290px;
            height: 100%;
        }}

        .fp-about-title {{
            font-size: 1.05rem;
            font-weight: 750;
            color: var(--fp-navy);
            margin-bottom: 12px;
        }}

        .fp-about-body {{
            font-size: 0.88rem;
            line-height: 1.55;
            color: #374151;
            margin-bottom: 16px;
            flex: 1;
        }}

        .fp-about-stats-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            padding-top: 14px;
            border-top: 1px solid rgba(20, 24, 63, 0.08);
        }}

        .fp-stat-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }}

        .fp-stat-icon-box {{
            width: 36px;
            height: 36px;
            border-radius: 8px;
            background: rgba(20, 24, 63, 0.04);
            border: 1px solid rgba(20, 24, 63, 0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            color: var(--fp-navy);
        }}

        .fp-stat-icon-box svg {{
            width: 18px;
            height: 18px;
        }}

        .fp-stat-meta {{
            display: flex;
            flex-direction: column;
            min-width: 0;
        }}

        .fp-stat-lbl {{
            font-family: var(--fp-mono);
            font-size: 0.7rem;
            color: var(--fp-gray);
            line-height: 1.2;
        }}

        .fp-stat-val {{
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--fp-navy);
            line-height: 1.3;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .fp-tool-label {{
            margin-bottom: 4px;
            font-family: var(--fp-mono);
            font-size: 0.9rem;
            color: var(--fp-navy);
        }}

        .fp-placeholder-row {{
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 18px;
        }}

        .fp-mini-box {{
            border: var(--fp-border);
            border-radius: var(--fp-radius-sm);
            min-height: 52px;
            padding: 12px 16px;
            font-family: var(--fp-mono);
            font-size: 1.25rem;
            color: var(--fp-navy);
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.88);
            box-shadow: 0 10px 28px rgba(20, 24, 63, 0.07);
        }}

        .fp-card {{
            border: var(--fp-border);
            border-radius: var(--fp-radius);
            padding: 24px;
            background: rgba(255, 255, 255, 0.9);
            margin-bottom: 18px;
            overflow: visible;
            height: auto;
            box-sizing: border-box;
            box-shadow: var(--fp-shadow);
            transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        }}

        .fp-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--fp-shadow-hover);
            border-color: rgba(20, 24, 63, 0.32);
        }}

        .fp-card-title {{
            margin: 0 0 16px;
            font-family: var(--fp-mono);
            font-size: 1rem;
            font-weight: 700;
            letter-spacing: 0;
            color: var(--fp-navy);
        }}

        .fp-small {{
            font-size: 0.88rem;
            color: var(--fp-gray);
        }}

        .fp-signal-row {{
            display: flex;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 14px;
        }}

        .fp-signal-word {{
            font-family: var(--fp-mono);
            font-size: clamp(2rem, 3.2vw, 2.6rem);
            font-weight: 800;
            line-height: 1;
        }}

        .fp-signal-score {{
            font-family: var(--fp-mono);
            font-size: 1rem;
            font-weight: 700;
        }}

        .fp-why-section {{
            border-top: var(--fp-border);
            padding-top: 14px;
        }}

        .fp-why-title {{
            font-family: var(--fp-mono);
            font-weight: 800;
            font-size: 0.95rem;
            margin-bottom: 8px;
            color: var(--fp-navy);
        }}

        .fp-list {{
            margin: 0;
            padding-left: 18px;
            color: var(--fp-navy);
            font-size: 0.92rem;
            line-height: 1.6;
            overflow-wrap: anywhere;
        }}

        .fp-confidence-row {{
            display: grid;
            grid-template-columns: minmax(160px, 0.9fr) 1fr;
            gap: 20px;
            align-items: center;
        }}

        .fp-confidence-number {{
            font-family: var(--fp-mono);
            font-size: 2.7rem;
            font-weight: 800;
            line-height: 1;
        }}

        .fp-confidence-label {{
            margin-top: 8px;
            font-family: var(--fp-mono);
            font-size: 1rem;
        }}

        .fp-factor-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
        }}

        .fp-factor-col {{
            min-height: 120px;
        }}

        .fp-factor-col + .fp-factor-col {{
            border-left: var(--fp-border);
            padding-left: 18px;
        }}

        .fp-factor-item {{
            margin: 0 0 11px;
            font-size: 0.95rem;
            line-height: 1.35;
        }}

        .fp-backtest-note {{
            border-top: var(--fp-border);
            margin-top: 14px;
            padding-top: 14px;
            font-size: 0.92rem;
            line-height: 1.45;
            color: var(--fp-gray);
        }}

        .fp-backtest-metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            border-top: var(--fp-border);
            margin-top: 14px;
        }}

        .fp-backtest-metric {{
            padding: 14px 12px 4px;
            border-right: var(--fp-border);
        }}

        .fp-backtest-metric:last-child {{
            border-right: none;
        }}

        .fp-metric-label {{
            font-family: var(--fp-mono);
            font-size: 0.76rem;
            color: var(--fp-gray);
        }}

        .fp-metric-value {{
            margin-top: 8px;
            font-family: var(--fp-mono);
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--fp-navy);
        }}

        .fp-feed-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(20, 24, 63, 0.1);
        }}

        .fp-feed-title-wrap {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .fp-bolt-icon {{
            width: 17px;
            height: 17px;
            color: var(--fp-navy);
            flex-shrink: 0;
        }}

        .fp-feed-title {{
            font-family: var(--fp-mono);
            font-size: 0.98rem;
            font-weight: 750;
            color: var(--fp-navy);
            letter-spacing: -0.01em;
        }}

        .fp-view-all {{
            font-family: var(--fp-mono);
            font-size: 0.8rem;
            font-weight: 600;
            color: rgba(20, 24, 63, 0.75);
            text-decoration: none;
            transition: color 150ms ease;
        }}

        .fp-view-all:hover {{
            color: var(--fp-navy);
            text-decoration: underline;
        }}

        .fp-feed-list {{
            display: flex;
            flex-direction: column;
        }}

        .fp-feed-item-row {{
            display: flex;
            align-items: flex-start;
            gap: 14px;
            padding: 12px 0;
            border-bottom: 1px solid rgba(20, 24, 63, 0.08);
        }}

        .fp-feed-item-row:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}

        .fp-feed-item-row:first-child {{
            padding-top: 0;
        }}

        .fp-feed-time {{
            font-family: var(--fp-mono);
            font-size: 0.8rem;
            color: var(--fp-gray);
            flex-shrink: 0;
            min-width: 52px;
            padding-top: 1px;
        }}

        .fp-feed-content {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
            flex: 1;
            min-width: 0;
        }}

        .fp-feed-headline-link {{
            color: var(--fp-navy);
            font-size: 0.92rem;
            font-weight: 700;
            line-height: 1.4;
            text-decoration: none;
            overflow-wrap: anywhere;
            transition: opacity 150ms ease;
        }}

        .fp-feed-headline-link:hover {{
            opacity: 0.75;
            text-decoration: underline;
        }}

        .fp-feed-headline-text {{
            color: var(--fp-navy);
            font-size: 0.92rem;
            font-weight: 700;
            line-height: 1.4;
            overflow-wrap: anywhere;
        }}

        .fp-pill {{
            display: inline-flex;
            align-items: center;
            padding: 2px 10px;
            border-radius: 9999px;
            font-family: var(--fp-mono);
            font-size: 0.72rem;
            font-weight: 700;
            line-height: 1.3;
        }}

        .fp-pill-positive {{
            background: #dcfce7;
            color: #15803d;
            border: 1px solid rgba(21, 128, 61, 0.2);
        }}

        .fp-pill-negative {{
            background: #fee2e2;
            color: #b91c1c;
            border: 1px solid rgba(185, 28, 28, 0.2);
        }}

        .fp-pill-neutral {{
            background: #f1f5f9;
            color: #475569;
            border: 1px solid rgba(71, 85, 105, 0.2);
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border: var(--fp-border);
            border-radius: var(--fp-radius);
            padding: 24px;
            background: rgba(255, 255, 255, 0.9);
            overflow: visible;
            box-shadow: var(--fp-shadow);
            margin-bottom: 18px;
            box-sizing: border-box;
            transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
            transform: translateY(-2px);
            box-shadow: var(--fp-shadow-hover);
            border-color: rgba(20, 24, 63, 0.32);
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] .fp-card {{
            border: none;
            padding: 0;
            margin-bottom: 0;
            box-shadow: none;
            background: transparent;
        }}

        div[data-testid="stPlotlyChart"] {{
            overflow: visible;
        }}

        .fp-status-strip {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 8px 0 22px;
        }}

        .fp-chip {{
            border: var(--fp-border);
            border-radius: 999px;
            background: rgba(255,255,255,0.78);
            padding: 7px 12px;
            color: rgba(20, 24, 63, 0.74);
            font-family: var(--fp-mono);
            font-size: 0.78rem;
            box-shadow: 0 8px 20px rgba(20,24,63,0.05);
        }}

        .stSlider {{
            padding-bottom: 4px;
        }}

        .stSlider label p {{
            font-family: var(--fp-mono) !important;
            font-size: 0.74rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            color: var(--fp-navy) !important;
            font-weight: 700 !important;
            margin-bottom: 2px !important;
        }}

        .fp-card-header-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 12px;
        }}

        .fp-card-title-wrap {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .fp-card-icon {{
            width: 17px;
            height: 17px;
            color: var(--fp-navy);
            flex-shrink: 0;
        }}

        .fp-card-title-text {{
            font-family: var(--fp-mono);
            font-size: 0.98rem;
            font-weight: 750;
            color: var(--fp-navy);
            letter-spacing: -0.01em;
        }}

        .fp-summary-headline {{
            font-size: 0.96rem;
            font-weight: 700;
            color: var(--fp-navy);
            line-height: 1.42;
            margin-bottom: 8px;
        }}

        .fp-summary-body {{
            font-size: 0.89rem;
            line-height: 1.55;
            color: rgba(20, 24, 63, 0.85);
        }}

        .fp-company-summary {{
            font-size: 0.88rem;
            line-height: 1.55;
            color: rgba(20, 24, 63, 0.85);
            margin-bottom: 14px;
        }}

        .fp-stat-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            border-top: 1px solid rgba(20, 24, 63, 0.1);
            padding-top: 12px;
        }}

        .fp-stat-box {{
            background: rgba(20, 24, 63, 0.03);
            border: 1px solid rgba(20, 24, 63, 0.08);
            border-radius: var(--fp-radius-sm);
            padding: 9px 12px;
        }}

        .fp-stat-label {{
            font-family: var(--fp-mono);
            font-size: 0.72rem;
            color: var(--fp-gray);
            margin-bottom: 3px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .fp-stat-value {{
            font-family: var(--fp-mono);
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--fp-navy);
            overflow-wrap: anywhere;
        }}

        .fp-green {{ color: var(--fp-green); }}
        .fp-red {{ color: var(--fp-red); }}
        .fp-gray {{ color: var(--fp-gray); }}

        @media (max-width: 1050px) {{
            .fp-header {{
                grid-template-columns: 1fr;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


LOGGER = logging.getLogger("finpulse")

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
    """Generate prioritized candidate tickers for corporate demergers, renames, and exchange fallbacks."""
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


def _fetch_raw_ticker_info(ticker: str, retries: int = 2) -> tuple[dict, object]:
    """Fetch raw ticker metadata and fast_info with candidate resolution, retries, and logging."""
    import time
    import yfinance as yf

    candidates = _get_ticker_candidates(ticker)
    last_error: Exception | None = None

    for candidate in candidates:
        for attempt in range(retries + 1):
            try:
                t = yf.Ticker(candidate)
                info = t.info
                if isinstance(info, dict) and (
                    info.get("longBusinessSummary")
                    or info.get("marketCap")
                    or info.get("currentPrice")
                    or info.get("regularMarketPrice")
                    or info.get("shortName")
                    or info.get("sector")
                ):
                    return info, t.fast_info

                try:
                    fi = t.fast_info
                    if fi and getattr(fi, "last_price", None) is not None:
                        return (info if isinstance(info, dict) else {}), fi
                except Exception:
                    pass

                # If info is empty without error, move immediately to next candidate
                break
            except Exception as exc:
                last_error = exc
                err_msg = str(exc).lower()
                is_not_found = any(k in err_msg for k in ("404", "not found", "delisted", "currenttradingperiod"))
                LOGGER.warning(
                    "yfinance lookup for %s (attempt %d/%d) failed: %s",
                    candidate,
                    attempt + 1,
                    retries + 1,
                    exc,
                )
                if is_not_found or attempt >= retries:
                    break
                time.sleep(0.3 * (attempt + 1))

    if last_error:
        LOGGER.error("All candidate lookups failed for %s (tried %s): %s", ticker, candidates, last_error)
    else:
        LOGGER.warning("No rich yfinance data returned for %s across candidates %s", ticker, candidates)

    return {}, None


def _format_market_cap(value: object) -> str:
    if not isinstance(value, (int, float)) or pd.isna(value) or value <= 0:
        return "---"
    if value >= 1_000_000_000_000:
        return f"₹{value / 1_000_000_000_000:.2f}T"
    if value >= 10_000_000_000:
        return f"₹{value / 10_000_000_000:.2f}B"
    if value >= 10_000_000:
        return f"₹{value / 10_000_000:.2f}Cr"
    return f"₹{value:,.0f}"


def _market_cap_category(value: object) -> str:
    if not isinstance(value, (int, float)) or pd.isna(value) or value <= 0:
        return "---"
    if value >= 200_000_000_000:  # >= ₹20,000 Cr
        return "Large Cap"
    if value >= 50_000_000_000:   # >= ₹5,000 Cr
        return "Mid Cap"
    return "Small Cap"


def _format_price(value: object) -> str:
    if not isinstance(value, (int, float)) or pd.isna(value) or value <= 0:
        return "---"
    return f"₹{value:,.2f}"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_snapshot(ticker: str | None) -> dict[str, object]:
    """Fetch lightweight market snapshot fields with multi-layer key fallbacks and fast_info."""
    if not ticker:
        return {
            "market_cap": "---",
            "market_cap_category": "---",
            "current_price": "---",
            "ticker_label": "---",
        }

    info, fast_info = _fetch_raw_ticker_info(ticker)
    raw_symbol = ticker.replace(".NS", "").replace(".BO", "").strip()

    # 1. Market cap resolution: info.marketCap -> fast_info.market_cap -> info.enterpriseValue
    market_cap = info.get("marketCap")
    if (not market_cap or pd.isna(market_cap)) and fast_info is not None:
        try:
            market_cap = fast_info.market_cap
        except Exception:
            pass
    if not market_cap or pd.isna(market_cap):
        market_cap = info.get("enterpriseValue")

    # 2. Current price resolution: currentPrice -> regularMarketPrice -> fast_info.last_price -> previousClose -> fast_info.previous_close -> open -> dayHigh
    current_price = info.get("currentPrice")
    if not current_price or pd.isna(current_price):
        current_price = info.get("regularMarketPrice")
    if (not current_price or pd.isna(current_price)) and fast_info is not None:
        try:
            current_price = fast_info.last_price
        except Exception:
            pass
    if not current_price or pd.isna(current_price):
        current_price = info.get("previousClose")
    if (not current_price or pd.isna(current_price)) and fast_info is not None:
        try:
            current_price = fast_info.previous_close or getattr(fast_info, "regular_market_previous_close", None)
        except Exception:
            pass
    if not current_price or pd.isna(current_price):
        current_price = info.get("open") or info.get("dayHigh") or info.get("bid") or info.get("ask")

    return {
        "market_cap": _format_market_cap(market_cap),
        "market_cap_category": _market_cap_category(market_cap),
        "current_price": _format_price(current_price),
        "ticker_label": f"NSE: {raw_symbol}" if raw_symbol else "---",
    }


def _truncate_company_summary(text: str, max_chars: int = 450, max_sentences: int = 4) -> str:
    """Truncate company summary to a maximum of 3-5 sentences or roughly 400-500 chars at sentence boundaries with ellipsis."""
    raw = str(text or "").strip()
    if not raw:
        return "Company profile summary not available."

    import re
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw.replace("\n", " ")) if s.strip()]
    if not sentences:
        return (raw[:max_chars].rstrip() + "...") if len(raw) > max_chars else raw

    selected: list[str] = []
    current_length = 0
    was_truncated = False

    for sentence in sentences[:max_sentences]:
        addition_len = len(sentence) + (1 if selected else 0)
        if current_length + addition_len > max_chars and selected:
            was_truncated = True
            break
        selected.append(sentence)
        current_length += addition_len

    if len(sentences) > len(selected):
        was_truncated = True

    result = " ".join(selected).strip()
    if was_truncated:
        if not result.endswith("..."):
            result = result.rstrip(".!?") + "..."
    elif not result.endswith((".", "!", "?")):
        result += "."

    return result


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_profile(ticker: str) -> dict[str, str]:
    """Fetch company profile and metadata from yfinance with graceful multi-key fallbacks."""
    info, _ = _fetch_raw_ticker_info(ticker)

    # 1. Summary fallbacks
    raw_summary = (
        info.get("longBusinessSummary")
        or info.get("description")
        or info.get("summaryProfile")
        or info.get("shortDescription")
        or ""
    )
    if not str(raw_summary).strip():
        comp_name = info.get("longName") or info.get("shortName") or ticker.replace(".NS", "").replace(".BO", "")
        sector = info.get("sector") or info.get("industry")
        if sector:
            raw_summary = f"{comp_name} is a leading publicly listed company operating in the {sector} sector in India."
        else:
            raw_summary = f"{comp_name} is a publicly listed enterprise on the National Stock Exchange of India (NSE)."
    summary = _truncate_company_summary(str(raw_summary).strip())

    # 2. Industry fallbacks: industry -> sector -> industryDisp -> industryKey -> category
    industry = (
        info.get("industry")
        or info.get("sector")
        or info.get("industryDisp")
        or info.get("industryKey")
        or info.get("category")
        or "Not available"
    )
    industry = str(industry).strip()

    # 3. Founded fallbacks: founded -> yearFounded -> startDate
    founded = info.get("founded") or info.get("yearFounded") or info.get("startDate")
    if founded and str(founded).strip() and str(founded).strip() != "None":
        founded_str = str(founded).strip()
    else:
        founded_str = "Not available"

    # 4. Headquarters fallbacks: city, country, state, address1
    city = info.get("city")
    country = info.get("country")
    state = info.get("state")
    if city and country:
        headquarters = f"{city}, {country}"
    elif city and state:
        headquarters = f"{city}, {state}"
    elif city:
        headquarters = str(city)
    elif country:
        headquarters = str(country)
    elif info.get("address1"):
        headquarters = str(info.get("address1"))
    else:
        headquarters = "Not available"

    # 5. Employees fallbacks: fullTimeEmployees -> employees -> totalEmployees
    employees = info.get("fullTimeEmployees") or info.get("employees") or info.get("totalEmployees")
    if isinstance(employees, (int, float)) and not pd.isna(employees) and employees > 0:
        employees_str = f"{int(employees):,}"
    else:
        employees_str = "Not available"

    return {
        "summary": summary,
        "industry": industry,
        "founded": founded_str,
        "headquarters": headquarters,
        "employees": employees_str,
    }


def _render_about_company_card(ticker: str | None) -> None:
    if not ticker:
        card_html = (
            '<div class="fp-card fp-about-card">'
            '<div class="fp-about-title">About the Company</div>'
            '<div class="fp-about-body" style="color: var(--fp-gray);">'
            'Select a stock from the search dropdown to view company profile, leadership, and operational details.'
            '</div>'
            '<div class="fp-about-stats-row">'
            '<div class="fp-stat-item"><div class="fp-stat-icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"></rect><path d="M9 22v-4h6v4"></path></svg></div><div class="fp-stat-meta"><div class="fp-stat-lbl">Industry</div><div class="fp-stat-val">---</div></div></div>'
            '<div class="fp-stat-item"><div class="fp-stat-icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg></div><div class="fp-stat-meta"><div class="fp-stat-lbl">Founded</div><div class="fp-stat-val">---</div></div></div>'
            '<div class="fp-stat-item"><div class="fp-stat-icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg></div><div class="fp-stat-meta"><div class="fp-stat-lbl">Headquarters</div><div class="fp-stat-val">---</div></div></div>'
            '<div class="fp-stat-item"><div class="fp-stat-icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg></div><div class="fp-stat-meta"><div class="fp-stat-lbl">Employees</div><div class="fp-stat-val">---</div></div></div>'
            '</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
        return

    profile = fetch_company_profile(ticker)
    summary = escape(profile["summary"])
    industry = escape(profile["industry"])
    founded = escape(profile["founded"])
    headquarters = escape(profile["headquarters"])
    employees = escape(profile["employees"])

    card_html = (
        '<div class="fp-card fp-about-card">'
        '<div class="fp-about-title">About the Company</div>'
        f'<div class="fp-about-body">{summary}</div>'
        '<div class="fp-about-stats-row">'
        '<div class="fp-stat-item">'
        '<div class="fp-stat-icon-box">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><path d="M9 22v-4h6v4"></path><path d="M8 6h.01"></path><path d="M16 6h.01"></path><path d="M8 10h.01"></path><path d="M16 10h.01"></path><path d="M8 14h.01"></path><path d="M16 14h.01"></path></svg>'
        '</div>'
        f'<div class="fp-stat-meta"><div class="fp-stat-lbl">Industry</div><div class="fp-stat-val">{industry}</div></div>'
        '</div>'
        '<div class="fp-stat-item">'
        '<div class="fp-stat-icon-box">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>'
        '</div>'
        f'<div class="fp-stat-meta"><div class="fp-stat-lbl">Founded</div><div class="fp-stat-val">{founded}</div></div>'
        '</div>'
        '<div class="fp-stat-item">'
        '<div class="fp-stat-icon-box">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>'
        '</div>'
        f'<div class="fp-stat-meta"><div class="fp-stat-lbl">Headquarters</div><div class="fp-stat-val">{headquarters}</div></div>'
        '</div>'
        '<div class="fp-stat-item">'
        '<div class="fp-stat-icon-box">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>'
        '</div>'
        f'<div class="fp-stat-meta"><div class="fp-stat-lbl">Employees</div><div class="fp-stat-val">{employees}</div></div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_controls() -> tuple[str | None, str | None]:
    """Render the top control and company information section matching the reference design."""
    left_col, right_col = st.columns([1, 1.25], vertical_alignment="top")

    with left_col:
        st.markdown('<div class="fp-tool-label">Search Stock</div>', unsafe_allow_html=True)
        company_names = sorted(list(NSE_COMPANIES.keys()))
        active_company = st.selectbox(
            "Search Stock",
            company_names,
            index=None,
            placeholder="Search company (e.g. Reliance, TCS, Zomato)...",
            label_visibility="collapsed",
            key="header_stock_search",
        )
        active_ticker = NSE_COMPANIES.get(active_company) if active_company else None

        market_snapshot = fetch_market_snapshot(active_ticker)
        mcap_col, price_col = st.columns([1, 1])
        with mcap_col:
            mcap_html = (
                '<div class="fp-metric-card">'
                '<div class="fp-metric-card-title">Market Cap</div>'
                f'<div class="fp-metric-card-value">{escape(str(market_snapshot["market_cap"]))}</div>'
                f'<div class="fp-metric-card-sub">{escape(str(market_snapshot["market_cap_category"]))}</div>'
                '</div>'
            )
            st.markdown(mcap_html, unsafe_allow_html=True)

        with price_col:
            price_html = (
                '<div class="fp-metric-card">'
                '<div class="fp-metric-card-title">Current Stock Price</div>'
                f'<div class="fp-metric-card-value">{escape(str(market_snapshot["current_price"]))}</div>'
                f'<div class="fp-metric-card-sub">{escape(str(market_snapshot["ticker_label"]))}</div>'
                '</div>'
            )
            st.markdown(price_html, unsafe_allow_html=True)

    with right_col:
        _render_about_company_card(active_ticker)

    return active_company, active_ticker


@st.cache_resource(show_spinner=False)
def cached_summarizer():
    return load_summarizer()


@st.cache_resource(show_spinner=False)
def cached_finbert():
    return load_finbert()


@st.cache_data(ttl=1800, show_spinner=True)
def cached_pipeline(tickers: tuple[str, ...], max_articles: int):
    """Run the data pipeline and cache results for Streamlit interactions."""
    cached_summarizer()
    cached_finbert()
    news_df = fetch_news_for_tickers(tickers, max_articles_per_ticker=max_articles)
    summarized_df = add_summaries(news_df)
    scored_df = add_sentiment_scores(summarized_df)
    explained_df = add_explainability(scored_df)
    signals_df = generate_stock_signals(explained_df)
    backtest_summary_df, backtest_events_df = run_backtest(
        explained_df,
        tickers,
        BacktestConfig(),
    )
    return explained_df, signals_df, backtest_summary_df, backtest_events_df


def _format_phrases(phrases: object) -> str:
    if isinstance(phrases, list):
        return "; ".join(phrases)
    return str(phrases or "")


def _export_frame(articles_df: pd.DataFrame, signals_df: pd.DataFrame) -> pd.DataFrame:
    if articles_df.empty:
        return pd.DataFrame()
    joined = articles_df.merge(
        signals_df[["ticker", "aggregate_score", "signal", "confidence"]],
        on="ticker",
        how="left",
    )
    export = joined.copy()
    export["contributing_phrases"] = export["contributing_phrases"].apply(_format_phrases)
    return export


def _signal_class(signal: object) -> str:
    signal_text = str(signal or "Neutral").lower()
    if signal_text == "bullish":
        return "fp-green"
    if signal_text == "bearish":
        return "fp-red"
    return "fp-gray"


def _sentiment_class(label: object) -> str:
    label_text = str(label or "neutral").lower()
    if label_text == "positive":
        return "fp-green"
    if label_text == "negative":
        return "fp-red"
    return "fp-gray"


def _confidence_level(confidence_text: object) -> str:
    text = str(confidence_text or "")
    for level in ("High", "Medium", "Low"):
        if level.lower() in text.lower():
            return f"{level} Confidence"
    return "Low Confidence"


def _confidence_percent(signal_row: pd.Series | None) -> int:
    if signal_row is None:
        return 0
    article_count = int(signal_row.get("article_count", 0) or 0)
    agreement_count = int(signal_row.get("agreement_count", 0) or 0)
    if article_count <= 0:
        return 0
    return round((agreement_count / article_count) * 100)


def _recommendation_reasons(signal_row: pd.Series, stock_articles: pd.DataFrame) -> list[str]:
    article_count = int(signal_row.get("article_count", len(stock_articles)) or 0)
    agreement_count = int(signal_row.get("agreement_count", 0) or 0)
    aggregate_score = float(signal_row.get("aggregate_score", 0.0) or 0.0)
    confidence_text = str(signal_row.get("confidence", "Low Confidence"))
    return [
        f"{article_count} recent articles analyzed for this ticker",
        f"{agreement_count}/{article_count} articles align with the aggregate direction",
        f"{_confidence_level(confidence_text)} based on article agreement",
        f"Aggregate sentiment score: {aggregate_score:+.2f}",
    ]


def _top_headline_themes(article_subset: pd.DataFrame, max_items: int = 3) -> list[str]:
    themes: list[str] = []
    for _, article in article_subset.head(max_items).iterrows():
        phrases = article.get("contributing_phrases", [])
        if isinstance(phrases, list) and phrases:
            themes.append(str(phrases[0])[:90])
        else:
            themes.append(str(article.get("headline", "Article theme"))[:90])
    return themes


def _key_factors(stock_articles: pd.DataFrame) -> tuple[list[str], list[str]]:
    sentiment_counts = stock_articles["sentiment_label"].astype(str).str.lower().value_counts()
    positive_count = int(sentiment_counts.get("positive", 0))
    negative_count = int(sentiment_counts.get("negative", 0))
    neutral_count = int(sentiment_counts.get("neutral", 0))

    positive_factors = [f"{positive_count} positive article{'s' if positive_count != 1 else ''}"]
    negative_factors = [f"{negative_count} negative/risk article{'s' if negative_count != 1 else ''}"]

    positive_factors.extend(_top_headline_themes(stock_articles[stock_articles["sentiment_label"].astype(str).str.lower() == "positive"], 2))
    negative_factors.extend(_top_headline_themes(stock_articles[stock_articles["sentiment_label"].astype(str).str.lower() == "negative"], 2))

    if neutral_count:
        positive_factors.append(f"{neutral_count} neutral items temper the signal")

    return positive_factors[:4], negative_factors[:4]


def _render_recommendation_card(signal_row: pd.Series | None, stock_articles: pd.DataFrame) -> None:
    if signal_row is None:
        st.markdown(
            '<div class="fp-card"><div class="fp-card-title">RECOMMENDATION</div><div class="fp-small">No signal available for this stock.</div></div>',
            unsafe_allow_html=True,
        )
        return

    signal = str(signal_row.get("signal", "Neutral")).upper()
    score = float(signal_row.get("aggregate_score", 0.0) or 0.0)
    reasons = _recommendation_reasons(signal_row, stock_articles)
    reason_items = "".join(f"<li>{escape(reason)}</li>" for reason in reasons)
    color_class = _signal_class(signal)
    rec_html = (
        '<div class="fp-card">'
        '<div class="fp-card-title">RECOMMENDATION</div>'
        '<div class="fp-signal-row">'
        f'<span class="fp-signal-word {color_class}">{escape(signal)}</span>'
        f'<span class="fp-signal-score {color_class}">Score {score:+.2f}</span>'
        '</div>'
        '<div class="fp-why-section">'
        '<div class="fp-why-title">WHY?</div>'
        f'<ul class="fp-list">{reason_items}</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(rec_html, unsafe_allow_html=True)


def _confidence_gauge(percent: int, color: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=percent,
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": color, "thickness": 0.22},
                "bgcolor": "white",
                "bordercolor": NAVY,
                "borderwidth": 1,
                "steps": [
                    {"range": [0, 40], "color": "#f3d9dc"},
                    {"range": [40, 70], "color": "#eef0f5"},
                    {"range": [70, 100], "color": "#d9f0e3"},
                ],
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(
        height=130,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=NAVY, family="Menlo, Consolas, monospace"),
    )
    return fig


def _render_confidence_card(signal_row: pd.Series | None) -> None:
    percent = _confidence_percent(signal_row)
    confidence_label = _confidence_level(signal_row.get("confidence", "") if signal_row is not None else "")
    color = GREEN if "High" in confidence_label else NAVY if "Medium" in confidence_label else GRAY

    with st.container(border=True):
        st.markdown('<div class="fp-card-title">CONFIDENCE LEVEL</div>', unsafe_allow_html=True)
        gauge_col, number_col = st.columns([1, 1], vertical_alignment="center")
        with gauge_col:
            st.plotly_chart(_confidence_gauge(percent, color), width="stretch", config={"displayModeBar": False})
        with number_col:
            num_html = (
                f'<div class="fp-confidence-number" style="color:{color};">{percent}%</div>'
                f'<div class="fp-confidence-label" style="color:{color};">{escape(confidence_label)}</div>'
            )
            st.markdown(num_html, unsafe_allow_html=True)


def _render_key_factors_card(stock_articles: pd.DataFrame) -> None:
    positive_factors, negative_factors = _key_factors(stock_articles)
    positive_html = "".join(f'<p class="fp-factor-item fp-green">+ {escape(factor)}</p>' for factor in positive_factors)
    negative_html = "".join(f'<p class="fp-factor-item fp-red">- {escape(factor)}</p>' for factor in negative_factors)
    factors_html = (
        '<div class="fp-card">'
        '<div class="fp-card-title">KEY FACTORS</div>'
        '<div class="fp-factor-grid">'
        f'<div class="fp-factor-col">{positive_html}</div>'
        f'<div class="fp-factor-col">{negative_html}</div>'
        '</div>'
        '</div>'
    )
    st.markdown(factors_html, unsafe_allow_html=True)


def _backtest_chart(stock_backtest: pd.DataFrame) -> go.Figure:
    chart_df = stock_backtest.melt(
        id_vars=["ticker", "events"],
        value_vars=[
            "sentiment_signal_hit_rate",
            "random_baseline_hit_rate",
            "naive_baseline_hit_rate",
        ],
        var_name="method",
        value_name="hit_rate",
    )
    chart_df["method"] = chart_df["method"].map(
        {
            "sentiment_signal_hit_rate": "Sentiment Signal",
            "random_baseline_hit_rate": "Random Baseline",
            "naive_baseline_hit_rate": "Naive Baseline",
        }
    )
    fig = px.bar(
        chart_df,
        x="method",
        y="hit_rate",
        text="hit_rate",
        range_y=[0, 100],
        labels={"hit_rate": "Hit rate (%)", "method": ""},
        color="method",
        color_discrete_map={
            "Sentiment Signal": GREEN,
            "Random Baseline": GRAY,
            "Naive Baseline": NAVY,
        },
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_color=NAVY, marker_line_width=1)
    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=14, b=6),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=NAVY, family="Menlo, Consolas, monospace"),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=NAVY),
        yaxis=dict(gridcolor="#e6e8ef", zeroline=False, ticksuffix="%"),
    )
    return fig


def _render_backtest_card(stock_backtest: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown('<div class="fp-card-title">BACKTEST PERFORMANCE</div>', unsafe_allow_html=True)
        if stock_backtest.empty:
            st.markdown(
                '<div class="fp-backtest-note">No eligible 90-day news events with 3-day forward prices. This is common with fresh news feeds, and no backtest numbers are fabricated.</div>',
                unsafe_allow_html=True,
            )
        else:
            row = stock_backtest.iloc[0]
            st.plotly_chart(_backtest_chart(stock_backtest), width="stretch", config={"displayModeBar": False})
            metrics_html = (
                '<div class="fp-backtest-metrics">'
                '<div class="fp-backtest-metric">'
                '<div class="fp-metric-label">Signal Hit Rate</div>'
                f'<div class="fp-metric-value fp-green">{float(row["sentiment_signal_hit_rate"]):.1f}%</div>'
                '</div>'
                '<div class="fp-backtest-metric">'
                '<div class="fp-metric-label">Random Baseline</div>'
                f'<div class="fp-metric-value">{float(row["random_baseline_hit_rate"]):.1f}%</div>'
                '</div>'
                '<div class="fp-backtest-metric">'
                '<div class="fp-metric-label">Naive Baseline</div>'
                f'<div class="fp-metric-value">{float(row["naive_baseline_hit_rate"]):.1f}%</div>'
                '</div>'
                '</div>'
                f'<div class="fp-backtest-note">Events tested: {int(row["events"])}. Directional hit-rate only; no P&amp;L or portfolio simulation.</div>'
            )
            st.markdown(metrics_html, unsafe_allow_html=True)


def _format_relative_time(value: object) -> str:
    """Calculate relative time string (e.g. '2h ago', '1d ago') from timestamp."""
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
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


def _sentiment_pill_class(label: object) -> tuple[str, str]:
    text = str(label or "neutral").strip().lower()
    if text == "positive":
        return "fp-pill-positive", "Positive"
    if text == "negative":
        return "fp-pill-negative", "Negative"
    return "fp-pill-neutral", "Neutral"


def _render_live_feed_card(stock_articles: pd.DataFrame, stock: str) -> None:
    bolt_svg = (
        '<svg class="fp-bolt-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>'
        '</svg>'
    )
    if stock_articles.empty:
        st.markdown(
            '<div class="fp-card">'
            '<div class="fp-feed-header">'
            f'<div class="fp-feed-title-wrap">{bolt_svg}<span class="fp-feed-title">Live News Feed</span></div>'
            '<span class="fp-view-all">View All &rarr;</span>'
            '</div>'
            '<div class="fp-small">No live news articles available for this ticker.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    articles_html: list[str] = []
    for _, article in stock_articles.iterrows():
        pill_class, pill_text = _sentiment_pill_class(article.get("sentiment_label"))
        headline = escape(str(article.get("headline", "Untitled")))
        rel_time = escape(_format_relative_time(article.get("published_date")))
        source_url = str(article.get("source_url", "") or "").strip()
        headline_html = (
            f'<a href="{escape(source_url)}" target="_blank" rel="noopener noreferrer" class="fp-feed-headline-link">{headline}</a>'
            if source_url
            else f'<span class="fp-feed-headline-text">{headline}</span>'
        )
        item_html = (
            '<div class="fp-feed-item-row">'
            f'<div class="fp-feed-time">{rel_time}</div>'
            '<div class="fp-feed-content">'
            f'{headline_html}'
            f'<span class="fp-pill {pill_class}">{pill_text}</span>'
            '</div>'
            '</div>'
        )
        articles_html.append(item_html)

    all_articles_html = "".join(articles_html)
    full_card_html = (
        '<div class="fp-card">'
        '<div class="fp-feed-header">'
        f'<div class="fp-feed-title-wrap">{bolt_svg}<span class="fp-feed-title">Live News Feed</span></div>'
        '<a href="#" class="fp-view-all">View All &rarr;</a>'
        '</div>'
        f'<div class="fp-feed-list">{all_articles_html}</div>'
        '</div>'
    )
    st.markdown(full_card_html, unsafe_allow_html=True)


def _render_real_time_news_summary_card(
    stock_articles: pd.DataFrame,
    signal_row: pd.Series | None,
) -> None:
    newspaper_svg = (
        '<svg class="fp-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>'
        '<path d="M18 14h-8"/>'
        '<path d="M15 18h-5"/>'
        '<path d="M10 6h8v4h-8V6Z"/>'
        '</svg>'
    )
    if signal_row is not None:
        raw_signal = str(signal_row.get("signal", "Neutral")).strip()
        signal_word = raw_signal.capitalize()
        confidence_pct = _confidence_percent(signal_row)
        pill_text = f"{signal_word} &bull; {confidence_pct}%"
        if raw_signal.lower() in ("bullish", "positive"):
            pill_class = "fp-pill-positive"
        elif raw_signal.lower() in ("bearish", "negative"):
            pill_class = "fp-pill-negative"
        else:
            pill_class = "fp-pill-neutral"
    else:
        pill_text = "Neutral &bull; 0%"
        pill_class = "fp-pill-neutral"

    if stock_articles.empty:
        content_html = '<div class="fp-small">No news articles available for this ticker.</div>'
    else:
        top_article = stock_articles.iloc[0]
        top_headline = escape(str(top_article.get("headline", "Latest Market News")))
        top_summary = escape(str(top_article.get("summary") or top_article.get("snippet") or "No summary available."))
        content_html = (
            f'<div class="fp-summary-headline">{top_headline}</div>'
            f'<div class="fp-summary-body">{top_summary}</div>'
        )

    card_html = (
        '<div class="fp-card">'
        '<div class="fp-card-header-row">'
        f'<div class="fp-card-title-wrap">{newspaper_svg}<span class="fp-card-title-text">Real-Time News Summary</span></div>'
        f'<span class="fp-pill {pill_class}">{pill_text}</span>'
        '</div>'
        f'{content_html}'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


st.set_page_config(
    page_title="FinPulse AI – Real-Time Financial News Summarization and Sentiment Analysis",
    layout="wide",
)
inject_wireframe_css()

selected_company, stock = render_controls()

if not selected_company or not stock:
    empty_prompt_html = (
        '<div class="fp-card" style="text-align: center; padding: 48px 24px; margin-top: 16px;">'
        '<div style="font-family: var(--fp-mono); font-size: 1.3rem; font-weight: 700; color: var(--fp-navy); margin-bottom: 8px;">'
        'Search and select a stock to begin'
        '</div>'
        '<div class="fp-small" style="font-size: 0.95rem; max-width: 620px; margin: 0 auto;">'
        'Choose any NSE company from the search dropdown above to analyze real-time financial news, generate FinBERT sentiment signals, and view backtest performance.'
        '</div>'
        '</div>'
    )
    st.markdown(empty_prompt_html, unsafe_allow_html=True)
    st.caption(DISCLAIMER)
    st.stop()
else:
    selected_tickers = [stock]
    status_html = (
        '<div class="fp-status-strip">'
        f'<span class="fp-chip">{escape(str(selected_company))} · {escape(str(stock))}</span>'
        f'<span class="fp-chip">{DEFAULT_MAX_ARTICLES} article window</span>'
        '<span class="fp-chip">Decision-support only</span>'
        '</div>'
    )
    st.markdown(status_html, unsafe_allow_html=True)
    st.caption(DISCLAIMER)

    articles_df, signals_df, backtest_summary_df, backtest_events_df = cached_pipeline(
        tuple(selected_tickers),
        DEFAULT_MAX_ARTICLES,
    )

    if articles_df.empty:
        st.error("No yfinance news articles were available for the selected stocks.")
        st.stop()

    stock_articles = articles_df[articles_df["ticker"] == stock].sort_values("published_date", ascending=False)
    stock_signal = signals_df[signals_df["ticker"] == stock]
    stock_backtest = backtest_summary_df[backtest_summary_df["ticker"] == stock]
    signal_row = None if stock_signal.empty else stock_signal.iloc[0]

    left, middle, right = st.columns([0.95, 1.08, 1.05], vertical_alignment="top")

    with left:
        _render_recommendation_card(signal_row, stock_articles)
        _render_confidence_card(signal_row)
        _render_key_factors_card(stock_articles)

    with middle:
        _render_real_time_news_summary_card(stock_articles, signal_row)
        _render_backtest_card(stock_backtest)
        export_df = _export_frame(articles_df, signals_df)
        st.download_button(
            "Export summaries + signals CSV",
            data=export_df.to_csv(index=False),
            file_name=f"finpulse_export_{datetime.now().date().isoformat()}.csv",
            mime="text/csv",
            width="stretch",
            disabled=export_df.empty,
        )

    with right:
        _render_live_feed_card(stock_articles, stock)
