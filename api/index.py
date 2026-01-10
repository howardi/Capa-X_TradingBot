from flask import Flask, jsonify, render_template, request, redirect, make_response, send_from_directory
import json
import os
import requests
import traceback
import time
import random
import ccxt
from datetime import datetime
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(BASE_DIR, 'frontend', 'dist')

# API Keys
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')
FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY')

app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path='')

# Initialize Exchange (Binance)
exchange = None
try:
    if BINANCE_API_KEY and BINANCE_SECRET:
        exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'} 
        })
        print("✅ Binance Authenticated")
    else:
        print("⚠️ Binance API Keys missing. Using public mode.")
        exchange = ccxt.binance({'enableRateLimit': True})
except Exception as e:
    print(f"❌ Exchange Init Error: {e}")
    exchange = ccxt.binance({'enableRateLimit': True})

# --- Helper Functions ---

def get_flutterwave_balance():
    """Fetch NGN balance from Flutterwave if configured."""
    if not FLUTTERWAVE_SECRET_KEY:
        return 0.0
    
    try:
        headers = {
            "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        # Fetch all balances
        url = "https://api.flutterwave.com/v3/balances"
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                # Find NGN wallet
                for wallet in data.get('data', []):
                    if wallet.get('currency') == 'NGN':
                        return float(wallet.get('available_balance', 0.0))
    except Exception as e:
        print(f"Flutterwave Error: {e}")
    return 0.0

# --- API Endpoints ---

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "online",
        "service": "CapaRox Trading Bot",
        "timestamp": datetime.utcnow().isoformat(),
        "authenticated": exchange.checkRequiredCredentials() if exchange else False
    })

@app.route('/api/balance')
def api_balance():
    """Fetch aggregated balances (USDT from Binance, NGN from Flutterwave)."""
    balances = {
        "USDT": 0.0,
        "NGN": 0.0,
        "BTC": 0.0,
        "ETH": 0.0
    }
    
    # 1. Fetch Crypto Balances (Binance)
    if exchange and exchange.checkRequiredCredentials():
        try:
            balance_data = exchange.fetch_balance()
            balances["USDT"] = float(balance_data.get('USDT', {}).get('free', 0.0))
            balances["BTC"] = float(balance_data.get('BTC', {}).get('free', 0.0))
            balances["ETH"] = float(balance_data.get('ETH', {}).get('free', 0.0))
        except Exception as e:
            print(f"Binance Balance Error: {e}")
    
    # 2. Fetch Fiat Balance (Flutterwave)
    balances["NGN"] = get_flutterwave_balance()
    
    return jsonify(balances)

@app.route('/api/trade', methods=['POST'])
def api_trade():
    """Execute a trade on Binance."""
    if not exchange or not exchange.checkRequiredCredentials():
        return jsonify({"error": "Exchange not authenticated. Check API keys."}), 401

    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT').replace('/', '') # Ensure format BTCUSDT
        side = data.get('side', '').lower() # buy or sell
        amount = float(data.get('amount', 0))
        price = float(data.get('price', 0))
        type = data.get('type', 'limit').lower()
        
        if side not in ['buy', 'sell']:
            return jsonify({"error": "Invalid side"}), 400
            
        if amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        # Create Order
        if type == 'market':
            order = exchange.create_order(symbol, 'market', side, amount)
        else:
            if price <= 0:
                return jsonify({"error": "Price required for limit order"}), 400
            order = exchange.create_order(symbol, 'limit', side, amount, price)
            
        return jsonify({
            "status": "success",
            "orderId": order.get('id'),
            "filled": order.get('filled'),
            "price": order.get('price', price)
        })
        
    except Exception as e:
        print(f"Trade Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/candles')
def api_candles():
    try:
        symbol = request.args.get('symbol', 'BTC/USDT')
        timeframe = request.args.get('timeframe', '1h')
        limit = int(request.args.get('limit', '100'))
        
        # CCXT handles timeframe mapping automatically
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        candles = []
        for candle in ohlcv:
            candles.append({
                'time': int(candle[0] / 1000), 
                'open': candle[1],
                'high': candle[2],
                'low': candle[3],
                'close': candle[4]
            })
            
        return jsonify(candles)
    except Exception as e:
        print(f"Candle Error: {e}")
        return jsonify([])

@app.route('/api/orderbook')
def api_orderbook():
    try:
        symbol = request.args.get('symbol', 'BTC/USDT')
        orderbook = exchange.fetch_order_book(symbol, limit=10)
        
        return jsonify({
            "bids": [{"price": x[0], "amount": x[1]} for x in orderbook['bids']],
            "asks": [{"price": x[0], "amount": x[1]} for x in orderbook['asks']]
        })
    except Exception as e:
        # Fallback Mock
        return jsonify({
            "bids": [{"price": 64000, "amount": 0.5}],
            "asks": [{"price": 64050, "amount": 0.3}]
        })

@app.route('/api/trades')
def api_trades():
    try:
        symbol = request.args.get('symbol', 'BTC/USDT')
        # Fetch public trades from exchange
        trades_data = exchange.fetch_trades(symbol, limit=20)
        
        trades = []
        for t in trades_data:
            trades.append({
                "symbol": t['symbol'],
                "side": t['side'],
                "amount": t['amount'],
                "price": t['price'],
                "timestamp": t['timestamp']
            })
            
        # Sort by latest
        trades.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify(trades)
    except Exception as e:
        return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
