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


BULLISH_THRESHOLD = 0.20
BEARISH_THRESHOLD = -0.20


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


TICKER_ALIASES: dict[str, list[str]] = {
    "TATAMOTORS.NS": ["TATAMOTORS.NS", "TMCV.NS", "TMPV.NS", "TATAMOTORS.BO"],
    "TMPV.NS": ["TMPV.NS", "TMCV.NS", "TATAMOTORS.NS"],
    "TMCV.NS": ["TMCV.NS", "TMPV.NS", "TATAMOTORS.NS"],
    "M&M.NS": ["M&M.NS", "M&M.BO"],
    "LTI.NS": ["LTIM.NS", "LTI.BO", "LTIM.BO", "540005.BO"],
    "MINDTREE.NS": ["LTIM.NS", "LTIM.BO", "540005.BO"],
    "LTIM.NS": ["LTIM.NS", "LTIM.BO", "540005.BO", "LTI.NS"],
    "HDFC.NS": ["HDFCBANK.NS", "HDFCBANK.BO"],
    "IDFCFIRSTB.NS": ["IDFCFIRSTB.NS", "IDFCBK.BO", "IDFCFIRSTB.BO"],
    "BAJAJ-AUTO.NS": ["BAJAJ-AUTO.NS", "BAJAJ_AUTO.NS", "BAJAJ-AUTO.BO"],
    "MCDOWELL-N.NS": ["UNITDSPR.NS", "MCDOWELL-N.BO"],
}


def _resolve_ticker_candidates(ticker: str) -> list[str]:
    clean = ticker.strip().upper()
    candidates: list[str] = []
    if clean in TICKER_ALIASES:
        for alias in TICKER_ALIASES[clean]:
            if alias not in candidates:
                candidates.append(alias)
    if clean not in candidates:
        candidates.append(clean)
    if clean.endswith(".NS"):
        bo_sym = clean[:-3] + ".BO"
        if bo_sym not in candidates:
            candidates.append(bo_sym)
    return candidates


def fetch_macro_market_regime() -> dict[str, object]:
    """Fetch broader Indian market context (Nifty 50 and India VIX) from Trading Room principles."""
    import yfinance as yf

    regime: dict[str, object] = {
        "nifty_close": 0.0,
        "nifty_pct": 0.0,
        "nifty_trend": "NEUTRAL",
        "vix_level": 15.0,
        "vix_regime": "Normal",
    }
    try:
        nifty = yf.Ticker("^NSEI")
        n_hist = nifty.history(period="5d", interval="1d")
        if not n_hist.empty and len(n_hist) >= 2:
            n_close = float(n_hist["Close"].iloc[-1])
            n_prev = float(n_hist["Close"].iloc[-2])
            n_chg = (n_close - n_prev) / n_prev * 100
            regime["nifty_close"] = round(n_close, 1)
            regime["nifty_pct"] = round(n_chg, 2)
            regime["nifty_trend"] = "BULLISH" if n_chg > 0.25 else ("BEARISH" if n_chg < -0.25 else "NEUTRAL")
    except Exception:
        pass

    try:
        vix = yf.Ticker("^INDIAVIX")
        v_hist = vix.history(period="5d", interval="1d")
        if not v_hist.empty:
            v_val = float(v_hist["Close"].iloc[-1])
            regime["vix_level"] = round(v_val, 2)
            if v_val < 15.0:
                regime["vix_regime"] = "Calm (Favorable)"
            elif v_val <= 18.0:
                regime["vix_regime"] = "Normal"
            else:
                regime["vix_regime"] = "Elevated (Caution)"
    except Exception:
        pass

    return regime


