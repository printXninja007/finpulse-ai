import json
import os

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FinPulse AI – Real-Time Financial News Summarization and Sentiment Analysis</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {
      --fp-navy: #14183f;
      --fp-green: #11854a;
      --fp-red: #b4232a;
      --fp-gray: #6b7280;
      --fp-light: #f8fafc;
      --fp-border: 1px solid rgba(20, 24, 63, 0.18);
      --fp-border-strong: 1.5px solid rgba(20, 24, 63, 0.7);
      --fp-radius: 18px;
      --fp-radius-sm: 12px;
      --fp-shadow: 0 18px 46px rgba(20, 24, 63, 0.09);
      --fp-shadow-hover: 0 24px 64px rgba(20, 24, 63, 0.13);
      --fp-mono: "JetBrains Mono", "SFMono-Regular", "Menlo", "Consolas", monospace;
      --fp-sans: "Inter", "Segoe UI", system-ui, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background:
        radial-gradient(circle at top left, rgba(17, 133, 74, 0.08), transparent 34rem),
        radial-gradient(circle at top right, rgba(20, 24, 63, 0.08), transparent 30rem),
        linear-gradient(180deg, #ffffff 0%, #fbfcff 52%, #f7f9fd 100%);
      color: var(--fp-navy);
      font-family: var(--fp-sans);
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }

    /* Streamlit-identical Header */
    header.stHeader {
      background: rgba(255, 255, 255, 0.96);
      border-bottom: var(--fp-border);
      backdrop-filter: blur(10px);
      height: 3.2rem;
      z-index: 999990;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      display: flex;
      align-items: center;
      padding: 0 1.5rem 0 2.85rem;
      font-size: clamp(0.76rem, 1.15vw, 0.88rem);
      font-weight: 650;
      color: var(--fp-navy);
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2314183f' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='22 7 13.5 15.5 8.5 10.5 2 17'%3E%3C/polyline%3E%3Cpolyline points='16 7 22 7 22 13'%3E%3C/polyline%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: 1rem center;
      background-size: 18px 18px;
    }

    .block-container {
      max-width: 1440px;
      margin: 0 auto;
      padding: 4.8rem 1.5rem 3.5rem;
    }

    /* Top Controls Row */
    .fp-top-row {
      display: grid;
      grid-template-columns: 1fr 1.25fr;
      gap: 22px;
      margin-bottom: 22px;
      align-items: stretch;
    }

    .fp-tool-label {
      margin-bottom: 6px;
      font-family: var(--fp-mono);
      font-size: 0.9rem;
      color: var(--fp-navy);
      font-weight: 600;
    }

    .fp-select-wrap {
      position: relative;
      margin-bottom: 12px;
    }

    .fp-select {
      width: 100%;
      height: 44px;
      padding: 0 14px;
      border: var(--fp-border);
      border-radius: var(--fp-radius-sm);
      background: rgba(255, 255, 255, 0.92);
      color: var(--fp-navy);
      font-family: var(--fp-sans);
      font-size: 0.95rem;
      font-weight: 600;
      outline: none;
      box-shadow: 0 8px 28px rgba(20, 24, 63, 0.07);
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2314183f' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 14px center;
      transition: border-color 150ms ease, box-shadow 150ms ease;
    }

    .fp-select:focus {
      border-color: rgba(17, 133, 74, 0.75);
      box-shadow: 0 0 0 4px rgba(17, 133, 74, 0.11);
    }

    .fp-metric-card-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 12px;
    }

    .fp-metric-card {
      border: var(--fp-border);
      border-radius: var(--fp-radius-sm);
      padding: 10px 14px;
      background: #ffffff;
      box-shadow: 0 2px 8px rgba(20, 24, 63, 0.03);
      min-height: 74px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .fp-metric-card-title {
      font-size: 0.74rem;
      font-weight: 700;
      color: var(--fp-navy);
      margin-bottom: 2px;
    }

    .fp-metric-card-value {
      font-size: 1.25rem;
      font-weight: 800;
      color: var(--fp-navy);
      font-family: var(--fp-mono);
      letter-spacing: -0.01em;
      margin: 1px 0;
      line-height: 1.2;
    }

    .fp-metric-card-sub {
      font-size: 0.68rem;
      color: var(--fp-gray);
      font-family: var(--fp-mono);
      font-weight: 600;
      margin-top: 1px;
    }

    .fp-screener-label {
      margin-top: 12px;
      margin-bottom: 8px;
      font-family: var(--fp-mono);
      font-size: 0.74rem;
      font-weight: 700;
      color: var(--fp-gray);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .fp-popup-btn-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .fp-btn {
      border: var(--fp-border);
      border-radius: var(--fp-radius);
      background: #ffffff;
      color: var(--fp-navy);
      font-family: var(--fp-mono);
      font-size: 0.82rem;
      font-weight: 700;
      padding: 10px 16px;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(20, 24, 63, 0.08);
      transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      width: 100%;
    }

    .fp-btn:hover {
      transform: translateY(-1px);
      border-color: rgba(20, 24, 63, 0.65);
      box-shadow: 0 14px 32px rgba(20, 24, 63, 0.12);
    }

    .fp-btn-primary {
      background: var(--fp-navy);
      color: #ffffff;
      border-color: var(--fp-navy);
    }

    .fp-btn-primary:hover {
      background: #1e245a;
    }

    /* About Card */
    .fp-card {
      border: var(--fp-border);
      border-radius: var(--fp-radius);
      padding: 24px;
      background: rgba(255, 255, 255, 0.9);
      margin-bottom: 18px;
      box-shadow: var(--fp-shadow);
      transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
      box-sizing: border-box;
    }

    .fp-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--fp-shadow-hover);
      border-color: rgba(20, 24, 63, 0.32);
    }

    .fp-about-card {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 290px;
      height: 100%;
      margin-bottom: 0;
    }

    .fp-about-title {
      font-size: 1.05rem;
      font-weight: 750;
      color: var(--fp-navy);
      margin-bottom: 12px;
    }

    .fp-about-body {
      font-size: 0.88rem;
      line-height: 1.55;
      color: #374151;
      margin-bottom: 16px;
      flex: 1;
    }

    .fp-about-stats-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      padding-top: 14px;
      border-top: 1px solid rgba(20, 24, 63, 0.08);
    }

    .fp-stat-item {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }

    .fp-stat-icon-box {
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
    }

    .fp-stat-icon-box svg {
      width: 18px;
      height: 18px;
    }

    .fp-stat-meta {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .fp-stat-lbl {
      font-family: var(--fp-mono);
      font-size: 0.7rem;
      color: var(--fp-gray);
      line-height: 1.2;
    }

    .fp-stat-val {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--fp-navy);
      line-height: 1.3;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Status Strip */
    .fp-status-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 8px 0 10px;
    }

    .fp-chip {
      border: var(--fp-border);
      border-radius: 999px;
      background: rgba(255,255,255,0.78);
      padding: 7px 12px;
      color: rgba(20, 24, 63, 0.74);
      font-family: var(--fp-mono);
      font-size: 0.78rem;
      font-weight: 600;
      box-shadow: 0 8px 20px rgba(20,24,63,0.05);
    }

    .fp-disclaimer {
      font-size: 0.82rem;
      color: var(--fp-gray);
      margin-bottom: 20px;
    }

    /* 3 Column Dashboard Layout */
    .fp-dashboard-grid {
      display: grid;
      grid-template-columns: 0.95fr 1.08fr 1.05fr;
      gap: 18px;
      align-items: start;
    }

    .fp-card-title {
      margin: 0 0 16px;
      font-family: var(--fp-mono);
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: 0;
      color: var(--fp-navy);
    }

    .fp-card-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }

    .fp-card-title-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .fp-card-icon {
      width: 17px;
      height: 17px;
      color: var(--fp-navy);
      flex-shrink: 0;
    }

    .fp-card-title-text {
      font-family: var(--fp-mono);
      font-size: 0.98rem;
      font-weight: 750;
      color: var(--fp-navy);
      letter-spacing: -0.01em;
    }

    /* Badges & Pills */
    .fp-confluence-badge {
      display: inline-block;
      font-family: var(--fp-mono);
      font-size: 0.68rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .fp-badge-confirmed {
      background: #dcfce7;
      color: #166534;
      border: 1px solid #86efac;
    }

    .fp-badge-divergence {
      background: #fee2e2;
      color: #991b1b;
      border: 1px solid #fca5a5;
    }

    .fp-badge-neutral {
      background: #f1f5f9;
      color: #334155;
      border: 1px solid #cbd5e1;
    }

    .fp-signal-row {
      display: flex;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 14px;
    }

    .fp-signal-word {
      font-family: var(--fp-mono);
      font-size: clamp(2rem, 3.2vw, 2.6rem);
      font-weight: 800;
      line-height: 1;
    }

    .fp-signal-score {
      font-family: var(--fp-mono);
      font-size: 1rem;
      font-weight: 700;
    }

    .fp-green { color: var(--fp-green); }
    .fp-red { color: var(--fp-red); }
    .fp-gray { color: var(--fp-gray); }

    .fp-confluence-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 10px 0;
      padding: 8px 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
    }

    .fp-confluence-tag {
      font-family: var(--fp-mono);
      font-size: 0.74rem;
      font-weight: 600;
      color: #1e293b;
    }

    .fp-why-section {
      border-top: var(--fp-border);
      padding-top: 14px;
      margin-top: 10px;
    }

    .fp-why-title {
      font-family: var(--fp-mono);
      font-weight: 800;
      font-size: 0.95rem;
      margin-bottom: 8px;
      color: var(--fp-navy);
    }

    .fp-list {
      margin: 0;
      padding-left: 18px;
      color: var(--fp-navy);
      font-size: 0.92rem;
      line-height: 1.6;
      overflow-wrap: anywhere;
    }

    /* Confidence Card */
    .fp-confidence-row {
      display: grid;
      grid-template-columns: minmax(140px, 0.9fr) 1.1fr;
      gap: 18px;
      align-items: center;
    }

    .fp-confidence-number {
      font-family: var(--fp-mono);
      font-size: 2.7rem;
      font-weight: 800;
      line-height: 1;
    }

    .fp-confidence-label {
      margin-top: 8px;
      font-family: var(--fp-mono);
      font-size: 1rem;
    }

    /* Key Factors Card */
    .fp-factor-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }

    .fp-factor-col {
      min-height: 120px;
    }

    .fp-factor-col + .fp-factor-col {
      border-left: var(--fp-border);
      padding-left: 18px;
    }

    .fp-factor-item {
      margin: 0 0 11px;
      font-size: 0.92rem;
      line-height: 1.35;
    }

    /* Summary Card */
    .fp-summary-headline {
      font-size: 0.96rem;
      font-weight: 700;
      color: var(--fp-navy);
      line-height: 1.42;
      margin-bottom: 8px;
    }

    .fp-summary-body {
      font-size: 0.89rem;
      line-height: 1.55;
      color: rgba(20, 24, 63, 0.85);
    }

    /* Segmented Control for Timeframe */
    .fp-segmented-control {
      display: inline-flex;
      background: #f1f3f8;
      padding: 3px;
      border-radius: 8px;
      border: 1px solid rgba(20, 24, 63, 0.12);
      gap: 2px;
    }

    .fp-segmented-btn {
      background: transparent;
      border: none;
      border-radius: 6px;
      padding: 4px 11px;
      font-family: var(--fp-mono);
      font-size: 0.74rem;
      font-weight: 700;
      color: var(--fp-gray);
      cursor: pointer;
      transition: all 150ms ease;
    }

    .fp-segmented-btn:hover {
      color: var(--fp-navy);
    }

    .fp-segmented-btn.active {
      background: #ffffff;
      color: var(--fp-navy);
      box-shadow: 0 2px 6px rgba(20, 24, 63, 0.12);
    }

    /* Backtest Metrics below comparison plot */
    .fp-backtest-metrics {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      border-top: var(--fp-border);
      margin-top: 14px;
    }

    .fp-backtest-metric {
      padding: 14px 12px 4px;
      border-right: var(--fp-border);
    }

    .fp-backtest-metric:last-child {
      border-right: none;
    }

    .fp-metric-label {
      font-family: var(--fp-mono);
      font-size: 0.76rem;
      color: var(--fp-gray);
    }

    .fp-metric-value {
      margin-top: 8px;
      font-family: var(--fp-mono);
      font-size: 1.25rem;
      font-weight: 800;
      color: var(--fp-navy);
    }

    .fp-backtest-note {
      border-top: var(--fp-border);
      margin-top: 14px;
      padding-top: 14px;
      font-size: 0.88rem;
      line-height: 1.45;
      color: var(--fp-gray);
    }

    /* LIVE NEWS FEED - EXACT STREAMLIT SPEC */
    .fp-feed-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(20, 24, 63, 0.1);
    }

    .fp-feed-title-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .fp-bolt-icon {
      width: 17px;
      height: 17px;
      color: var(--fp-navy);
      flex-shrink: 0;
    }

    .fp-feed-title {
      font-family: var(--fp-mono);
      font-size: 0.98rem;
      font-weight: 750;
      color: var(--fp-navy);
      letter-spacing: -0.01em;
    }

    .fp-view-all {
      font-family: var(--fp-mono);
      font-size: 0.8rem;
      font-weight: 600;
      color: rgba(20, 24, 63, 0.75);
      text-decoration: none;
      transition: color 150ms ease;
    }

    .fp-view-all:hover {
      color: var(--fp-navy);
      text-decoration: underline;
    }

    .fp-feed-list {
      display: flex;
      flex-direction: column;
    }

    .fp-feed-item-row {
      display: flex;
      align-items: flex-start;
      gap: 14px;
      padding: 12px 0;
      border-bottom: 1px solid rgba(20, 24, 63, 0.08);
    }

    .fp-feed-item-row:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }

    .fp-feed-item-row:first-child {
      padding-top: 0;
    }

    .fp-feed-time {
      font-family: var(--fp-mono);
      font-size: 0.8rem;
      color: var(--fp-gray);
      flex-shrink: 0;
      min-width: 52px;
      padding-top: 1px;
    }

    .fp-feed-content {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
      flex: 1;
      min-width: 0;
    }

    .fp-feed-headline-link {
      color: var(--fp-navy);
      font-size: 0.92rem;
      font-weight: 700;
      line-height: 1.4;
      text-decoration: none;
      overflow-wrap: anywhere;
      transition: opacity 150ms ease;
    }

    .fp-feed-headline-link:hover {
      opacity: 0.75;
      text-decoration: underline;
    }

    .fp-feed-headline-text {
      color: var(--fp-navy);
      font-size: 0.92rem;
      font-weight: 700;
      line-height: 1.4;
      overflow-wrap: anywhere;
    }

    .fp-pill {
      display: inline-flex;
      align-items: center;
      padding: 2px 10px;
      border-radius: 9999px;
      font-family: var(--fp-mono);
      font-size: 0.72rem;
      font-weight: 700;
      line-height: 1.3;
    }

    .fp-pill-positive {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid rgba(21, 128, 61, 0.2);
    }

    .fp-pill-negative {
      background: #fee2e2;
      color: #b91c1c;
      border: 1px solid rgba(185, 28, 28, 0.2);
    }

    .fp-pill-neutral {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid rgba(71, 85, 105, 0.2);
    }

    .fp-small {
      font-size: 0.88rem;
      color: var(--fp-gray);
    }

    /* Modal Overlay */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(20, 24, 63, 0.45);
      backdrop-filter: blur(6px);
      z-index: 1000000;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .modal-card {
      background: #ffffff;
      border-radius: var(--fp-radius);
      border: var(--fp-border-strong);
      box-shadow: 0 25px 60px rgba(20, 24, 63, 0.2);
      max-width: 580px;
      width: 100%;
      padding: 24px;
      max-height: 85vh;
      overflow-y: auto;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 12px;
      border-bottom: var(--fp-border);
    }

    .modal-title {
      font-family: var(--fp-mono);
      font-size: 1.1rem;
      font-weight: 800;
      color: var(--fp-navy);
    }

    .modal-close {
      background: none;
      border: none;
      font-size: 1.4rem;
      cursor: pointer;
      color: var(--fp-gray);
    }

    @media (max-width: 1050px) {
      .fp-top-row {
        grid-template-columns: 1fr;
      }
      .fp-dashboard-grid {
        grid-template-columns: 1fr;
      }
      .fp-backtest-metrics {
        grid-template-columns: repeat(2, 1fr);
      }
      .fp-about-stats-row {
        grid-template-columns: repeat(2, 1fr);
      }
    }
  </style>
