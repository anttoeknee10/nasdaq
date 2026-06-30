#!/usr/bin/env python3
"""
Magnificent Seven vs RSP & SPY Index Creator

This script downloads historical prices for the M7 stocks, SPY, and RSP,
normalizes them to 100% on 2020-01-02, computes the equal-weight M7 Index,
and saves the resulting comparative dataset.
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Import downloader
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from nasdaq_downloader import download_historical_data

def run_m7_pipeline():
    print("="*60)
    print("M7 VS RSP COMPARISON DATA PIPELINE")
    print("="*60)
    
    # Define Tickers
    m7_tickers = ["aapl", "msft", "nvda", "googl", "amzn", "meta", "tsla"]
    benchmarks = ["rsp", "spy"]
    all_tickers = m7_tickers + benchmarks
    
    from_date = "2020-01-02"
    to_date = datetime.today().strftime("%Y-%m-%d")
    
    os.makedirs("downloads", exist_ok=True)
    
    # Download data for all tickers
    for ticker in all_tickers:
        raw_file = f"downloads/{ticker}_m7_raw.csv"
        print(f"[*] Downloading {ticker.upper()}...")
        download_historical_data(
            symbol=ticker,
            from_date=from_date,
            to_date=to_date,
            output_file=raw_file,
            source="yahoo"
        )
        
    # Read and align prices
    aligned_data = {}
    
    for ticker in all_tickers:
        file_path = f"downloads/{ticker}_m7_raw.csv"
        if not os.path.exists(file_path):
            print(f"[!] Warning: Raw file for {ticker.upper()} is missing. Skipping.")
            continue
            
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Keep only date and close
        df = df[['date', 'close']].rename(columns={'close': ticker})
        aligned_data[ticker] = df

    # Merge all datasets on Date
    df_merged = None
    for ticker, df in aligned_data.items():
        if df_merged is None:
            df_merged = df
        else:
            df_merged = pd.merge(df_merged, df, on='date', how='inner')
            
    if df_merged is None or df_merged.empty:
        print("[!] Error: No overlapping data rows found for M7 stocks.")
        return False
        
    df_merged = df_merged.sort_values('date').reset_index(drop=True)
    
    # Base row (2020-01-02 or the closest available date)
    base_idx = 0
    base_date = df_merged.iloc[base_idx]['date'].strftime('%Y-%m-%d')
    print(f"[+] Base Date for Normalization: {base_date}")
    
    # Normalize each column to 100 on the base date
    normalized_df = pd.DataFrame()
    normalized_df['date'] = df_merged['date']
    
    for col in all_tickers:
        if col in df_merged.columns:
            base_val = df_merged.loc[base_idx, col]
            # Normalize to 100
            normalized_df[col] = (df_merged[col] / base_val) * 100
            
    # Calculate Equal-Weight Magnificent Seven Index (average of normalized values)
    normalized_df['m7_index'] = normalized_df[m7_tickers].mean(axis=1)
    
    # Save comparison data
    output_file = "downloads/m7_comparison.csv"
    normalized_df.to_csv(output_file, index=False)
    print(f"[+] Saved comparative dataset to {output_file}")
    
    # Print sample
    print("\nFirst 5 rows of normalized comparison data:")
    print(normalized_df[['date', 'm7_index', 'spy', 'rsp']].head())
    print("\nLast 5 rows of normalized comparison data:")
    print(normalized_df[['date', 'm7_index', 'spy', 'rsp']].tail())
    return True

if __name__ == "__main__":
    run_m7_pipeline()