def fetch_stock_technical_context(ticker: str) -> dict[str, object]:
    """Calculate multi-day trend, RSI momentum, and volume surge for the target stock."""
    import numpy as np
    import yfinance as yf

    candidates = _resolve_ticker_candidates(ticker)
    for cand in candidates:
        try:
            t = yf.Ticker(cand)
            df = t.history(period="60d", interval="1d")
            if df.empty or len(df) < 15:
                continue

            close = df["Close"]
            vol = df["Volume"]

            # 1. Trend Quality: EMA9 vs EMA21 spread
            ema9 = close.ewm(span=9, adjust=False).mean()
            ema21 = close.ewm(span=21, adjust=False).mean()
            spread = (ema9.iloc[-1] - ema21.iloc[-1]) / ema21.iloc[-1] * 100
            trend_z = float(np.clip(spread / 1.5, -2.5, 2.5))
            trend_dir = "BULLISH" if trend_z > 0.2 else ("BEARISH" if trend_z < -0.2 else "NEUTRAL")

            # 2. RSI (14)
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1e-9)
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # 3. Volume Surge Ratio
            recent_vol = float(vol.iloc[-1])
            avg_vol = float(vol.iloc[-21:-1].mean()) if len(vol) >= 21 else float(vol.mean())
            vol_ratio = float(recent_vol / avg_vol) if avg_vol > 0 else 1.0

            return {
                "trend_z": round(trend_z, 2),
                "trend_direction": trend_dir,
                "rsi_14": round(rsi, 1),
                "volume_ratio": round(vol_ratio, 2),
                "is_overbought": rsi > 75.0,
                "is_oversold": rsi < 25.0,
                "has_volume_surge": vol_ratio >= 1.3,
            }
        except Exception:
            continue

    return {
        "trend_z": 0.0,
        "trend_direction": "NEUTRAL",
        "rsi_14": 50.0,
        "volume_ratio": 1.0,
        "is_overbought": False,
        "is_oversold": False,
        "has_volume_surge": False,
    }


def compute_trading_room_confluence(
    event_score: float,
    tech_ctx: dict[str, object],
    macro_ctx: dict[str, object],
) -> dict[str, object]:
    """Compute 3-family confluence alpha, badging, reasons, and confidence adjustment."""
    import numpy as np

    trend_z = float(tech_ctx.get("trend_z", 0.0))
    trend_dir = str(tech_ctx.get("trend_direction", "NEUTRAL"))
    rsi = float(tech_ctx.get("rsi_14", 50.0))
    vol_ratio = float(tech_ctx.get("volume_ratio", 1.0))
    nifty_trend = str(macro_ctx.get("nifty_trend", "NEUTRAL"))
    vix = float(macro_ctx.get("vix_level", 15.0))

    # 1. 3-Family Alpha Scores
    event_alpha = float(np.clip(event_score, -1.0, 1.0))
    trend_alpha = float(np.clip(trend_z / 1.8, -1.0, 1.0))
    flow_alpha = 0.5 if nifty_trend == "BULLISH" else (-0.5 if nifty_trend == "BEARISH" else 0.0)
    if vix > 18.0:
        flow_alpha -= 0.25

    confluence_score = round(0.50 * event_alpha + 0.30 * trend_alpha + 0.20 * flow_alpha, 3)

    # 2. Confluence Diagnosis
    news_dir = "BULLISH" if event_score > BULLISH_THRESHOLD else ("BEARISH" if event_score < BEARISH_THRESHOLD else "NEUTRAL")

    reasons: list[str] = []
    confluence_status = "NEUTRAL"
    confluence_badge = "NEUTRAL"
    confluence_class = "fp-badge-neutral"
    confidence_delta = 0

    if news_dir == "BULLISH" and trend_dir == "BULLISH":
        confluence_status = "CONFLUENCE CONFIRMED"
        confluence_badge = "CONFIRMED"
        confluence_class = "fp-badge-confirmed"
        confidence_delta = 15
        reasons.append("Trading Room Confluence: Positive news is backed by an upward price trend (+EMA spread).")
        if vol_ratio >= 1.3:
            reasons.append(f"Institutional Volume: High volume surge ({vol_ratio:.1f}x 20D average) confirms real conviction.")
            confidence_delta += 10
        if rsi > 75.0:
            reasons.append(f"Caution: RSI is {rsi:.0f} (overbought), which may trigger short-term profit taking.")
            confidence_delta -= 10
    elif news_dir == "BEARISH" and trend_dir == "BEARISH":
        confluence_status = "CONFLUENCE CONFIRMED"
        confluence_badge = "CONFIRMED"
        confluence_class = "fp-badge-confirmed"
        confidence_delta = 15
        reasons.append("Trading Room Confluence: Negative news aligns with downward technical momentum.")
        if vol_ratio >= 1.3:
            reasons.append(f"Institutional Volume: Selling volume is elevated ({vol_ratio:.1f}x 20D average).")
            confidence_delta += 10
    elif (news_dir == "BULLISH" and trend_dir == "BEARISH") or (news_dir == "BEARISH" and trend_dir == "BULLISH"):
        confluence_status = "DIVERGENCE WARNING"
        confluence_badge = "DIVERGENCE"
        confluence_class = "fp-badge-divergence"
        confidence_delta = -25
        opp_trend = "downtrend" if trend_dir == "BEARISH" else "uptrend"
        reasons.append(f"Divergence Warning: News sentiment points {news_dir.lower()}, but price is in an opposing {opp_trend} ({trend_z:+.2f}z).")
        reasons.append("Risk control applied: Headwind penalty reduces signal conviction to protect against traps.")
    else:
        confluence_status = "PARTIAL ALIGNMENT"
        confluence_badge = "PARTIAL"
        confluence_class = "fp-badge-partial"
        reasons.append(f"Technical Context: Trend is {trend_dir.lower()} with RSI at {rsi:.0f}.")

    # Macro regime factor
    n_pct = float(macro_ctx.get("nifty_pct", 0.0))
    v_reg = str(macro_ctx.get("vix_regime", "Normal"))
    reasons.append(f"Market Environment: Nifty 50 is {nifty_trend.lower()} ({n_pct:+.2f}%), India VIX at {vix:.1f} ({v_reg}).")

    final_signal = signal_from_score(confluence_score)

    return {
        "confluence_score": confluence_score,
        "confluence_signal": final_signal,
        "confluence_status": confluence_status,
        "confluence_badge": confluence_badge,
        "confluence_class": confluence_class,
        "confluence_reasons": reasons,
        "confidence_delta": confidence_delta,
    }