</head>
<body>
  <!-- Fixed Header -->
  <header class="stHeader">
    FinPulse AI – Real-Time Financial News Summarization and Sentiment Analysis
  </header>

  <main class="block-container">
    <!-- Top Controls Row -->
    <div class="fp-top-row">
      <!-- Left Controls Col -->
      <div>
        <div class="fp-tool-label">Search Stock</div>
        <div class="fp-select-wrap">
          <select id="stock-select" class="fp-select" onchange="onStockChange(this.value)">
            <!-- Options populated by JS -->
          </select>
        </div>

        <div class="fp-metric-card-row">
          <div class="fp-metric-card">
            <div class="fp-metric-card-title">Market Cap</div>
            <div class="fp-metric-card-value" id="market-cap-val">---</div>
            <div class="fp-metric-card-sub" id="market-cap-sub">Large Cap</div>
          </div>
          <div class="fp-metric-card">
            <div class="fp-metric-card-title">Current Stock Price</div>
            <div class="fp-metric-card-value" id="price-val">---</div>
            <div class="fp-metric-card-sub" id="price-sub">NSE Live</div>
          </div>
        </div>

        <div class="fp-screener-label">Filter by Weekly News Sentiment (News Only)</div>
        <div class="fp-popup-btn-row">
          <button class="fp-btn" onclick="openPopup('bullish')">🟢 Top 5 Weekly Bullish</button>
          <button class="fp-btn" onclick="openPopup('bearish')">🔴 Top 5 Weekly Bearish</button>
        </div>
      </div>

      <!-- Right About Company Col -->
      <div id="about-card-container">
        <!-- Rendered by JS -->
      </div>
    </div>

    <!-- Status Strip -->
    <div class="fp-status-strip" id="status-strip">
      <!-- Rendered by JS -->
    </div>
    <div class="fp-disclaimer">
      Decision-support only, not investment advice. No price targets, stop-losses, or buy/sell recommendations.
    </div>

    <!-- 3-Column Dashboard -->
    <div class="fp-dashboard-grid">
      <!-- Left Column -->
      <div class="fp-col">
        <!-- RECOMMENDATION CARD -->
        <div class="fp-card" id="recommendation-card">
          <!-- Rendered by JS -->
        </div>

        <!-- CONFIDENCE LEVEL CARD -->
        <div class="fp-card" id="confidence-card">
          <!-- Rendered by JS -->
        </div>

        <!-- KEY FACTORS CARD -->
        <div class="fp-card" id="key-factors-card">
          <!-- Rendered by JS -->
        </div>
      </div>

      <!-- Middle Column -->
      <div class="fp-col">
        <!-- REAL-TIME NEWS SUMMARY CARD -->
        <div class="fp-card" id="summary-card">
          <!-- Rendered by JS -->
        </div>

        <!-- PRICE VS NIFTY 50 BENCHMARK CARD -->
        <div class="fp-card" id="comparison-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div class="fp-card-title" style="margin-bottom: 0;">PRICE VS NIFTY 50</div>
            <div class="fp-segmented-control">
              <button class="fp-segmented-btn active" data-tf="1Y" onclick="setTimeframe('1Y')">1Y</button>
              <button class="fp-segmented-btn" data-tf="3Y" onclick="setTimeframe('3Y')">3Y</button>
              <button class="fp-segmented-btn" data-tf="5Y" onclick="setTimeframe('5Y')">5Y</button>
              <button class="fp-segmented-btn" data-tf="ALL" onclick="setTimeframe('ALL')">ALL</button>
            </div>
          </div>
          <div id="comparison-plot" style="width: 100%; height: 270px;"></div>
          <div id="comparison-metrics"></div>
        </div>

        <!-- Export CSV Button -->
        <div style="margin-top: 10px;">
          <button class="fp-btn" onclick="exportCSV()" style="width: 100%; padding: 12px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Export summaries + signals CSV
          </button>
        </div>
      </div>

      <!-- Right Column -->
      <div class="fp-col">
        <!-- LIVE NEWS FEED CARD -->
        <div class="fp-card" id="feed-card">
          <!-- Rendered by JS matching Streamlit _render_live_feed_card -->
        </div>
      </div>
    </div>
  </main>

  <!-- Modal for Weekly Rankings -->
  <div class="modal-overlay" id="modal-overlay" onclick="if(event.target===this)closePopup()">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title" id="modal-title">Top 5 Weekly Ranking</div>
        <button class="modal-close" onclick="closePopup()">&times;</button>
      </div>
      <div class="fp-small" id="modal-desc" style="margin-bottom: 14px;"></div>
      <div id="modal-list"></div>
    </div>
  </div>

  <script>
    const appData = __APP_DATA_JSON__;
    let currentTicker = "POWERGRID.NS";
    let currentTimeframe = "1Y";

    function init() {
      const select = document.getElementById("stock-select");
      select.innerHTML = "";
      Object.keys(appData.stocks).forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = `${appData.stocks[t].company} (${t.replace(".NS", "")})`;
        if (t === currentTicker) opt.selected = true;
        select.appendChild(opt);
      });

      renderAll();
    }

    function onStockChange(ticker) {
      currentTicker = ticker;
      renderAll();
    }

    function renderAll() {
      const stock = appData.stocks[currentTicker];
      if (!stock) return;

      // Top metrics
      document.getElementById("market-cap-val").textContent = stock.market_cap || "---";
      document.getElementById("price-val").textContent = stock.price ? `₹${Number(stock.price).toFixed(2)}` : "---";
      const changeEl = document.getElementById("price-sub");
      if (stock.change_pct != null) {
        changeEl.textContent = `${stock.change_pct >= 0 ? '+' : ''}${stock.change_pct}% Today`;
        changeEl.style.color = stock.change_pct >= 0 ? "#11854a" : "#b4232a";
      }

      renderAboutCard(stock);
      renderStatusStrip(stock);
      renderRecommendationCard(stock);
      renderConfidenceCard(stock);
      renderKeyFactorsCard(stock);
      renderSummaryCard(stock);
      renderComparisonCard(stock);
      renderFeedCard(stock);
    }

    function renderAboutCard(stock) {
      const p = stock.profile || {};
      const cont = document.getElementById("about-card-container");
      cont.innerHTML = `
        <div class="fp-card fp-about-card">
          <div class="fp-about-title">About the Company</div>
          <div class="fp-about-body">${p.summary || "Select a stock to view profile details."}</div>
          <div class="fp-about-stats-row">
            <div class="fp-stat-item">
              <div class="fp-stat-icon-box">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"></rect><path d="M9 22v-4h6v4"></path></svg>
              </div>
              <div class="fp-stat-meta"><div class="fp-stat-lbl">Industry</div><div class="fp-stat-val">${p.industry || "---"}</div></div>
            </div>
            <div class="fp-stat-item">
              <div class="fp-stat-icon-box">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
              </div>
              <div class="fp-stat-meta"><div class="fp-stat-lbl">Founded</div><div class="fp-stat-val">${p.founded || "---"}</div></div>
            </div>
            <div class="fp-stat-item">
              <div class="fp-stat-icon-box">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
              </div>
              <div class="fp-stat-meta"><div class="fp-stat-lbl">Headquarters</div><div class="fp-stat-val">${p.headquarters || "---"}</div></div>
            </div>
            <div class="fp-stat-item">
              <div class="fp-stat-icon-box">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
              </div>
              <div class="fp-stat-meta"><div class="fp-stat-lbl">Employees</div><div class="fp-stat-val">${p.employees || "---"}</div></div>
            </div>
          </div>
        </div>
      `;
    }

    function renderStatusStrip(stock) {
      const cont = document.getElementById("status-strip");
      const nPct = stock.nifty_pct != null ? stock.nifty_pct : 0.0;
      const vix = stock.vix_level != null ? stock.vix_level : 15.0;
      const vReg = stock.vix_regime || "Normal";
      cont.innerHTML = `
        <span class="fp-chip">${stock.company} · ${stock.ticker}</span>
        <span class="fp-chip">NIFTY 50: ${nPct >= 0 ? '+' : ''}${Number(nPct).toFixed(2)}%</span>
        <span class="fp-chip">INDIA VIX: ${Number(vix).toFixed(1)} (${vReg})</span>
        <span class="fp-chip">Trading Room Confluence Active</span>
      `;
    }

    function renderRecommendationCard(stock) {
      const cont = document.getElementById("recommendation-card");
      const sig = (stock.signal || "Neutral").toUpperCase();
      const sigClass = sig === "BULLISH" ? "fp-green" : sig === "BEARISH" ? "fp-red" : "fp-gray";
      const score = stock.confluence_score != null ? stock.confluence_score : (stock.aggregate_score || 0.0);
      const confStatus = stock.confluence_status || "CONFLUENCE CONFIRMED";
      const confBadgeClass = stock.confluence_class || "fp-badge-confirmed";

      const trendDir = stock.trend_direction || "NEUTRAL";
      const trendZ = stock.trend_z != null ? stock.trend_z : 0.0;
      const rsi = stock.rsi_14 != null ? stock.rsi_14 : 50;
      const volRatio = stock.volume_ratio != null ? stock.volume_ratio : 1.0;
      const nPct = stock.nifty_pct != null ? stock.nifty_pct : 0.0;
      const vix = stock.vix_level != null ? stock.vix_level : 15.0;

      const reasons = stock.reasons || [
        `${stock.total_articles || 8} recent articles analyzed for this ticker`,
        `${stock.agreement_count || 5}/${stock.total_articles || 8} articles align with aggregate direction`,
        `Aggregate sentiment score: ${score >= 0 ? '+' : ''}${Number(score).toFixed(2)}`
      ];
      const reasonsHtml = reasons.map(r => `<li>${r}</li>`).join("");

      cont.innerHTML = `
        <div class="fp-card-header-row" style="margin-bottom: 8px;">
          <div class="fp-card-title" style="margin: 0;">RECOMMENDATION</div>
          <span class="fp-confluence-badge ${confBadgeClass}">${confStatus}</span>
        </div>
        <div class="fp-signal-row">
          <span class="fp-signal-word ${sigClass}">${sig}</span>
          <span class="fp-signal-score ${sigClass}">Confluence Alpha ${score >= 0 ? '+' : ''}${Number(score).toFixed(2)}</span>
        </div>
        <div class="fp-confluence-strip">
          <span class="fp-confluence-tag">📰 News: <b>${sig}</b></span>
          <span class="fp-confluence-tag">📈 Trend: <b>${trendDir} (${trendZ >= 0 ? '+' : ''}${Number(trendZ).toFixed(2)}z)</b> · RSI ${Math.round(rsi)} · Vol ${Number(volRatio).toFixed(1)}x</span>
          <span class="fp-confluence-tag">🏛 Market: <b>Nifty ${nPct >= 0 ? '+' : ''}${Number(nPct).toFixed(2)}%</b> · VIX ${Number(vix).toFixed(1)}</span>
        </div>
        <div class="fp-why-section">
          <div class="fp-why-title">WHY?</div>
          <ul class="fp-list">${reasonsHtml}</ul>
        </div>
      `;
    }

    function renderConfidenceCard(stock) {
      const cont = document.getElementById("confidence-card");
      const pct = stock.confidence_pct || 80;
      const confLabel = stock.confidence || "High Confidence";
      const confStatus = stock.confluence_status || "CONFLUENCE CONFIRMED";
      const confClass = stock.confluence_class || "fp-badge-confirmed";
      const color = pct >= 70 ? "#11854a" : pct >= 40 ? "#14183f" : "#6b7280";

      // Angular gauge arc length = 125.6
      const offset = 125.6 - (125.6 * (pct / 100));

      cont.innerHTML = `
        <div class="fp-card-title">CONFIDENCE LEVEL</div>
        <div class="fp-confidence-row">
          <div>
            <svg viewBox="0 0 100 55" style="width:100%; max-width:150px; overflow:visible;">
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#eef0f5" stroke-width="12" stroke-linecap="round"/>
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="${color}" stroke-width="12" stroke-dasharray="125.6" stroke-dashoffset="${offset}" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <div class="fp-confidence-number" style="color:${color};">${pct}%</div>
            <div class="fp-confidence-label" style="color:${color}; margin-bottom: 6px;">${confLabel}</div>
            <span class="fp-confluence-badge ${confClass}" style="font-size: 0.62rem;">${confStatus}</span>
          </div>
        </div>
      `;
    }

    function renderKeyFactorsCard(stock) {
      const cont = document.getElementById("key-factors-card");
      const k = stock.key_factors || {};
      const pos = k.bullish || ["Positive sentiment supported by steady project capitalization"];
      const neg = k.bearish || ["Minor macro volatility across benchmark sector"];

      const posHtml = pos.map(f => `<p class="fp-factor-item fp-green">+ ${f}</p>`).join("");
      const negHtml = neg.map(f => `<p class="fp-factor-item fp-red">- ${f}</p>`).join("");

      cont.innerHTML = `
        <div class="fp-card-title">KEY FACTORS</div>
        <div class="fp-factor-grid">
          <div class="fp-factor-col">${posHtml}</div>
          <div class="fp-factor-col">${negHtml}</div>
        </div>
      `;
    }

    function renderSummaryCard(stock) {
      const cont = document.getElementById("summary-card");
      const sig = stock.signal || "Bullish";
      const pillClass = sig === "Bullish" ? "fp-pill-positive" : sig === "Bearish" ? "fp-pill-negative" : "fp-pill-neutral";
      const pillText = `${sig} &bull; ${stock.confidence_pct || 80}%`;

      const newspaperSvg = `
        <svg class="fp-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
          <path d="M18 14h-8"/>
          <path d="M15 18h-5"/>
          <path d="M10 6h8v4h-8V6Z"/>
        </svg>
      `;

      cont.innerHTML = `
        <div class="fp-card-header-row">
          <div class="fp-card-title-wrap">
            ${newspaperSvg}
            <span class="fp-card-title-text">Real-Time News Summary</span>
          </div>
          <span class="fp-pill ${pillClass}">${pillText}</span>
        </div>
        <div class="fp-summary-headline">${stock.summary_headline || "Latest Market News"}</div>
        <div class="fp-summary-body">${stock.summary_body || "Analysis of corporate developments and earnings momentum."}</div>
      `;
    }

    /* PRICE VS NIFTY 50 - EXACT STREAMLIT SPEC WITH PLOTLY.JS */
    function renderComparisonCard(stock) {
      const tf = currentTimeframe;
      const tfs = stock.timeframes || {};
      const comp = tfs[tf] || stock.comparison || {};
      const dates = comp.dates || [];
      const stockReturns = comp.stock_returns || [];
      const niftyReturns = comp.nifty_returns || [];
      const stockCloses = comp.stock_closes || [];
      const niftyCloses = comp.nifty_closes || [];

      const stockLastReturn = comp.stock_return != null ? comp.stock_return : (stockReturns.length ? stockReturns[stockReturns.length - 1] : 0.0);
      const niftyLastReturn = comp.nifty_return != null ? comp.nifty_return : (niftyReturns.length ? niftyReturns[niftyReturns.length - 1] : 0.0);
      const alpha = comp.alpha != null ? comp.alpha : (stockLastReturn - niftyLastReturn);

      const stockColor = stockLastReturn >= 0 ? "#11854a" : "#2563eb";
      const rawDisplayName = stock.company || stock.ticker;
      let shortStockLabel = rawDisplayName.includes("(") ? rawDisplayName.split("(")[0].trim() : rawDisplayName;
      if (shortStockLabel.length > 16) {
        shortStockLabel = stock.ticker.replace(".NS", "");
      }

      const traceStock = {
        x: dates,
        y: stockReturns,
        mode: "lines",
        name: shortStockLabel,
        line: { color: stockColor, width: 2.4 },
        customdata: stockCloses,
        hovertemplate: `<b>${shortStockLabel}</b>: %{y:+.2f}% (₹%{customdata:,.2f})<extra></extra>`
      };

      const traceNifty = {
        x: dates,
        y: niftyReturns,
        mode: "lines",
        name: "NIFTY 50",
        line: { color: "#14183f", width: 1.8, dash: "dot" },
        customdata: niftyCloses,
        hovertemplate: "<b>NIFTY 50</b>: %{y:+.2f}% (%{customdata:,.1f})<extra></extra>"
      };

      const layout = {
        height: 270,
        margin: { l: 10, r: 10, t: 28, b: 6 },
        paper_bgcolor: "white",
        plot_bgcolor: "white",
        font: { color: "#14183f", family: "JetBrains Mono, Menlo, Consolas, monospace" },
        xaxis: {
          showgrid: true,
          gridcolor: "#f1f3f8",
          zeroline: false,
          linecolor: "#14183f",
          tickformat: "%b %y"
        },
        yaxis: {
          gridcolor: "#e6e8ef",
          zeroline: true,
          zerolinecolor: "rgba(20, 24, 63, 0.35)",
          zerolinewidth: 1.2,
          ticksuffix: "%"
        },
        legend: {
          orientation: "h",
          y: 1.14,
          x: 1,
          xanchor: "right",
          font: { size: 11 },
          bgcolor: "rgba(255, 255, 255, 0.8)"
        },
        hovermode: "x unified",
        autosize: true
      };

      const config = {
        displayModeBar: false,
        responsive: true
      };

      Plotly.react("comparison-plot", [traceStock, traceNifty], layout, config);

      // Render 4-metric strip matching Streamlit _render_price_comparison_card
      const stockRetColor = stockLastReturn >= 0 ? "#11854a" : "#d9383a";
      const niftyRetColor = niftyLastReturn >= 0 ? "#11854a" : "#d9383a";
      const alphaColor = alpha >= 0 ? "#11854a" : "#d9383a";
      const alphaLabel = alpha >= 0 ? "Outperformed" : "Underperformed";
      let cleanName = rawDisplayName.includes("(") ? rawDisplayName.split("(")[0].trim() : rawDisplayName;
      if (cleanName.length > 12) {
        cleanName = stock.ticker.replace(".NS", "");
      }
      const startDateStr = comp.start_date || (dates.length ? dates[0] : "");

      document.getElementById("comparison-metrics").innerHTML = `
        <div class="fp-backtest-metrics">
          <div class="fp-backtest-metric">
            <div class="fp-metric-label">${cleanName} Return</div>
            <div class="fp-metric-value" style="color: ${stockRetColor};">${stockLastReturn >= 0 ? '+' : ''}${Number(stockLastReturn).toFixed(1)}%</div>
          </div>
          <div class="fp-backtest-metric">
            <div class="fp-metric-label">Nifty 50 Return</div>
            <div class="fp-metric-value" style="color: ${niftyRetColor};">${niftyLastReturn >= 0 ? '+' : ''}${Number(niftyLastReturn).toFixed(1)}%</div>
          </div>
          <div class="fp-backtest-metric">
            <div class="fp-metric-label">Alpha (vs Nifty)</div>
            <div class="fp-metric-value" style="color: ${alphaColor};">${alpha >= 0 ? '+' : ''}${Number(alpha).toFixed(1)}%</div>
          </div>
          <div class="fp-backtest-metric">
            <div class="fp-metric-label">Relative Result</div>
            <div class="fp-metric-value" style="font-size: 0.88rem; color: ${alphaColor};">${alphaLabel}</div>
          </div>
        </div>
        <div class="fp-backtest-note">Normalized performance (${currentTimeframe}) indexed from 0.0% at start (${startDateStr}).</div>
      `;
    }

    function setTimeframe(tf) {
      currentTimeframe = tf;
      document.querySelectorAll(".fp-segmented-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-tf") === tf);
      });
      renderComparisonCard(appData.stocks[currentTicker]);
    }

    /* LIVE NEWS FEED - EXACT STREAMLIT SPEC _render_live_feed_card */
    function renderFeedCard(stock) {
      const cont = document.getElementById("feed-card");
      const articles = stock.articles || [];

      const boltSvg = `
        <svg class="fp-bolt-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
      `;

      if (!articles.length) {
        cont.innerHTML = `
          <div class="fp-feed-header">
            <div class="fp-feed-title-wrap">
              ${boltSvg}
              <span class="fp-feed-title">Live News Feed</span>
            </div>
            <span class="fp-view-all">View All &rarr;</span>
          </div>
          <div class="fp-small">No live news articles available for this ticker.</div>
        `;
        return;
      }

      const itemsHtml = articles.map(a => {
        const sLabel = (a.sentiment_label || "neutral").toLowerCase();
        const pillClass = sLabel === "positive" ? "fp-pill-positive" : sLabel === "negative" ? "fp-pill-negative" : "fp-pill-neutral";
        const pillText = sLabel === "positive" ? "Positive" : sLabel === "negative" ? "Negative" : "Neutral";
        const headline = a.headline || "Untitled";
        const relTime = a.time_ago || "recently";
        const sourceUrl = (a.source_url || "").trim();

        const headlineHtml = sourceUrl
          ? `<a href="${sourceUrl}" target="_blank" rel="noopener noreferrer" class="fp-feed-headline-link">${headline}</a>`
          : `<span class="fp-feed-headline-text">${headline}</span>`;

        return `
          <div class="fp-feed-item-row">
            <div class="fp-feed-time">${relTime}</div>
            <div class="fp-feed-content">
              ${headlineHtml}
              <span class="fp-pill ${pillClass}">${pillText}</span>
            </div>
          </div>
        `;
      }).join("");

      cont.innerHTML = `
        <div class="fp-feed-header">
          <div class="fp-feed-title-wrap">
            ${boltSvg}
            <span class="fp-feed-title">Live News Feed</span>
          </div>
          <a href="#" class="fp-view-all">View All &rarr;</a>
        </div>
        <div class="fp-feed-list">${itemsHtml}</div>
      `;
    }

    /* Modals for Weekly Rankings */
    function openPopup(type) {
      const overlay = document.getElementById("modal-overlay");
      const title = document.getElementById("modal-title");
      const desc = document.getElementById("modal-desc");
      const list = document.getElementById("modal-list");

      const items = (appData.weekly_rankings || {})[type] || [];
      const isBull = type === "bullish";

      title.textContent = isBull ? "🟢 Top 5 Weekly Bullish Stocks" : "🔴 Top 5 Weekly Bearish Stocks";
      desc.textContent = "Ranked by weekly news sentiment + confluence alpha (past 7 days):";

      list.innerHTML = items.map((s, idx) => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid #f1f5f9;">
          <div>
            <div style="font-weight:700; font-size:0.92rem; color:var(--fp-navy);">#${idx+1} ${s.company} <span style="font-family:var(--fp-mono); font-size:0.75rem; color:var(--fp-gray);">(${s.ticker})</span></div>
            <div style="margin-top:4px;">
              <span class="fp-pill ${isBull ? 'fp-pill-positive' : 'fp-pill-negative'}" style="font-size:0.7rem;">News Alpha: ${s.score >= 0 ? '+' : ''}${Number(s.score).toFixed(2)}</span>
              <span style="font-size:0.75rem; color:var(--fp-gray); margin-left:6px;">${s.articles} articles</span>
            </div>
          </div>
          <button class="fp-btn fp-btn-primary" style="width:auto; padding:6px 14px; font-size:0.75rem;" onclick="selectFromPopup('${s.ticker}')">View ↗</button>
        </div>
      `).join("");

      overlay.style.display = "flex";
    }

    function closePopup() {
      document.getElementById("modal-overlay").style.display = "none";
    }

    function selectFromPopup(ticker) {
      closePopup();
      if (appData.stocks[ticker]) {
        currentTicker = ticker;
        document.getElementById("stock-select").value = ticker;
        renderAll();
      }
    }

    function exportCSV() {
      const stock = appData.stocks[currentTicker];
      if (!stock) return;
      const rows = [
        ["Ticker", "Company", "Signal", "Confluence Alpha", "Market Cap", "Price", "Headline", "Summary"],
        [stock.ticker, stock.company, stock.signal, stock.confluence_score, stock.market_cap, stock.price, `"${stock.summary_headline}"`, `"${stock.summary_body}"`]
      ];
      const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\\n");
      const link = document.createElement("a");
      link.setAttribute("href", encodeURI(csvContent));
      link.setAttribute("download", `finpulse_${stock.ticker}_${new Date().toISOString().slice(0,10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    window.onload = init;
  </script>
</body>
</html>"""

def generate_html():
    app_data_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/app_data.json"
    with open(app_data_path) as f:
        app_data = json.load(f)

    app_data_json = json.dumps(app_data, separators=(',', ':'))
    html_content = HTML_TEMPLATE.replace("__APP_DATA_JSON__", app_data_json)

    output_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully generated {output_path} (size: {len(html_content):,} bytes)")

if __name__ == "__main__":
    generate_html()
