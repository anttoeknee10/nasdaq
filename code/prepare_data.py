#!/usr/bin/env python3
"""
Tesla Data Preparation & Technical Indicators

This script loads the historical TSLA stock data, calculates moving averages
and other technical indicators, and saves the enriched dataset.
"""

import pandas as pd
import numpy as np

def prepare_data():
    input_file = "downloads/tsla_all_historical.csv"
    output_file = "downloads/tsla_enriched.csv"
    
    print(f"[*] Loading historical data from {input_file}...")
    try:
        df = pd.read_csv(input_file)
        
        # Ensure correct date format and sorting
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        print("[*] Calculating moving averages...")
        # 20-day, 50-day, and 200-day Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        print("[*] Calculating Bollinger Bands...")
        # 20-day rolling standard deviation
        df['std_20'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
        df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
        
        print("[*] Calculating daily returns...")
        df['daily_return'] = df['close'].pct_change()
        
        # Format the date column back to string for CSV
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        # Save enriched dataset
        df.to_csv(output_file, index=False)
        print(f"[+] Enriched dataset saved to {output_file}")
        
        # Display sample
        print("\nFirst few rows of enriched data:")
        print(df[['date', 'close', 'sma_20', 'sma_50', 'sma_200', 'bb_upper', 'bb_lower']].tail(5))
        return True
    except Exception as e:
        print(f"[!] Error preparing data: {e}")
        return False

if __name__ == "__main__":
    prepare_data()
