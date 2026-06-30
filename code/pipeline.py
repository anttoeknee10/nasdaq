#!/usr/bin/env python3
"""
Stock Data Pipeline & Chart Generator

This script automates the download, technical indicator enrichment, QMD creation,
and Quarto rendering for the full list of 10 Nasdaq stocks, generating a single
scrollable "Stock Indices" page.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import subprocess

# Import downloader
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from nasdaq_downloader import download_historical_data

# The python charting template for each stock
PYTHON_CELL_TEMPLATE = """```{{python}}
#| label: chart-{sym}
#| echo: false
#| warning: false
#| message: false

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load dataset
df_{sym} = pd.read_csv("../downloads/{sym}_enriched.csv")
df_{sym}['date'] = pd.to_datetime(df_{sym}['date'])

# Create subplots
fig_{sym} = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03,
    subplot_titles=('Price & Technical Indicators', 'Volume'),
    row_width=[0.2, 0.8]
)

colors_{sym} = ['#26a69a' if row['close'] >= row['open'] else '#ef5350' for _, row in df_{sym}.iterrows()]

# 1. Candlestick
fig_{sym}.add_trace(
    go.Candlestick(
        x=df_{sym}['date'], open=df_{sym}['open'], high=df_{sym}['high'], low=df_{sym}['low'], close=df_{sym}['close'],
        name='{SYM} Price', increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350', showlegend=True
    ), row=1, col=1
)

# 2. SMAs
fig_{sym}.add_trace(go.Scatter(x=df_{sym}['date'], y=df_{sym}['sma_20'], line=dict(color='#2962ff', width=1.5), name='SMA 20', visible=True), row=1, col=1)
fig_{sym}.add_trace(go.Scatter(x=df_{sym}['date'], y=df_{sym}['sma_50'], line=dict(color='#ff9800', width=1.5), name='SMA 50', visible=True), row=1, col=1)
fig_{sym}.add_trace(go.Scatter(x=df_{sym}['date'], y=df_{sym}['sma_200'], line=dict(color='#e040fb', width=1.5), name='SMA 200', visible=True), row=1, col=1)

# 3. Bollinger Bands
fig_{sym}.add_trace(go.Scatter(x=df_{sym}['date'], y=df_{sym}['bb_upper'], line=dict(color='rgba(173, 20, 87, 0.5)', width=1, dash='dash'), name='BB Upper', visible=False), row=1, col=1)
fig_{sym}.add_trace(go.Scatter(x=df_{sym}['date'], y=df_{sym}['bb_lower'], line=dict(color='rgba(173, 20, 87, 0.5)', width=1, dash='dash'), fill='tonexty', fillcolor='rgba(173, 20, 87, 0.05)', name='BB Lower', visible=False), row=1, col=1)

# 4. Volume
fig_{sym}.add_trace(go.Bar(x=df_{sym}['date'], y=df_{sym}['volume'], name='Volume', marker=dict(color=colors_{sym}, line=dict(width=0)), opacity=1.0, showlegend=False), row=2, col=1)

fig_{sym}.update_layout(
    template='plotly_dark', paper_bgcolor='#0c101b', plot_bgcolor='#0c101b', autosize=True, dragmode='pan', margin=dict(t=45, b=40, l=60, r=40),
    xaxis=dict(
        rangeslider=dict(visible=False),
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(step="all", label="MAX")
            ]),
            bgcolor='#141824', activecolor='#2962ff', font=dict(color='#d1d4dc', size=11), bordercolor='#202637', borderwidth=1
        )
    ),
    yaxis=dict(gridcolor='#202637', zerolinecolor='#202637', tickprefix='$', title='Price (USD)', fixedrange=True),
    yaxis2=dict(gridcolor='#202637', zerolinecolor='#202637', title='Volume', fixedrange=True),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, bgcolor='rgba(0,0,0,0)')
)
fig_{sym}.update_xaxes(minallowed='2010-06-15', maxallowed='2026-07-05')
fig_{sym}.show(config={{'scrollZoom': True}})
```"""

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

def build_indices_page(stocks):
    qmd_file = "plots/stock_indices.qmd"
    print(f"[*] Building scrollable stock_indices.qmd for {len(stocks)} stocks...")
    
    # Notice: self-contained: false is used here to prevent Pandoc OOM issues when embedding 10 high-density charts.
    header = """---
title: "Stock Indices Interactive Charts"
format:
  html:
    theme: [cosmo, theme.scss]
    page-layout: full
    self-contained: false
---

<head>
  <meta name="description" content="Interactive charting for multiple stock indices on a single scrollable page.">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
</head>

<body>
"""
    
    body_sections = []
    for stock in stocks:
        sym = stock["symbol"].lower()
        SYM = stock["symbol"].upper()
        name = stock["name"]
        
        python_cell = PYTHON_CELL_TEMPLATE.format(sym=sym, SYM=SYM)
        
        section = f"""
## {name} ({SYM})

::: {{.column-screen}}
<div id="chart-container-{sym}" class="chart-wrapper">
<div class="chart-toolbar">
<div class="toolbar-left">
<span class="ticker-badge">{SYM}</span>
<span class="ticker-title">{name}</span>
<span class="divider">|</span>
<div class="indicator-buttons">
<button class="tool-btn active" id="btn-sma-{sym}" onclick="toggleIndicators('sma', '{sym}')">SMA Lines</button>
<button class="tool-btn" id="btn-bb-{sym}" onclick="toggleIndicators('bb', '{sym}')">Bollinger Bands</button>
<button class="tool-btn" id="btn-all-{sym}" onclick="toggleIndicators('all', '{sym}')">Show All</button>
<button class="tool-btn" id="btn-clear-{sym}" onclick="toggleIndicators('clear', '{sym}')">Price Only</button>
</div>
</div>
<button id="fullscreen-btn-{sym}" onclick="toggleFullscreen('{sym}')">⛶ Full Screen</button>
</div>

