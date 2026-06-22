"""
Live NAV Fetching Script for Bluestock Mutual Fund Analytics Project

This script fetches the latest and historical Net Asset Value (NAV) data for a
pre-defined list of mutual fund schemes from the public mfapi.in API.

Key Functions:
1.  Iterates through a list of 6 key AMFI scheme codes.
2.  For each scheme, constructs a request to the 'https://api.mfapi.in/mf/{scheme_code}'
    endpoint.
3.  Handles potential network errors or bad responses gracefully.
4.  Parses the JSON response to extract metadata (like scheme name) and the
    historical NAV data.
5.  Converts the NAV data into a pandas DataFrame.
6.  Enriches the DataFrame by adding 'amfi_code' and 'scheme_name' columns for
    easy identification.
7.  Saves the fetched data for each scheme into a separate CSV file in the
    'data/raw/' directory, named 'live_nav_{scheme_code}.csv'.
8.  Prints a summary for each scheme, including the number of data points fetched,
    the date range, and the most recent NAV.
9.  Includes a 1-second delay between API calls to avoid overwhelming the free API service.

This script is intended to be run to supplement the static datasets with the most
up-to-date NAV information.
"""

import requests
import pandas as pd
from pathlib import Path
import time
import sys

def fetch_nav_for_scheme(scheme_code: int, raw_data_path: Path):
    """Fetches, processes, and saves NAV data for a single scheme code."""
    api_url = f"https://api.mfapi.in/mf/{scheme_code}"
    print("-" * 50)
    print(f"Fetching data for scheme code: {scheme_code} from {api_url}")

    try:
        response = requests.get(api_url, timeout=30)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        json_data = response.json()
        
        meta = json_data.get("meta", {})
        data = json_data.get("data", [])
        
        scheme_name = meta.get("scheme_name", "Unknown Scheme")

        if not data:
            print(f"  - WARNING: No data found for {scheme_name} ({scheme_code})")
            return

        # Convert data to DataFrame
        df = pd.DataFrame(data)
        if df.empty or 'nav' not in df.columns or 'date' not in df.columns:
            print(f"  - WARNING: Data for {scheme_name} is empty or malformed.")
            return
            
        # Add metadata columns
        df['amfi_code'] = scheme_code
        df['scheme_name'] = scheme_name
        
        # Ensure correct types
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y', errors='coerce')
        df.dropna(subset=['nav', 'date'], inplace=True)

        # Save to CSV
        output_filename = f"live_nav_{scheme_code}.csv"
        output_path = raw_data_path / output_filename
        df.to_csv(output_path, index=False)

        # Print summary
        latest_nav = df.sort_values('date', ascending=False).iloc[0]
        print(f"  - Scheme Name: {scheme_name}")
        print(f"  - Success: Saved {len(df)} rows to {output_path.name}")
        print(f"  - Date Range: {df['date'].min().date()} to {df['date'].max().date()}")
        print(f"  - Latest NAV: {latest_nav['nav']} on {latest_nav['date'].date()}")

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR: API call failed for scheme {scheme_code}. Reason: {e}", file=sys.stderr)
    except (ValueError, KeyError) as e:
        print(f"  - ERROR: Failed to parse JSON response for scheme {scheme_code}. Reason: {e}", file=sys.stderr)


def main():
    """Main function to fetch NAV for all specified schemes."""
    # --- Setup Paths ---
    project_root = Path(__file__).resolve().parent.parent
    raw_data_path = project_root / "data" / "raw"
    raw_data_path.mkdir(parents=True, exist_ok=True) # Ensure directory exists

    # --- Define Schemes to Fetch ---
    scheme_codes = [
        125497,  # HDFC Top 100 Direct
        119551,  # SBI Bluechip
        120503,  # ICICI Bluechip
        118632,  # Nippon Large Cap
        119092,  # Axis Bluechip
        120841,  # Kotak Bluechip
    ]

    print("=" * 80)
    print("STARTING LIVE NAV DATA FETCH")
    print("=" * 80)

    for code in scheme_codes:
        fetch_nav_for_scheme(code, raw_data_path)
        # Be respectful to the free API
        print("  - Waiting 1 second before next call...")
        time.sleep(1)
    
    print("\n" + "=" * 80)
    print("LIVE NAV DATA FETCH COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
