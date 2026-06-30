#!/usr/bin/env python3
"""
Stock Historical Data Downloader

This script fetches historical stock price data directly from Nasdaq's internal API
or Yahoo Finance (via yfinance) and saves it as a cleaned CSV file.
"""

import sys
import argparse
import requests
import io
import pandas as pd
from datetime import datetime, timedelta

def clean_value(val):
    """Remove dollar signs, commas, and other formatting characters."""
    if not isinstance(val, str):
        return val
    val = val.replace('$', '').replace(',', '').strip()
    if not val:
        return None
    try:
        if '.' in val:
            return float(val)
        return int(val)
    except ValueError:
        return val

def download_from_yfinance(symbol, from_date, to_date, output_file):
    """
    Fetch historical data from Yahoo Finance via the yfinance library.
    Used for dates exceeding 10 years or as a robust fallback.
    """
    print(f"[*] Querying Yahoo Finance (via yfinance) for '{symbol.upper()}' from {from_date} to {to_date}...")
    try:
        import yfinance as yf
        
        # Download data using yfinance
        df = yf.download(symbol.upper(), start=from_date, end=to_date)
        
        if df.empty:
            print("[!] Warning: Zero rows returned from yfinance.")
            return False
            
        print(f"[+] Successfully fetched {len(df)} records from yfinance. Processing data...")
        
        # Reset index to make Date a column
        df = df.reset_index()
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Standardize columns to lowercase to match Nasdaq schema
        df.columns = [c.lower() for c in df.columns]
        
        # Format the date column to YYYY-MM-DD
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # Sort chronologically
        df = df.sort_values('date').reset_index(drop=True)
        
        # Reorder columns: Date first, then Open, High, Low, Close, Volume
        cols_order = ['date', 'open', 'high', 'low', 'close', 'volume']
        cols_present = [c for c in cols_order if c in df.columns]
        extra_cols = [c for c in df.columns if c not in cols_present]
        df = df[cols_present + extra_cols]
        
        df.to_csv(output_file, index=False)
        print(f"[+] Dataset saved to {output_file}")
        print("\nFirst 5 rows:")
        print(df.head())
        print("\nSummary Statistics:")
        print(df.describe())
        return True
        
    except Exception as e:
        print(f"[!] yfinance fetch failed: {e}")
        return False