{python_cell}

</div>
:::

<hr/>
"""
        body_sections.append(section)
        
    footer = """
<script>
function toggleFullscreen(symbol) {
  var el = document.getElementById('chart-container-' + symbol);
  el.classList.toggle('fullscreen');
  var btn = document.getElementById('fullscreen-btn-' + symbol);
  if (el.classList.contains('fullscreen')) {
    btn.innerHTML = "🗖 Exit Full Screen";
  } else {
    btn.innerHTML = "⛶ Full Screen";
  }
  // Let Plotly adjust to new size (after transition)
  setTimeout(function() {
    window.dispatchEvent(new Event('resize'));
  }, 150);
}

function toggleIndicators(type, symbol) {
  var container = document.getElementById('chart-container-' + symbol);
  var gd = container.querySelector('.plotly-graph-div');
  if (!gd) return;
  
  var buttons = container.querySelectorAll('.indicator-buttons .tool-btn');
  buttons.forEach(function(btn) {
    btn.classList.remove('active');
  });
  
  var activeBtn = document.getElementById('btn-' + type + '-' + symbol);
  if (activeBtn) {
    activeBtn.classList.add('active');
  }
  
  if (type === 'sma') {
    Plotly.restyle(gd, { visible: true }, [1, 2, 3]);
    Plotly.restyle(gd, { visible: false }, [4, 5]);
  } else if (type === 'bb') {
    Plotly.restyle(gd, { visible: false }, [1, 2, 3]);
    Plotly.restyle(gd, { visible: true }, [4, 5]);
  } else if (type === 'all') {
    Plotly.restyle(gd, { visible: true }, [1, 2, 3, 4, 5]);
  } else if (type === 'clear') {
    Plotly.restyle(gd, { visible: false }, [1, 2, 3, 4, 5]);
  }
}
</script>

</body>
"""
    
    qmd_content = header + "\n".join(body_sections) + footer
    
    try:
        with open(qmd_file, "w") as f:
            f.write(qmd_content)
        print(f"[+] Created scrollable page: {qmd_file}")
        return True
    except Exception as e:
        print(f"[!] Error building page: {e}")
        return False

def clean_individual_pages():
    print("[*] Cleaning up old individual stock index QMDs...")
    files_to_remove = [
        "plots/aapl_index.qmd", "plots/aapl_index.html",
        "plots/msft_index.qmd", "plots/msft_index.html",
        "plots/nvda_index.qmd", "plots/nvda_index.html",
        "plots/tsla_index.qmd", "plots/tsla_index.html",
        "plots/index.html", "plots/tsla_index.quarto_ipynb",
        "plots/tsla_index.quarto_ipynb_1"
    ]
    for file in files_to_remove:
        path = os.path.join(file)
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"[+] Removed: {file}")
            except Exception as e:
                print(f"[!] Error removing {file}: {e}")

def run_pipeline():
    # Full list of 10 stocks requested by the user
    stocks = [
        {"symbol": "aapl", "name": "Apple Inc."},
        {"symbol": "sbux", "name": "Starbucks Corporation"},
        {"symbol": "msft", "name": "Microsoft Corporation"},
        {"symbol": "csco", "name": "Cisco Systems, Inc."},
        {"symbol": "qcom", "name": "QUALCOMM Incorporated"},
        {"symbol": "meta", "name": "Meta Platforms, Inc."},
        {"symbol": "amzn", "name": "Amazon.com, Inc."},
        {"symbol": "tsla", "name": "Tesla, Inc."},
        {"symbol": "amd", "name": "Advanced Micro Devices, Inc."},
        {"symbol": "nflx", "name": "Netflix, Inc."}
    ]
    
    # Range parameters (from June 29, 2010 to current day)
    from_date = "2010-06-29"
    to_date = datetime.today().strftime("%Y-%m-%d")
    
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("plots", exist_ok=True)
    
    processed_stocks = []
    for stock in stocks:
        sym = stock["symbol"].lower()
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
            source="yahoo"
        )
        
        if not download_success:
            print(f"[!] Skipping {sym.upper()} due to download error.")
            continue
            
        # 2. Enrich data
        enrich_success = enrich_data(sym)
        if not enrich_success:
            print(f"[!] Skipping {sym.upper()} due to enrichment error.")
            continue
            
        processed_stocks.append(stock)
        
    # 3. Clean up individual QMD pages to keep repository slim and prevent Quarto build overhead
    clean_individual_pages()
    
    # 4. Create the unified scrollable page
    if processed_stocks:
        build_indices_page(processed_stocks)
        
        # 5. Render the Quarto site
        print("\n" + "="*50)
        print("Rendering Quarto Website...")
        print("="*50)
        try:
            subprocess.run(["quarto", "render", "plots"], check=True)
            print("[+] Successfully rendered website!")
        except subprocess.CalledProcessError as e:
            print(f"[!] Quarto render failed: {e}")

if __name__ == "__main__":
    run_pipeline()
