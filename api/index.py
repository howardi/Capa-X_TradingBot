from flask import Flask, jsonify, render_template, request, redirect, make_response
import json
import os
import requests
import traceback
from datetime import datetime

# Robust template folder resolution for Vercel
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir, static_folder='static')

# Helper to get Bitcoin Price (Lightweight)
def get_btc_price():
    try:
        response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', timeout=2)
        data = response.json()
        return float(data['price'])
    except:
        return 0.0

@app.route('/')
def index():
    try:
        # Check for simple auth cookie
        auth = request.cookies.get('capax_auth')
        if auth == 'verified':
            return redirect('/dashboard')
        return redirect('/login')
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
        "service": "Capa-X Lite Monitor",
        "environment": "Vercel Serverless",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/analyze')
def api_analyze():
    try:
        price = get_btc_price()
        signal = "NEUTRAL"
        if price > 0:
            signal = "BUY" if (int(price) % 2 == 0) else "SELL"
        
        return jsonify({
            "symbol": "BTC/USDT",
            "price": price,
            "signal": signal,
            "confidence": "Demo Mode (Lite)",
            "note": "For deep learning inference, deploy Docker container."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
