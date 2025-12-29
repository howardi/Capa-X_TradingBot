from flask import Flask, jsonify, render_template
import json
import os
import requests
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

# Helper to get Bitcoin Price (Lightweight)
def get_btc_price():
    try:
        response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', timeout=2)
        data = response.json()
        return float(data['price'])
    except:
        return 0.0

@app.route('/')
def dashboard():
    # Fetch lightweight data for the dashboard
    btc_price = get_btc_price()
    
    # Read Mock/Repo Data for Trade History (since we can't run the full DB here)
    # We'll try to read from the committed json files if they exist
    trades = []
    try:
        trade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users', 'howardino', 'trade_history.json')
        if os.path.exists(trade_path):
            with open(trade_path, 'r') as f:
                trades = json.load(f)
                # Sort by timestamp desc and take last 5
                trades.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                trades = trades[:5]
    except Exception as e:
        print(f"Error reading trades: {e}")

    return render_template('dashboard.html', 
                           btc_price=btc_price, 
                           trades=trades,
                           server_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "online",
        "service": "Capa-X Lite Monitor",
        "environment": "Vercel Serverless",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/analyze')
def api_analyze():
    # A lightweight mock analysis endpoint
    # In a full deployment, this would trigger the AI Brain
    price = get_btc_price()
    signal = "NEUTRAL"
    if price > 0:
        # Simple dummy logic for demonstration
        signal = "BUY" if (int(price) % 2 == 0) else "SELL" # Random-ish deterministic
    
    return jsonify({
        "symbol": "BTC/USDT",
        "price": price,
        "signal": signal,
        "confidence": "Demo Mode (Lite)",
        "note": "For deep learning inference, deploy Docker container."
    })
