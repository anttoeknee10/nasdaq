#!/usr/bin/env python3
"""
Stock Data Pipeline & Chart Generator

This script automates the download, indicator enrichment, QMD creation, 
and Quarto rendering for target stock symbols (AAPL, MSFT, NVDA) 
using TSLA as the layout template.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import subprocess

# Import downloader
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from nasdaq_downloader import download_historical_data

def enrich_data(symbol):
    input_file = f"downloads/{symbol.lower()}_all_historical.csv"
    output_file = f"downloads/{symbol.lower()}_enriched.csv"
    
    print(f"[*] Enriching data for {symbol.upper()}...")
    try:
        df = pd.read_csv(input_file)
        
        # Date parsing and sorting
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Technical indicators (SMA 20, 50, 200)
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Bollinger Bands
        df['std_20'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
        df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
        
        # Daily Return
        df['daily_return'] = df['close'].pct_change()
        
        # Format date for CSV
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        df.to_csv(output_file, index=False)
        print(f"[+] Saved enriched dataset to {output_file}")
        return True
    except Exception as e:
        print(f"[!] Error enriching data for {symbol}: {e}")
        return False

def generate_qmd(symbol, company_name, company_short):
    template_file = "plots/tsla_index.qmd"
    output_file = f"plots/{symbol.lower()}_index.qmd"
    
    print(f"[*] Generating {output_file} from template...")
    try:
        with open(template_file, "r") as f:
            content = f.read()
            
        # Specific replacements
        content = content.replace("TSLA Advanced Charting", f"{symbol.upper()} Advanced Charting")
        content = content.replace("TSLA", symbol.upper())
        content = content.replace("tsla", symbol.lower())
        content = content.replace("Tesla, Inc.", company_name)
        content = content.replace("Tesla Inc.", company_name)
        content = content.replace("Tesla", company_short)
        
        with open(output_file, "w") as f:
            f.write(content)
            
        print(f"[+] Created QMD file: {output_file}")
        return True
    except Exception as e:
        print(f"[!] Error creating QMD for {symbol}: {e}")
        return False

def run_pipeline():
    # Define stocks to process
    stocks = [
        {"symbol": "aapl", "name": "Apple Inc.", "short": "Apple"},
        {"symbol": "msft", "name": "Microsoft Corp.", "short": "Microsoft"},
        {"symbol": "nvda", "name": "NVIDIA Corp.", "short": "NVIDIA"}
    ]
    
    # Range parameters (from TSLA IPO start date to current day)
    from_date = "2010-06-29"
    to_date = datetime.today().strftime("%Y-%m-%d")
    
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("plots", exist_ok=True)
    
    for stock in stocks:
        sym = stock["symbol"]
        print("\n" + "="*50)
        print(f"Processing Stock: {sym.upper()}")
        print("="*50)
        
        # 1. Download data
        raw_file = f"downloads/{sym}_all_historical.csv"
        download_success = download_historical_data(
            symbol=sym,
            from_date=from_date,
            to_date=to_date,
            output_file=raw_file,
            source="yahoo" # Force yahoo for historical depth
        )
        
        if not download_success:
            print(f"[!] Skipping {sym.upper()} due to download error.")
            continue
            
        # 2. Enrich data
        enrich_success = enrich_data(sym)
        if not enrich_success:
            print(f"[!] Skipping {sym.upper()} due to enrichment error.")
            continue
            
        # 3. Create QMD from template
        qmd_success = generate_qmd(sym, stock["name"], stock["short"])
        if not qmd_success:
            continue
            
        # 4. Render Quarto QMD to HTML
        print(f"[*] Rendering plots/{sym}_index.qmd to HTML...")
        try:
            subprocess.run(["quarto", "render", f"plots/{sym}_index.qmd", "--to", "html"], check=True)
            print(f"[+] Successfully rendered plots/{sym}_index.html")
        except subprocess.CalledProcessError as e:
            print(f"[!] Quarto render failed for {sym.upper()}: {e}")

if __name__ == "__main__":
    run_pipeline()