def aggregate_article_signals(news_df):
    """Aggregate article sentiment into one row per ticker with Trading Room confluence confirmation.

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
                "confluence_score",
                "confluence_signal",
                "confluence_status",
                "confluence_badge",
                "confluence_class",
                "confluence_reasons",
                "trend_direction",
                "trend_z",
                "rsi_14",
                "volume_ratio",
                "nifty_pct",
                "nifty_trend",
                "vix_level",
                "vix_regime",
            ]
        )

    macro_ctx = fetch_macro_market_regime()
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
        raw_signal = signal_from_score(float(weighted_score))
        confidence, agreement_count, directional_count = _confidence_detail(
            raw_signal,
            ticker_df["sentiment_label"].astype(str).str.lower().tolist(),
        )

        tech_ctx = fetch_stock_technical_context(str(ticker))
        confluence = compute_trading_room_confluence(float(weighted_score), tech_ctx, macro_ctx)

        rows.append(
            {
                "ticker": ticker,
                "article_count": int(len(ticker_df)),
                "aggregate_score": round(float(weighted_score), 4),
                "signal": confluence["confluence_signal"],
                "raw_sentiment_signal": raw_signal,
                "confidence": confidence,
                "agreement_count": int(agreement_count),
                "directional_article_count": int(directional_count),
                "confluence_score": confluence["confluence_score"],
                "confluence_status": confluence["confluence_status"],
                "confluence_badge": confluence["confluence_badge"],
                "confluence_class": confluence["confluence_class"],
                "confluence_reasons": confluence["confluence_reasons"],
                "confidence_delta": confluence["confidence_delta"],
                "trend_direction": tech_ctx["trend_direction"],
                "trend_z": tech_ctx["trend_z"],
                "rsi_14": tech_ctx["rsi_14"],
                "volume_ratio": tech_ctx["volume_ratio"],
                "nifty_pct": macro_ctx["nifty_pct"],
                "nifty_trend": macro_ctx["nifty_trend"],
                "vix_level": macro_ctx["vix_level"],
                "vix_regime": macro_ctx["vix_regime"],
            }
        )

    return pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)


def generate_stock_signals(news_df):
    """Alias kept expressive for app and report usage."""
    return aggregate_article_signals(news_df)
