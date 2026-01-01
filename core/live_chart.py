import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import websockets
import asyncio
import json
import threading
import argparse
import logging
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set Console Title for Process Management
import sys
import ctypes
if sys.platform == 'win32':
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("Binance Live Chart Service")
    except:
        pass

# Global DataFrame to store price data
price_df = pd.DataFrame(columns=["t", "o", "h", "l", "c", "v"])

def parse_args():
    parser = argparse.ArgumentParser(description="Binance Live Chart Service")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Trading pair (e.g., BTCUSDT)")
    parser.add_argument("--interval", type=str, default="1m", help="Timeframe (e.g., 1m)")
    parser.add_argument("--port", type=int, default=8050, help="Dash server port")
    return parser.parse_args()

def fetch_initial_data(symbol, interval):
    global price_df
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit=100"
        logging.info(f"Fetching initial data from {url}")
        response = requests.get(url)
        data = response.json()
        
        rows = []
        for k in data:
            # [time, open, high, low, close, volume, ...]
            rows.append({
                "t": pd.to_datetime(k[0], unit="ms"),
                "o": float(k[1]),
                "h": float(k[2]),
                "l": float(k[3]),
                "c": float(k[4]),
                "v": float(k[5]),
            })
        
        price_df = pd.DataFrame(rows)
        logging.info(f"Loaded {len(price_df)} initial candles.")
    except Exception as e:
        logging.error(f"Failed to fetch initial data: {e}")

async def stream_klines(symbol, interval):
    global price_df
    ws_url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{interval}"
    
    logging.info(f"Connecting to {ws_url}...")
    
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    k = data["k"]
                    
                    t = pd.to_datetime(k["T"], unit="ms")
                    row = {
                        "t": t,
                        "o": float(k["o"]),
                        "h": float(k["h"]),
                        "l": float(k["l"]),
                        "c": float(k["c"]),
                        "v": float(k["v"]),
                    }
                    
                    # Update DataFrame logic
                    if not price_df.empty and price_df.iloc[-1]["t"] == t:
                        # Update last row safely
                        price_df.iloc[-1] = list(row.values())
                    else:
                        # Append new row
                        new_row_df = pd.DataFrame([row])
                        price_df = pd.concat([price_df, new_row_df], ignore_index=True).tail(500)
                    
        except Exception as e:
            logging.error(f"WebSocket Error: {e}")
            await asyncio.sleep(5) # Retry delay

def start_websocket_loop(symbol, interval):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(stream_klines(symbol, interval))

# Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id='live-graph', animate=False),
    dcc.Interval(
        id='graph-update',
        interval=1000, # 1 second
        n_intervals=0
    )
], style={'backgroundColor': '#0E1117', 'height': '100vh', 'margin': '0'}) 

@app.callback(Output('live-graph', 'figure'),
              [Input('graph-update', 'n_intervals')])
def update_graph_scatter(n):
    global price_df
    if price_df.empty:
        # Return empty dark chart
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='#0E1117',
            plot_bgcolor='#0E1117'
        )
        return fig

    # Create Candlestick
    fig = go.Figure(data=[go.Candlestick(
        x=price_df['t'],
        open=price_df['o'],
        high=price_df['h'],
        low=price_df['l'],
        close=price_df['c']
    )])

    last_price = price_df.iloc[-1]['c']
    color = "green" if price_df.iloc[-1]['c'] >= price_df.iloc[-1]['o'] else "red"

    fig.update_layout(
        title=f"Live Price: {last_price:.2f}",
        xaxis_title=None,
        yaxis_title="Price (USDT)",
        template="plotly_dark",
        paper_bgcolor='#0E1117',
        plot_bgcolor='#0E1117',
        margin=dict(l=40, r=40, t=40, b=40),
        height=600,
        xaxis_rangeslider_visible=False
    )
    
    return fig

if __name__ == '__main__':
    args = parse_args()
    
    # Fetch initial history
    fetch_initial_data(args.symbol, args.interval)
    
    # Start WebSocket in a separate thread
    t = threading.Thread(target=start_websocket_loop, args=(args.symbol, args.interval))
    t.daemon = True
    t.start()
    
    # Start Dash Server
    # Suppress Flask banner
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    print(f"Starting Live Chart on port {args.port} for {args.symbol} {args.interval}")
    try:
        app.run_server(debug=False, port=args.port, host='0.0.0.0')
    except Exception as e:
        print(f"Failed to start Dash server: {e}")
        # Optionally try next port or exit
        sys.exit(1)
