#!/usr/bin/env python3
"""
Stock Data Pipeline & Chart Generator

This script automates the download, technical indicator enrichment, QMD creation,
and Quarto rendering for the full list of 10 Nasdaq stocks, generating a single
scrollable "Stock Indices" page with events overlays and dropdown explanations.
All generated HTML elements are left-aligned to prevent Quarto Markdown parser
errors where indented HTML is parsed as code blocks.
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

# Comprehensive database of origins and historical events for all 10 stocks
STOCK_METADATA = {
    "aapl": {
        "origin": "Apple Inc. was founded in 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne. Initially focusing on personal computers, the company transformed into a consumer electronics giant with the launches of the iMac, iPod, iPhone, and iPad. Today, it is a global leader in technology, hardware design, and digital services.",
        "events": [
            {"date": "2011-08-24", "label": "Jobs Resigns / Cook CEO", "desc": "Steve Jobs resigns due to health reasons; Tim Cook is appointed CEO. Jobs passes away shortly after on October 5, 2011."},
            {"date": "2014-06-09", "label": "7-for-1 Stock Split", "desc": "Apple implements a 7-for-1 stock split to make shares more accessible to retail investors."},
            {"date": "2020-08-31", "label": "4-for-1 Stock Split", "desc": "Apple conducts another stock split (4-for-1) amid massive market expansion."},
            {"date": "2023-06-30", "label": "$3T Market Cap", "desc": "Apple becomes the first publicly traded company to close with a market capitalization exceeding $3 trillion."}
        ]
    },
    "sbux": {
        "origin": "Starbucks Corporation was founded in Seattle, Washington in 1971. Under Howard Schultz's leadership in the 1980s, the company adopted the Italian espresso bar concept, leading to rapid global expansion. Starbucks is now the world's largest coffeehouse chain, known for popularizing dark-roasted coffee and creating a 'third place' between home and work.",
        "events": [
            {"date": "2017-04-03", "label": "Johnson Appointed CEO", "desc": "Kevin Johnson takes over as CEO from long-time leader Howard Schultz, shifting focus to technology, mobile ordering, and cold beverage innovation."},
            {"date": "2020-03-12", "label": "COVID store closures", "desc": "Starbucks closes company-operated stores across North America to curb COVID-19, causing a sharp drop in short-term sales and share prices."},
            {"date": "2022-04-04", "label": "Schultz returns interim CEO", "desc": "Howard Schultz returns as interim CEO to lead a restructuring program and address growing unionization efforts."}
        ]
    },
    "msft": {
        "origin": "Microsoft Corporation was founded in 1975 by Paul Allen and Bill Gates. It dominated the personal computer operating system market with MS-DOS and Windows. Under Satya Nadella, the company successfully pivoted to cloud computing, enterprise services, and artificial intelligence, positioning it as one of the world's most valuable corporations.",
        "events": [
            {"date": "2014-02-04", "label": "Nadella appointed CEO", "desc": "Satya Nadella is named CEO, succeeding Steve Ballmer. Nadella initiates a 'cloud-first, mobile-first' strategy, reviving Microsoft's market leadership."},
            {"date": "2016-06-13", "label": "LinkedIn Acquisition", "desc": "Microsoft announces the acquisition of LinkedIn for $26.2 billion, expanding its network services."},
            {"date": "2023-01-23", "label": "OpenAI Partnership Boost", "desc": "Microsoft announces a multi-year, multi-billion dollar investment in OpenAI, accelerating the integration of generative AI into its Windows, Office, and Azure products."}
        ]
    },
    "csco": {
        "origin": "Cisco Systems, Inc. was founded in 1984 by Stanford University computer scientists Leonard Bosack and Sandy Lerner. Cisco pioneered the concept of local area networks (LAN) connecting geographically disparate computers over multiprotocol router systems. It remains a key infrastructure provider for global networking, cybersecurity, and cloud integrations.",
        "events": [
            {"date": "2015-07-26", "label": "Robbins becomes CEO", "desc": "Chuck Robbins succeeds John Chambers as CEO, accelerating Cisco's shift toward software-defined networking, cloud security, and subscription models."},
            {"date": "2020-03-11", "label": "WFH Hardware Spike", "desc": "The onset of COVID-19 drives high demand for enterprise networking hardware and Webex collaboration software to support remote work setups."},
            {"date": "2023-09-21", "label": "Splunk Acquisition Announced", "desc": "Cisco announces the acquisition of Splunk for $28 billion to bolster its data analytics, AI observability, and cybersecurity portfolios."}
        ]
    },
    "qcom": {
        "origin": "QUALCOMM Incorporated was founded in 1985 by Irwin Jacobs and a group of industry pioneers. Qualcomm pioneered CDMA wireless technology, which became the foundation for 3G, 4G, and 5G cellular communication networks. It is a leading designer of mobile system-on-chips (SoC) and cellular baseband processors.",
        "events": [
            {"date": "2019-04-16", "label": "Apple settlement rally", "desc": "Qualcomm and Apple reach an agreement to drop all worldwide litigation, signing a six-year patent license and chipset supply deal, triggering a 23% stock spike in one day."},
            {"date": "2021-06-30", "label": "Amon assumes CEO role", "desc": "Cristiano Amon takes office as CEO, pushing Qualcomm's diversification into automotive chips, internet of things (IoT), and laptops."},
            {"date": "2023-10-24", "label": "Snapdragon X Elite Launch", "desc": "Qualcomm introduces Snapdragon X Elite, a custom ARM PC processor designed to rival Apple's M-series chips, driving optimism in the PC market."}
        ]
    },
    "meta": {
        "origin": "Meta Platforms, Inc. (formerly Facebook) was founded in 2004 by Mark Zuckerberg and his Harvard roommates. Starting as a social network, it acquired Instagram, WhatsApp, and Oculus. In 2021, the company rebranded to Meta to emphasize its focus on the metaverse and next-generation spatial computing.",
        "events": [
            {"date": "2012-05-18", "label": "Facebook IPO", "desc": "Facebook goes public at $38 per share, in one of the largest tech IPOs in history, valuation initially peaking around $104 billion."},
            {"date": "2014-02-19", "label": "WhatsApp Acquisition", "desc": "Facebook announces the acquisition of mobile messaging app WhatsApp for $19 billion, cementing its mobile messaging leadership."},
            {"date": "2021-10-28", "label": "Rebranding to Meta", "desc": "Mark Zuckerberg announces the name change to Meta Platforms to signal a focus on building virtual environments."},
            {"date": "2022-11-09", "label": "Layoffs & Efficiency Pivot", "desc": "Meta announces its first mass layoff of 11,000 employees, initiating a transition to capital discipline and cost reductions, fueling a massive stock recovery."}
        ]
    },
    "amzn": {
        "origin": "Amazon.com, Inc. was founded in 1994 by Jeff Bezos as an online bookstore. It grew into the world's largest e-commerce platform and a dominant provider of cloud computing services via Amazon Web Services (AWS). Amazon also operates major digital streaming and smart home technology businesses.",
        "events": [
            {"date": "2017-06-16", "label": "Whole Foods Acquisition", "desc": "Amazon acquires Whole Foods Market for $13.7 billion, signaling a major expansion into brick-and-mortar grocery retail."},
            {"date": "2021-07-05", "label": "Bezos steps down / Jassy CEO", "desc": "Jeff Bezos officially steps down as CEO to become Executive Chairman; AWS chief Andy Jassy is appointed CEO."},
            {"date": "2022-06-06", "label": "20-for-1 Stock Split", "desc": "Amazon implements a 20-for-1 stock split and initiates a $10 billion share buyback program."}
        ]
    },
    "tsla": {
        "origin": "Tesla, Inc. was founded in 2003 by Martin Eberhard and Marc Tarpenning, with Elon Musk joining as lead investor and CEO shortly after. Tesla revolutionized the automotive market by proving electric vehicles could be fast, desirable, and practical, expanding into solar energy and battery storage systems.",
        "events": [
            {"date": "2012-06-22", "label": "Model S Deliveries Begin", "desc": "Tesla begins deliveries of its Model S sedan, the vehicle that established Tesla's premium brand and manufacturing capabilities."},
            {"date": "2020-08-31", "label": "5-for-1 Stock Split", "desc": "Tesla splits its stock 5-for-1 to handle the rapid run-up in its share price."},
            {"date": "2020-12-21", "label": "S&P 500 Inclusion", "desc": "Tesla joins the S&P 500 index after consecutive quarters of profitability, triggering heavy institutional index-buying."},
            {"date": "2022-10-27", "label": "Twitter Acquisition closes", "desc": "Elon Musk completes the purchase of Twitter, leading to selloffs of TSLA shares to fund the acquisition and concerns over executive focus."}
        ]
    },
    "amd": {
        "origin": "Advanced Micro Devices, Inc. was founded in 1969 by Jerry Sanders and colleagues. Initially a second-source manufacturer of microchips, AMD became Intel's primary competitor in x86 microprocessors and a major graphics processing unit (GPU) supplier through its acquisition of ATI Technologies in 2006.",
        "events": [
            {"date": "2014-10-08", "label": "Dr. Lisa Su CEO", "desc": "Dr. Lisa Su is appointed President and CEO, guiding AMD from near-bankruptcy to technological leadership and financial stability."},
            {"date": "2017-03-02", "label": "Zen Architecture Launch", "desc": "AMD launches its new Ryzen desktop processors based on the Zen architecture, matching Intel's performance and triggering a multi-year market share recovery."},
            {"date": "2022-02-14", "label": "Xilinx Acquisition closed", "desc": "AMD completes the acquisition of adaptive computing leader Xilinx for a record $49 billion, expanding its data center presence."}
        ]
    },
    "nflx": {
        "origin": "Netflix, Inc. was founded in 1997 by Reed Hastings and Marc Randolph as a DVD-by-mail service. Netflix launched streaming media in 2007, pioneering subscription video-on-demand. It has expanded into one of the largest media production companies in the world, distributing original content globally.",
        "events": [
            {"date": "2013-02-01", "label": "House of Cards launch", "desc": "Netflix releases its first major original drama series, 'House of Cards', proving the viability of streaming-only original programming."},
            {"date": "2020-03-16", "label": "COVID Lockdown surge", "desc": "Pandemic lock-downs drive a historic wave of new signups and viewing hours, pushing Netflix to peak subscriber growth."},
            {"date": "2022-04-19", "label": "First subscriber loss", "desc": "Netflix reports a loss of 200,000 subscribers—its first quarterly decline in a decade—prompting a pivot to ad-supported plans and password-sharing crackdowns."}
        ]
    }
}

# The python charting template with integrated overlays logic
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

# 5. Overlays (Historical Events)
events_{sym} = {events_list}

for ev in events_{sym}:
    ev_date = pd.to_datetime(ev['date'])
    # Get closest trading date to prevent empty gaps on weekend/holiday events
    trading_dates = df_{sym}['date'][df_{sym}['date'] >= ev_date]
    if not trading_dates.empty:
        actual_date = trading_dates.iloc[0]
        # Draw vertical line
        fig_{sym}.add_vline(x=actual_date, line_width=1.2, line_dash="dash", line_color="#888888", row=1, col=1)
        
        # Position label above the high price for that date
        row_data = df_{sym}[df_{sym}['date'] == actual_date]
        y_val = row_data['high'].values[0] if not row_data.empty else df_{sym}['high'].mean()
        
        fig_{sym}.add_annotation(
            x=actual_date,
            y=y_val,
            text=ev['label'],
            showarrow=True,
            arrowhead=1,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor='#888888',
            ax=0,
            ay=-40,
            font=dict(color='#ffffff', size=9),
            bgcolor='#141824',
            bordercolor='#202637',
            borderwidth=1,
            borderpad=4,
            row=1, col=1
        )

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
        
        # Fetch metadata
        meta = STOCK_METADATA.get(sym, {"origin": "", "events": []})
        events_list_str = str(meta["events"])
        
        # Format Python code cell
        python_cell = PYTHON_CELL_TEMPLATE.format(sym=sym, SYM=SYM, events_list=events_list_str)
        
        # Format dropdown content with zero leading spaces on every line to prevent Quarto code block parsing
        dropdown_html = f"""<details class="event-details">
<summary>🔍 Click to view {name} Origins & Major Price Action Drivers</summary>
<div class="event-content">
<h4>Company Origins</h4>
<p>{meta["origin"]}</p>
<h4>Key Historical Milestones & Price Events</h4>
<ul>"""
        
        for ev in meta["events"]:
            dropdown_html += f"\n<li><strong>{ev['date']} ({ev['label']}):</strong> {ev['desc']}</li>"
            
        dropdown_html += """
</ul>
</div>
</details>"""
        
        # Format toolbar HTML with zero leading spaces on every line
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

{dropdown_html}

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
        
    # 3. Clean up old individual files
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
