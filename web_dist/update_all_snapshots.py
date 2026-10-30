"""Fetch real market snapshots for all 531 NSE companies using exact streamlit_app logic."""

import sys
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI")
import streamlit_app
import nse_universe

def run():
    app_data_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/app_data.json"
    with open(app_data_path) as f:
        app_data = json.load(f)

    stocks_dict = app_data.setdefault("stocks", {})
    all_companies = nse_universe.NSE_COMPANIES  # dict: { 'Company Name': 'TICKER.NS' }
    total = len(all_companies)
    print(f"Starting snapshot fetch for {total} NSE companies...")

    def fetch_one(name, ticker):
        try:
            snap = streamlit_app.fetch_market_snapshot(ticker)
            return ticker, name, snap
        except Exception as e:
            return ticker, name, None

    t0 = time.time()
    success_count = 0

    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = [executor.submit(fetch_one, name, ticker) for name, ticker in all_companies.items()]
        for idx, fut in enumerate(as_completed(futures), 1):
            ticker, name, snap = fut.result()
            if snap:
                stock_entry = stocks_dict.setdefault(ticker, {})
                stock_entry["company"] = name
                stock_entry["ticker"] = ticker
                stock_entry["current_price"] = snap.get("current_price", "---")
                stock_entry["market_cap"] = snap.get("market_cap", "---")
                stock_entry["market_cap_category"] = snap.get("market_cap_category", "---")
                stock_entry["ticker_label"] = snap.get("ticker_label", f"NSE: {ticker.replace('.NS', '')}")
                
                # Extract numeric price if possible for calculations
                raw_p_str = snap.get("current_price", "").replace("₹", "").replace(",", "").strip()
                try:
                    stock_entry["price"] = float(raw_p_str)
                except ValueError:
                    pass

                if snap.get("current_price") != "---":
                    success_count += 1

            if idx % 50 == 0 or idx == total:
                print(f"Progress: {idx}/{total} completed ({time.time()-t0:.1f}s, {success_count} prices found)...")

    # Save to app_data.json and data.json
    with open(app_data_path, "w") as f:
        json.dump(app_data, f, indent=2, default=str)

    data_json_path = "/Users/vaibhav/Work/0. College 3st Sem/9. AIF - C /Capstone/FinPulse AI/web_dist/data.json"
    with open(data_json_path, "w") as f:
        json.dump(app_data, f, indent=2, default=str)

    print(f"Done! Successfully updated {total} snapshots in {time.time()-t0:.2f}s ({success_count} with real live prices).")

if __name__ == "__main__":
    run()
