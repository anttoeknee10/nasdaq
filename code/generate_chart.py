#!/usr/bin/env python3
"""
Tesla Advanced Chart Generator

This script generates an interactive, high-performance financial chart
modeled after Nasdaq's advanced charting interface using Plotly.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def generate_chart():
    df = pd.read_csv("downloads/tsla_enriched.csv")
    df['date'] = pd.to_datetime(df['date'])
    
    # Create subplots: Price (row 1) and Volume (row 2)
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03,
        subplot_titles=('Price & Technical Indicators', 'Volume'),
        row_width=[0.2, 0.8]  # Row 2 (Volume) is 20%, Row 1 (Price) is 80%
    )
    
    # Determine candle colors (green if Close >= Open, else red)
    colors = ['#089981' if row['close'] >= row['open'] else '#f23645' for _, row in df.iterrows()]
    
    # 1. Add Candlestick trace (Row 1)
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='TSLA Price',
            increasing_line_color='#089981', 
            decreasing_line_color='#f23645',
            increasing_fillcolor='#089981',
            decreasing_fillcolor='#f23645',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # 2. Add SMA Lines (Row 1)
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['sma_20'],
            line=dict(color='#2962ff', width=1.5),
            name='SMA 20',
            visible=True
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['sma_50'],
            line=dict(color='#ff9800', width=1.5),
            name='SMA 50',
            visible=True
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['sma_200'],
            line=dict(color='#e040fb', width=1.5),
            name='SMA 200',
            visible=True
        ),
        row=1, col=1
    )
    
    # 3. Add Bollinger Bands (Row 1)
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['bb_upper'],
            line=dict(color='rgba(173, 20, 87, 0.4)', width=1, dash='dash'),
            name='BB Upper',
            visible=False
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['bb_lower'],
            line=dict(color='rgba(173, 20, 87, 0.4)', width=1, dash='dash'),
            fill='tonexty',  # Fill area between Upper and Lower bands
            fillcolor='rgba(173, 20, 87, 0.05)',
            name='BB Lower',
            visible=False
        ),
        row=1, col=1
    )
    
    # 4. Add Volume bars (Row 2)
    fig.add_trace(
        go.Bar(
            x=df['date'], y=df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.8,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Update layout and styling for a modern dark theme
    fig.update_layout(
        template='plotly_dark',
        title={
            'text': '<b>Tesla Inc. (TSLA) Advanced Charting</b>',
            'y': 0.96, 'x': 0.05,
            'xanchor': 'left', 'yanchor': 'top',
            'font': {'size': 22, 'color': '#ffffff', 'family': 'Outfit, sans-serif'}
        },
        paper_bgcolor='#131722',  # Premium charting charcoal
        plot_bgcolor='#131722',
        height=800,
        margin=dict(t=80, b=40, l=60, r=40),
        xaxis=dict(
            rangeslider=dict(visible=False),  # Hide default rangeslider to keep subplots clean
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                    dict(step="all", label="MAX")
                ]),
                bgcolor='#1e222d',
                activecolor='#2962ff',
                font=dict(color='#d1d4dc', size=11),
                bordercolor='#2a2e39',
                borderwidth=1
            )
        ),
        yaxis=dict(
            gridcolor='#2a2e39',
            zerolinecolor='#2a2e39',
            tickprefix='$',
            title='Price (USD)'
        ),
        yaxis2=dict(
            gridcolor='#2a2e39',
            zerolinecolor='#2a2e39',
            title='Volume'
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(0,0,0,0)',
            bordercolor='rgba(0,0,0,0)'
        ),
        # Add indicator toggle buttons at the top left
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.05,
                y=1.12,
                showactive=True,
                bgcolor='#1e222d',
                font=dict(color='#d1d4dc', size=12),
                bordercolor='#2a2e39',
                pad=dict(r=10, t=10),
                buttons=list([
                    dict(
                        label="Toggle SMA Lines",
                        method="update",
                        args=[
                            {"visible": [True, True, True, True, False, False, True]}, # Visibility list for traces
                            {"title": "<b>Tesla Inc. (TSLA) - Simple Moving Averages</b>"}
                        ]
                    ),
                    dict(
                        label="Toggle Bollinger Bands",
                        method="update",
                        args=[
                            {"visible": [True, False, False, False, True, True, True]},
                            {"title": "<b>Tesla Inc. (TSLA) - Bollinger Bands</b>"}
                        ]
                    ),
                    dict(
                        label="Show All Indicators",
                        method="update",
                        args=[
                            {"visible": [True, True, True, True, True, True, True]},
                            {"title": "<b>Tesla Inc. (TSLA) - All Indicators</b>"}
                        ]
                    ),
                    dict(
                        label="Clear Indicators",
                        method="update",
                        args=[
                            {"visible": [True, False, False, False, False, False, True]},
                            {"title": "<b>Tesla Inc. (TSLA) - Price Action Only</b>"}
                        ]
                    )
                ])
            )
        ]
    )
    
    # Save chart as HTML
    output_html = "downloads/tsla_advanced_chart.html"
    fig.write_html(output_html, include_plotlyjs='cdn', full_html=False)
    print(f"[+] Advanced chart generated successfully and saved to {output_html}")
    return fig

if __name__ == "__main__":
    generate_chart()
