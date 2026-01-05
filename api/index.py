from flask import Flask, jsonify, render_template, request, redirect, make_response
import json
import os
import requests
import traceback
import time
from datetime import datetime

# Robust template folder resolution for Vercel
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir, static_folder='static')

def get_price(symbol='BTCUSDT'):
    symbol = symbol.upper()
    
    # 1. Try Binance.com
    for i in range(2):
        try:
            url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
            response = requests.get(url, timeout=2)
            response.raise_for_status()
            data = response.json()
            return float(data['price'])
        except:
            time.sleep(0.1)

    # 2. Try Binance.US (Good for US servers)
    try:
        url = f'https://api.binance.us/api/v3/ticker/price?symbol={symbol}'
        response = requests.get(url, timeout=2)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except:
        pass

    # 3. Try CoinGecko (Mapping needed)
    try:
        cg_map = {'BTCUSDT': 'bitcoin', 'ETHUSDT': 'ethereum', 'BNBUSDT': 'binancecoin'}
        cg_id = cg_map.get(symbol)
        if cg_id:
            url = f'https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd'
            response = requests.get(url, timeout=2)
            response.raise_for_status()
            data = response.json()
            if cg_id in data and 'usd' in data[cg_id]:
                return float(data[cg_id]['usd'])
    except:
        pass

    # 4. Try Kraken (Mapping needed)
    try:
        k_map = {'BTCUSDT': 'XBTUSD', 'ETHUSDT': 'ETHUSD'}
        pair = k_map.get(symbol)
        if pair:
            url = f'https://api.kraken.com/0/public/Ticker?pair={pair}'
            response = requests.get(url, timeout=2)
            response.raise_for_status()
            data = response.json()
            if 'result' in data:
                # Kraken returns a dictionary with the pair name as key (which might differ slightly from request)
                # We iterate to find the first key
                key = list(data['result'].keys())[0]
                # 'c' is the last trade closed array, first element is price
                return float(data['result'][key]['c'][0])
    except:
        pass

    return 0.0

# Helper to get Bitcoin Price (Lightweight)
def get_btc_price():
    return get_price('BTCUSDT')

def get_exchange_health():
    results = []
    try:
        import time
        start = time.perf_counter()
        r = requests.get('https://api.binance.com/api/v3/ping', timeout=2)
        latency = int((time.perf_counter() - start) * 1000)
        results.append({"name": "Binance", "status": "ok" if r.status_code == 200 else "maintenance", "latency_ms": latency})
    except:
        results.append({"name": "Binance", "status": "maintenance", "latency_ms": None})
    try:
        import time
        start = time.perf_counter()
        r = requests.get('https://api.bitfinex.com/v2/platform/status', timeout=2)
        latency = int((time.perf_counter() - start) * 1000)
        s = "ok"
        try:
            arr = r.json()
            s = "ok" if isinstance(arr, list) and len(arr) > 0 and arr[0] == 1 else "maintenance"
        except:
            s = "maintenance"
        results.append({"name": "Bitfinex", "status": s if r.status_code == 200 else "maintenance", "latency_ms": latency})
    except:
        results.append({"name": "Bitfinex", "status": "maintenance", "latency_ms": None})
    try:
        import time
        start = time.perf_counter()
        r = requests.get('https://api.kraken.com/0/public/SystemStatus', timeout=2)
        latency = int((time.perf_counter() - start) * 1000)
        s = "maintenance"
        try:
            data = r.json()
            status_raw = data.get('result', {}).get('status')
            s = "ok" if status_raw == 'online' else "maintenance"
        except:
            s = "maintenance"
        results.append({"name": "Kraken", "status": s if r.status_code == 200 else "maintenance", "latency_ms": latency})
    except:
        results.append({"name": "Kraken", "status": "maintenance", "latency_ms": None})
    try:
        import time
        start = time.perf_counter()
        r = requests.get('https://api.toobit.com/api/v1/ping', timeout=2)
        latency = int((time.perf_counter() - start) * 1000)
        results.append({"name": "Toobit", "status": "ok" if r.status_code == 200 else "maintenance", "latency_ms": latency})
    except:
        results.append({"name": "Toobit", "status": "maintenance", "latency_ms": None})
    try:
        import time
        start = time.perf_counter()
        r = requests.get('https://api.hashkey.global/api/v1/ping', timeout=2)
        latency = int((time.perf_counter() - start) * 1000)
        results.append({"name": "HashKey", "status": "ok" if r.status_code == 200 else "maintenance", "latency_ms": latency})
    except:
        results.append({"name": "HashKey", "status": "maintenance", "latency_ms": None})
    return results