def download_historical_data(symbol, from_date, to_date, output_file=None, source="nasdaq"):
    """
    Fetch historical data for a given symbol and date range, then save to CSV.
    """
    # Determine the default output file path
    if not output_file:
        output_file = f"{symbol.lower()}_historical_{from_date}_to_{to_date}.csv"
        
    # Check if start date is more than 10 years ago (approx. 3652 days)
    from_date_dt = datetime.strptime(from_date, '%Y-%m-%d')
    ten_years_ago = datetime.today() - timedelta(days=3652)
    
    if from_date_dt < ten_years_ago and source == "nasdaq":
        print(f"[!] Nasdaq API only supports the last 10 years of historical data.")
        print(f"    Your start date ({from_date}) is older. Automatically switching source to Yahoo Finance...")
        source = "yahoo"
        
    if source == "yahoo":
        return download_from_yfinance(symbol, from_date, to_date, output_file)
        
    url = f"https://api.nasdaq.com/api/quote/{symbol.upper()}/historical"
    
    # Nasdaq internal API params
    params = {
        'assetclass': 'stocks',
        'fromdate': from_date,
        'todate': to_date,
        'limit': '9999'  # Fetch a large number of records in one go
    }
    
    # Headers to mimic a browser request
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.nasdaq.com',
        'referer': 'https://www.nasdaq.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"[*] Querying Nasdaq API for '{symbol.upper()}' from {from_date} to {to_date}...")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code != 200:
            print(f"[!] Error: Received status code {response.status_code} from Nasdaq API.")
            print(response.text[:500])
            print("[*] Attempting fallback to Yahoo Finance (yfinance)...")
            return download_from_yfinance(symbol, from_date, to_date, output_file)
            
        data = response.json()
        
        # Check for error status in the response payload
        status = data.get('status', {})
        if status.get('rCode') != 200:
            print(f"[!] Nasdaq API Error: {status.get('bCodeMessage', 'Unknown error')}")
            print("[*] Attempting fallback to Yahoo Finance (yfinance)...")
            return download_from_yfinance(symbol, from_date, to_date, output_file)
            
        payload = data.get('data')
        if not payload or 'tradesTable' not in payload or 'rows' not in payload['tradesTable']:
            print("[!] Warning: No data rows returned from Nasdaq.")
            print("[*] Attempting fallback to Yahoo Finance (yfinance)...")
            return download_from_yfinance(symbol, from_date, to_date, output_file)
            
        rows = payload['tradesTable']['rows']
        if not rows:
            print("[!] Warning: Zero rows returned from Nasdaq.")
            print("[*] Attempting fallback to Yahoo Finance (yfinance)...")
            return download_from_yfinance(symbol, from_date, to_date, output_file)
            
        print(f"[+] Successfully fetched {len(rows)} records from Nasdaq. Processing data...")
        
        # Parse into a pandas DataFrame
        df = pd.DataFrame(rows)
        
        # Clean price and volume columns
        for col in ['close', 'volume', 'open', 'high', 'low']:
            if col in df.columns:
                df[col] = df[col].apply(clean_value)
                
        # Parse date and sort chronologically
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
            df = df.sort_values('date').reset_index(drop=True)
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
        # Reorder columns: Date first, then Open, High, Low, Close, Volume
        cols_order = ['date', 'open', 'high', 'low', 'close', 'volume']
        cols_present = [c for c in cols_order if c in df.columns]
        extra_cols = [c for c in df.columns if c not in cols_present]
        df = df[cols_present + extra_cols]
        
        df.to_csv(output_file, index=False)
        print(f"[+] Dataset saved to {output_file}")
        print("\nFirst 5 rows:")
        print(df.head())
        print("\nSummary Statistics:")
        print(df.describe())
        
        return True
        
    except requests.exceptions.Timeout:
        print("[!] Error: Nasdaq request timed out.")
        print("[*] Attempting fallback to Yahoo Finance (yfinance)...")
        return download_from_yfinance(symbol, from_date, to_date, output_file)
    except requests.exceptions.RequestException as e:
        print(f"[!] Network error: {e}")
        print("[*] Attempting fallback to Yahoo Finance (yfinance)...")
        return download_from_yfinance(symbol, from_date, to_date, output_file)
    except Exception as e:
        print(f"[!] Unexpected error occurred while parsing Nasdaq data: {e}")
        print("[*] Attempting fallback to Yahoo Finance (yfinance)...")
        return download_from_yfinance(symbol, from_date, to_date, output_file)

def main():
    parser = argparse.ArgumentParser(description="Download stock historical data from Nasdaq or Yahoo Finance API")
    parser.add_argument("symbol", help="Stock ticker symbol (e.g., AAPL, MSFT, TSLA)")
    parser.add_argument("--from-date", help="Start date (YYYY-MM-DD). Defaults to 1 year ago.", default=None)
    parser.add_argument("--to-date", help="End date (YYYY-MM-DD). Defaults to today.", default=None)
    parser.add_argument("-o", "--output", help="Output CSV path. Defaults to <symbol>_historical_<start>_to_<end>.csv", default=None)
    parser.add_argument("--source", choices=["nasdaq", "yahoo"], default="nasdaq", 
                        help="Data source. 'nasdaq' has a 10-year limit; 'yahoo' goes back to IPO. Defaults to 'nasdaq' (auto-falls back if date range exceeds 10 years).")
    
    args = parser.parse_args()
    
    # Calculate default dates if not provided
    to_date = args.to_date
    if not to_date:
        to_date = datetime.today().strftime('%Y-%m-%d')
        
    from_date = args.from_date
    if not from_date:
        # Default to 1 year ago
        one_year_ago = datetime.today() - timedelta(days=365)
        from_date = one_year_ago.strftime('%Y-%m-%d')
        
    # Validate date formats
    try:
        datetime.strptime(from_date, '%Y-%m-%d')
        datetime.strptime(to_date, '%Y-%m-%d')
    except ValueError:
        print("[!] Error: Date formats must be YYYY-MM-DD.")
        sys.exit(1)
        
    download_historical_data(args.symbol, from_date, to_date, args.output, args.source)

if __name__ == "__main__":
    main()