@app.route('/')
def index():
    try:
        # Check for simple auth cookie
        auth = request.cookies.get('capax_auth')
        if auth == 'verified':
            return redirect('/dashboard')
        btc_price = get_btc_price()
        status_payload = {
            "status": "online",
            "service": "CapacityBay Lite Monitor",
            "environment": "Vercel Serverless",
            "timestamp": datetime.utcnow().isoformat()
        }
        return render_template(
            'status.html',
            btc_price=btc_price,
            status=status_payload,
            server_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            exchange_health=get_exchange_health()
        )
    except Exception:
        return f"<pre>Error in Index: {traceback.format_exc()}</pre>", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            password = request.form.get('password')
            # Simple hardcoded check for Lite mode
            if password == 'admin':
                resp = make_response(redirect('/dashboard'))
                resp.set_cookie('capax_auth', 'verified', max_age=3600*24)
                return resp
            else:
                return render_template('login.html', error="Invalid Access Code")
        return render_template('login.html')
    except Exception:
        return f"<pre>Error in Login: {traceback.format_exc()}</pre>", 500

@app.route('/logout')
def logout():
    resp = make_response(redirect('/login'))
    resp.set_cookie('capax_auth', '', expires=0)
    return resp

@app.route('/dashboard')
def dashboard():
    try:
        # Simple Auth Check
        auth = request.cookies.get('capax_auth')
        if auth != 'verified':
            return redirect('/login')

        # Fetch lightweight data for the dashboard
        btc_price = get_btc_price()
        
        # Read Mock/Repo Data for Trade History
        trades = []
        try:
            # Try multiple paths to be safe on Vercel
            base_dir = os.path.dirname(os.path.dirname(__file__)) # Up one level from api/
            trade_path = os.path.join(base_dir, 'data', 'users', 'howardino', 'trade_history.json')
            
            if os.path.exists(trade_path):
                with open(trade_path, 'r') as f:
                    trades = json.load(f)
                    trades.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                    trades = trades[:5]
        except Exception as e:
            print(f"Error reading trades: {e}")

        return render_template('dashboard.html', 
                               btc_price=btc_price, 
                               trades=trades,
                               server_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
    except Exception:
        return f"<pre>Error in Dashboard: {traceback.format_exc()}</pre>", 500

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "online",
        "service": "CapacityBay Lite Monitor",
        "environment": "Vercel Serverless",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/status')
def status_page():
    try:
        btc_price = get_btc_price()
        status_payload = {
            "status": "online",
            "service": "CapacityBay Lite Monitor",
            "environment": "Vercel Serverless",
            "timestamp": datetime.utcnow().isoformat()
        }
        return render_template(
            'status.html',
            btc_price=btc_price,
            status=status_payload,
            server_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            exchange_health=get_exchange_health()
        )
    except Exception:
        return f"<pre>Error in Status: {traceback.format_exc()}</pre>", 500

@app.route('/api/analyze')
def api_analyze():
    try:
        timeframe = request.args.get('timeframe', '1h')
        price = get_btc_price()
        
        # Simple Mock Logic sensitive to price to seem "real"
        # In Docker mode, this would call the actual ML model
        signal = "NEUTRAL"
        if price > 0:
            # Create a pseudo-random determination based on price + timeframe len
            # This ensures consistent results for same price/timeframe but variety across them
            seed = int(price) + len(timeframe)
            if seed % 3 == 0:
                signal = "BUY"
            elif seed % 3 == 1:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
        
        return jsonify({
            "symbol": "BTC/USDT",
            "timeframe": timeframe,
            "price": price,
            "signal": signal,
            "confidence": "Demo Mode (Lite)",
            "note": f"Analysis based on {timeframe} candles. Deploy Docker for full ML."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/price')
def api_price():
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        price = get_price(symbol)
        return jsonify({
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exchange-health')
def api_exchange_health():
    try:
        return jsonify({"exchanges": get_exchange_health(), "timestamp": datetime.utcnow().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
