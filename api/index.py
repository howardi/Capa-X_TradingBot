import os
import time
import asyncio
import random
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, url_for, redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from authlib.integrations.flask_client import OAuth
from api.db import get_db_connection, init_db
from api.services.payment_service import PaymentService
from api.services.exchange_service import ExchangeService
from api.services.wallet_service import WalletService
from api.services.health_monitor import HealthMonitor
from api.services.auth_service import AuthService
from api.services.strategy_service import StrategyService

# Determine absolute path to frontend/dist
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, 'frontend', 'dist')

app = Flask(__name__, static_folder=DIST_DIR, static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key_change_me')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
CORS(app)

# Initialize DB
init_db()

# Services
payment_service = PaymentService()
wallet_service = WalletService()
auth_service = AuthService()
exchange_service = ExchangeService()
strategy_service = StrategyService()

# OAuth Setup
oauth = OAuth(app)

# Google
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# GitHub
github = oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify(error='Not found'), 404
    return send_from_directory(app.static_folder, 'index.html')

# --- Auth Routes ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    phone_number = data.get('phone_number')
    security_answer = data.get('security_answer')
    
    if not username or not email or not password or not full_name or not phone_number:
        return jsonify({"error": "Missing fields"}), 400
        
    # Simple Security Check (Math: 2 + 2 = 4)
    if str(security_answer).strip() != '4':
         return jsonify({"error": "Security check failed"}), 400
        
    result = auth_service.register_user(username, email, password, full_name, phone_number)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/auth/providers', methods=['GET'])
def get_auth_providers():
    return jsonify({
        "google": bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET')),
        "github": bool(os.getenv('GITHUB_CLIENT_ID') and os.getenv('GITHUB_CLIENT_SECRET'))
    })

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400
        
    result = auth_service.login_user(username, password)
    if "error" in result:
        return jsonify(result), 401
    return jsonify(result)

# Alias for legacy support if needed
@app.route('/api/login', methods=['POST'])
def login_alias():
    return auth_login()

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    if not email: return jsonify({"error": "Email required"}), 400
    
    result = auth_service.forgot_password(email)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    token = data.get('token')
    password = data.get('password')
    if not token or not password: return jsonify({"error": "Token and password required"}), 400
    
    result = auth_service.reset_password(token, password)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/auth/login/google')
def google_login():
    if not os.getenv('GOOGLE_CLIENT_ID') or not os.getenv('GOOGLE_CLIENT_SECRET'):
        return redirect("/login?error=Google login is not configured")
    
    # Force HTTPS redirect_uri in production
    frontend_url = os.getenv('FRONTEND_URL')
    if frontend_url:
        redirect_uri = f"{frontend_url.rstrip('/')}/api/auth/google/callback"
    else:
        redirect_uri = url_for('google_auth', _external=True)
        
    return google.authorize_redirect(redirect_uri)

@app.route('/api/auth/me')
def get_current_user():
    user = session.get('user')
    if user:
        return jsonify(user)
    return jsonify({"error": "Not authenticated"}), 401

@app.route('/api/auth/google/callback')
def google_auth():
    try:
        token = google.authorize_access_token()
        # userinfo is often included in the token response for OIDC
        user_info = token.get('userinfo')
        if not user_info:
            user_info = google.userinfo()
            
        result = auth_service.oauth_login('google', user_info)
        
        if "error" in result:
             return redirect(f"/login?error={result['error']}")
             
        # Store user in session
        session['user'] = result
        
        # Redirect to frontend login page with auth_check flag
        # Using relative path to support both local and cloud deployments
        return redirect("/login?auth_check=true")
    except Exception as e:
        print(f"Google Auth Error: {e}")
        return redirect(f"/login?error=Google login failed: {str(e)}")

@app.route('/api/auth/login/github')
def github_login():
    if not os.getenv('GITHUB_CLIENT_ID') or not os.getenv('GITHUB_CLIENT_SECRET'):
        return redirect("/login?error=GitHub login is not configured")
        
    # Force HTTPS redirect_uri in production
    frontend_url = os.getenv('FRONTEND_URL')
    if frontend_url:
        redirect_uri = f"{frontend_url.rstrip('/')}/api/auth/github/callback"
    else:
        redirect_uri = url_for('github_auth', _external=True)
        
    return github.authorize_redirect(redirect_uri)

@app.route('/api/auth/github/callback')
def github_auth():
    try:
        token = github.authorize_access_token()
        resp = github.get('user').json()
        # GitHub email might be private
        email = resp.get('email')
        if not email:
            try:
                emails = github.get('user/emails').json()
                for e in emails:
                    if e['primary']:
                        email = e['email']
                        break
            except:
                pass
        
        profile = {
            'id': str(resp['id']),
            'name': resp.get('name') or resp.get('login'),
            'email': email
        }
        result = auth_service.oauth_login('github', profile)
        
        if "error" in result:
             return redirect(f"/login?error={result['error']}")

        # Store user in session
        session['user'] = result

        # Redirect to frontend login page with auth_check flag
        return redirect("/login?auth_check=true")
    except Exception as e:
        print(f"GitHub Auth Error: {e}")
        return redirect(f"/login?error=GitHub login failed: {str(e)}")

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    username = request.args.get('username') 
    admin_secret = request.headers.get('X-Admin-Secret')
    
    conn = get_db_connection()
    c = conn.cursor()
    
    is_admin = False
    if username:
        c.execute("SELECT is_admin FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if row and row['is_admin']:
            is_admin = True
            
    if not is_admin and admin_secret != os.getenv('ADMIN_SECRET', 'admin123'):
        conn.close()
        return jsonify({"error": "Unauthorized"}), 403
        
    c.execute("SELECT id, username, email, is_admin, google_id, github_id FROM users")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(users)

@app.route('/api/analyze', methods=['GET'])
def analyze_signal():
    symbol = request.args.get('symbol', 'BTC/USDT')
    
    async def fetch_and_analyze():
        # Create local instance to avoid event loop issues with asyncio.run()
        local_service = ExchangeService()
        ohlcv = []
        try:
            exchange = await local_service.get_shared_price_source()
            # Fetch Candles (100 candles for sufficient history)
            ohlcv = await exchange.fetch_ohlcv(symbol, '1h', 100)
        except Exception as e:
            print(f"Data Fetch Failed: {e}. Using mock data.")
        finally:
            await local_service.close_shared_resources()
            
        # Fallback to Mock Data if no real data
        if not ohlcv:
            now = int(time.time())
            base_price = 95000 if 'BTC' in symbol else 2800 if 'ETH' in symbol else 100
            current_price = base_price
            for i in range(100):
                timestamp = now - ((100 - i) * 3600)
                change = (random.random() - 0.5) * (base_price * 0.02)
                open_price = current_price
                close_price = open_price + change
                high_price = max(open_price, close_price) + (random.random() * base_price * 0.005)
                low_price = min(open_price, close_price) - (random.random() * base_price * 0.005)
                volume = random.random() * 100
                
                ohlcv.append([timestamp, open_price, high_price, low_price, close_price, volume])
                current_price = close_price

        candles = []
        for c in ohlcv:
            candles.append({
                'time': c[0],
                'open': c[1],
                'high': c[2],
                'low': c[3],
                'close': c[4],
                'volume': c[5]
            })
        
        # Analyze using combined_ai strategy
        result = strategy_service.analyze('combined_ai', candles)
        return result

    try:
        result = asyncio.run(fetch_and_analyze())
        return jsonify(result)
    except Exception as e:
        print(f"Analysis Failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['GET', 'PUT'])
def user_profile():
    username = request.args.get('username')
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if request.method == 'GET':
        if not username:
             return jsonify({"error": "Username required"}), 400
        
        c.execute("SELECT username, email, full_name, phone_number FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user:
            return jsonify(dict(user))
        return jsonify({"error": "User not found"}), 404
        
    elif request.method == 'PUT':
        data = request.json
        username = data.get('username')
        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        
        if not username:
            conn.close()
            return jsonify({"error": "Username required"}), 400
            
        try:
            c.execute("UPDATE users SET full_name=?, phone_number=? WHERE username=?", 
                      (full_name, phone_number, username))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Profile updated"})
        except Exception as e:
            conn.close()
            return jsonify({"error": str(e)}), 500

# --- Exchange Routes ---

@app.route('/api/pairs', methods=['GET'])
def get_pairs():
    return jsonify([
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
        "ADA/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT", "LTC/USDT"
    ])

@app.route('/api/candles', methods=['GET'])
def get_candles():
    symbol = request.args.get('symbol', 'BTC/USDT')
    timeframe = request.args.get('timeframe', '1h')
    limit = int(request.args.get('limit', 100))
    
    now = int(time.time())
    interval_seconds = 3600
    if timeframe == '1m': interval_seconds = 60
    elif timeframe == '5m': interval_seconds = 300
    elif timeframe == '15m': interval_seconds = 900
    elif timeframe == '4h': interval_seconds = 14400
    elif timeframe == '1d': interval_seconds = 86400
    
    start_time = now - (limit * interval_seconds)
    candles = []
    
    base_price = 100
    if 'BTC' in symbol: base_price = 95000
    elif 'ETH' in symbol: base_price = 2800
    elif 'SOL' in symbol: base_price = 140
    elif 'BNB' in symbol: base_price = 600
    
    current_price = base_price
    
    for i in range(limit):
        timestamp = start_time + (i * interval_seconds)
        change = (random.random() - 0.5) * (base_price * 0.02)
        open_price = current_price
        close_price = open_price + change
        high_price = max(open_price, close_price) + (random.random() * base_price * 0.005)
        low_price = min(open_price, close_price) - (random.random() * base_price * 0.005)
        volume = random.random() * 100
        
        candles.append({
            "time": timestamp,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume
        })
        current_price = close_price
        
    return jsonify(candles)

@app.route('/api/orderbook', methods=['GET'])
def get_orderbook():
    symbol = request.args.get('symbol', 'BTC/USDT')
    base_price = 100
    if 'BTC' in symbol: base_price = 95000
    elif 'ETH' in symbol: base_price = 2800
    elif 'SOL' in symbol: base_price = 140
    
    asks = []
    bids = []
    
    for i in range(10):
        ask_price = base_price + (i * base_price * 0.0005) + (random.random() * base_price * 0.0002)
        ask_amount = random.random() * 2
        asks.append({"price": ask_price, "amount": ask_amount})
        
        bid_price = base_price - (i * base_price * 0.0005) - (random.random() * base_price * 0.0002)
        bid_amount = random.random() * 2
        bids.append({"price": bid_price, "amount": bid_amount})
        
    return jsonify({"symbol": symbol, "asks": asks, "bids": bids})

@app.route('/api/trade', methods=['POST'])
def place_trade():
    data = request.json
    username = data.get('username')
    symbol = data.get('symbol')
    side = data.get('side')
    amount = float(data.get('amount', 0))
    mode = data.get('mode', 'demo')
    
    if not username or not symbol or not side or amount <= 0:
        return jsonify({"error": "Invalid params"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Simple Mock Price for Trade
    price = 95000 if 'BTC' in symbol else 2800 if 'ETH' in symbol else 100
    
    try:
        # Check Balance Logic (Simplified for Demo)
        # In production, ExchangeService handles this
        
        c.execute("""
            INSERT INTO bot_activity (username, symbol, type, price, amount, pnl, timestamp, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, symbol, side.upper(), price, amount, 0, datetime.utcnow(), mode))
        conn.commit()
        return jsonify({"status": "success", "message": "Order Placed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/swap', methods=['POST'])
def swap_tokens():
    data = request.json
    username = data.get('username')
    from_currency = data.get('from_currency')
    to_currency = data.get('to_currency')
    amount = float(data.get('amount', 0))
    
    if not username or not from_currency or not to_currency or amount <= 0:
        return jsonify({"error": "Invalid params"}), 400
        
    result = wallet_service.swap_currency(username, from_currency, to_currency, amount)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

# --- Wallet Management Routes ---

@app.route('/api/wallet/generate', methods=['POST'])
def generate_wallet():
    data = request.json
    username = data.get('username')
    chain = data.get('chain', 'EVM') # EVM, TRON, BTC
    
    if not username:
        return jsonify({"error": "Username required"}), 400
        
    result = wallet_service.generate_wallet(username, chain)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/wallet/list', methods=['GET'])
def list_wallets():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username required"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT address, type, created_at FROM wallets WHERE username=?", (username,))
    wallets = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(wallets)

@app.route('/api/wallet/reveal', methods=['POST'])
def reveal_private_key():
    data = request.json
    username = data.get('username')
    chain = data.get('chain')
    password = data.get('password')
    
    if not username or not chain or not password:
        return jsonify({"error": "Missing fields"}), 400
        
    # Verify password first
    login_result = auth_service.login_user(username, password)
    if "error" in login_result:
        return jsonify({"error": "Invalid password"}), 401
        
    private_key = wallet_service.get_private_key(username, chain)
    if not private_key:
        return jsonify({"error": "Wallet not found"}), 404
        
    return jsonify({"private_key": private_key})

@app.route('/api/wallet/transfer', methods=['POST'])
def transfer_crypto():
    data = request.json
    username = data.get('username')
    chain = data.get('chain') # EVM, TRON, BTC
    to_address = data.get('to_address')
    amount = float(data.get('amount', 0))
    currency = data.get('currency') # ETH, USDT, BTC, etc.
    password = data.get('password') # Security check
    
    if not username or not chain or not to_address or amount <= 0 or not currency or not password:
        return jsonify({"error": "Missing fields"}), 400
        
    # Verify password
    login_result = auth_service.login_user(username, password)
    if "error" in login_result:
        return jsonify({"error": "Invalid password"}), 401
        
    result = wallet_service.withdraw_crypto(username, chain, to_address, amount, currency)
    if "error" in result:
        return jsonify(result), 400
        
    return jsonify(result)

# --- Analytics Routes ---
@app.route('/api/analytics/orderbook/<path:symbol>', methods=['GET'])
def analytics_orderbook(symbol):
    sentiment = "bullish" if random.random() > 0.5 else "bearish"
    return jsonify({
        "symbol": symbol,
        "analysis": {
            "sentiment": sentiment,
            "spread": random.random() * 10,
            "imbalance_ratio": random.random() * 2,
            "buy_wall": random.choice([True, False]),
            "sell_wall": random.choice([True, False])
        }
    })

@app.route('/api/analytics/risk', methods=['GET'])
def analytics_risk():
    return jsonify({
        "volatility": "Medium",
        "sharpe_ratio": 1.5,
        "max_drawdown": 12.5
    })

@app.route('/api/analytics/heat/<path:symbol>', methods=['GET'])
def analytics_heat(symbol):
    return jsonify({
        "symbol": symbol,
        "score": random.randint(20, 90)
    })

# --- Copy Trading Routes ---
@app.route('/api/copy-trade/traders', methods=['GET'])
def get_copy_traders():
    traders = [
        {"id": 1, "name": "CryptoKing", "followers": 1250, "pnl": 345.5, "winRate": 78, "risk": "High"},
        {"id": 2, "name": "SafeHands", "followers": 890, "pnl": 120.2, "winRate": 92, "risk": "Low"},
        {"id": 3, "name": "AlphaSignal", "followers": 2100, "pnl": 560.8, "winRate": 65, "risk": "Medium"},
        {"id": 4, "name": "WhaleWatcher", "followers": 560, "pnl": 89.4, "winRate": 81, "risk": "Medium"},
    ]
    return jsonify(traders)

@app.route('/api/copy-trade/follow', methods=['POST'])
def follow_trader():
    return jsonify({"status": "success", "message": "Now following trader!"})

# --- CMC Proxy (Mock) ---
@app.route('/api/cmc/price', methods=['GET'])
def cmc_price():
    symbol = request.args.get('symbol', 'BTC')
    price = 95000
    if symbol == 'ETH': price = 2800
    elif symbol == 'SOL': price = 140
    
    return jsonify({
        "data": {
            symbol: {
                "quote": {
                    "USD": {
                        "price": price
                    }
                }
            }
        }
    })

@app.route('/api/balance', methods=['GET'])
async def get_balance():
    username = request.args.get('username')
    mode = request.args.get('mode', 'live')
    if not username: return jsonify({"error": "Username required"}), 400
    
    # 1. Fetch Exchange Balance (Crypto)
    exchange_service = ExchangeService()
    exchange_balance = {'free': {}, 'total': {}, 'info': {}}
    
    if mode == 'live':
        # Try to get real exchange balance if connected
        try:
            exchange = await exchange_service.get_exchange_for_user(username)
            if exchange:
                exchange_balance = await exchange.fetch_balance()
        except Exception as e:
            print(f"Exchange balance fetch error: {e}")

    # 2. Fetch Fiat/Internal Balance (NGN, etc.) from DB
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT currency, balance FROM live_balances WHERE username=?", (username,))
    rows = c.fetchall()
    conn.close()

    # 3. Merge DB Balances into Exchange Balance
    # CCXT structure: {'free': {'BTC': 1.0}, 'total': {'BTC': 1.0}}
    
    for row in rows:
        currency = row['currency']
        balance = row['balance']
        
        # Initialize if not present
        if currency not in exchange_balance['free']:
            exchange_balance['free'][currency] = 0.0
        if currency not in exchange_balance['total']:
            exchange_balance['total'][currency] = 0.0
            
        # Add DB balance (assuming DB tracks 'free' balance available for use)
        exchange_balance['free'][currency] += balance
        exchange_balance['total'][currency] += balance

    return jsonify(exchange_balance)

@app.route('/api/ticker', methods=['GET'])
def get_ticker():
    symbol = request.args.get('symbol', 'BTC/USDT')
    base_prices = {'BTC': 95000, 'ETH': 2800, 'BNB': 600, 'USDT': 1.0, 'NGN': 0.00065, 'DAI': 1.0}
    try:
        base, quote = symbol.split('/')
        price = base_prices.get(base, 100) / base_prices.get(quote, 1)
        price = price * (1 + (random.random() - 0.5) * 0.001)
    except:
        price = 0.0
    return jsonify({'symbol': symbol, 'last': price})

# --- Payment & Balance Routes ---

@app.route('/api/<provider>/pay', methods=['POST'])
def initiate_payment(provider):
    data = request.json
    amount = data.get('amount')
    email = data.get('email')
    username = data.get('username')
    host_url = request.host_url
    
    if not amount or not email:
        return jsonify({"error": "Missing amount or email"}), 400
        
    if provider == 'flutterwave':
        result = payment_service.initiate_flutterwave(username, amount, email, host_url)
    elif provider == 'paystack':
        result = payment_service.initiate_paystack(username, amount, email, host_url)
    elif provider == 'stripe':
        result = payment_service.initiate_stripe(username, amount, email, host_url)
    else:
        return jsonify({"error": "Invalid provider"}), 400
        
    return jsonify(result)

@app.route('/api/flutterwave/verify', methods=['POST'])
def verify_flutterwave():
    data = request.json
    tx_ref = data.get('tx_ref')
    username = data.get('username')
    transaction_id = data.get('transaction_id')
    
    if not username:
        return jsonify({"error": "Missing username"}), 400
        
    if not tx_ref and not transaction_id:
        return jsonify({"error": "Missing tx_ref or transaction_id"}), 400
        
    # Check if input tx_ref is likely a Transaction ID (numeric) if transaction_id not explicitly provided
    if not transaction_id and str(tx_ref).isdigit():
        transaction_id = tx_ref
        
    verification = payment_service.verify_transaction('flutterwave', tx_ref, transaction_id=transaction_id)
    
    if verification.get('status') == 'success':
        amount = verification['amount']
        currency = verification['currency']
        
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT id FROM transactions WHERE tx_ref=?", (tx_ref,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "error": "Transaction already processed"})
            
        c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (username, currency))
        row = c.fetchone()
        if row:
            c.execute("UPDATE live_balances SET balance = balance + ? WHERE username=? AND currency=?", (amount, username, currency))
        else:
            c.execute("INSERT INTO live_balances (username, currency, balance) VALUES (?, ?, ?)", (username, currency, amount))
            
        c.execute("INSERT INTO transactions (username, type, currency, amount, status, tx_ref, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (username, 'deposit', currency, amount, 'success', tx_ref, datetime.utcnow()))
                  
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": f"Deposit of {amount} {currency} confirmed!"})
    else:
        return jsonify({"status": "error", "error": verification.get('message', 'Verification failed')})

@app.route('/api/paystack/verify', methods=['POST'])
def verify_paystack():
    data = request.json
    tx_ref = data.get('tx_ref')
    username = data.get('username')
    
    if not tx_ref or not username:
        return jsonify({"error": "Missing tx_ref or username"}), 400
        
    verification = payment_service.verify_transaction('paystack', tx_ref)
    
    if verification.get('status') == 'success':
        amount = verification['amount']
        currency = verification['currency']
        
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT id FROM transactions WHERE tx_ref=?", (tx_ref,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "error": "Transaction already processed"})
            
        c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (username, currency))
        row = c.fetchone()
        if row:
            c.execute("UPDATE live_balances SET balance = balance + ? WHERE username=? AND currency=?", (amount, username, currency))
        else:
            c.execute("INSERT INTO live_balances (username, currency, balance) VALUES (?, ?, ?)", (username, currency, amount))
            
        c.execute("INSERT INTO transactions (username, type, currency, amount, status, tx_ref, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (username, 'deposit', currency, amount, 'success', tx_ref, datetime.utcnow()))
                  
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": f"Deposit of {amount} {currency} confirmed!"})
    else:
        return jsonify({"status": "error", "error": verification.get('message', 'Verification failed')})

@app.route('/api/withdraw', methods=['POST'])
def withdraw_fiat():
    data = request.json
    username = data.get('username')
    amount = float(data.get('amount', 0))
    currency = data.get('currency', 'NGN')
    
    if amount <= 0: return jsonify({"error": "Invalid amount"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (username, currency))
    row = c.fetchone()
    current_balance = row['balance'] if row else 0
    
    if current_balance < amount:
        conn.close()
        return jsonify({"error": "Insufficient balance"}), 400
        
    c.execute("UPDATE live_balances SET balance = balance - ? WHERE username=? AND currency=?", (amount, username, currency))
    
    tx_ref = f"wd_{int(time.time())}_{random.randint(1000,9999)}"
    c.execute("INSERT INTO transactions (username, type, currency, amount, status, tx_ref, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (username, 'withdrawal', currency, amount, 'pending', tx_ref, datetime.utcnow()))
              
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "Withdrawal request submitted", "tx_ref": tx_ref})

# --- Crypto Wallet Routes ---
@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    data = request.json
    username = data.get('username')
    chain = data.get('chain', 'EVM')
    if not username: return jsonify({"error": "Username required"}), 400
    
    result = wallet_service.generate_wallet(username, chain)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/wallet/list', methods=['GET'])
def list_wallets():
    username = request.args.get('username')
    if not username: return jsonify({"error": "Username required"}), 400
    
    wallets = wallet_service.get_user_wallets(username)
    return jsonify({"wallets": wallets})

@app.route('/api/wallet/withdraw', methods=['POST'])
def withdraw_crypto_route():
    data = request.json
    username = data.get('username')
    amount = float(data.get('amount', 0))
    currency = data.get('currency', 'USDT')
    to_address = data.get('to_address')
    chain = data.get('chain', 'EVM')
    
    if not username or not to_address or amount <= 0:
        return jsonify({"error": "Invalid params"}), 400
        
    result = wallet_service.withdraw_crypto(username, amount, currency, to_address, chain)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

# --- Bot Config Routes ---
@app.route('/api/bot/config', methods=['GET'])
def get_bot_config():
    username = request.args.get('username')
    if not username: return jsonify({"error": "Username required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bot_settings WHERE username=?", (username,))
    settings = c.fetchone()
    
    active_trade = None
    c.execute("SELECT * FROM bot_activity WHERE username=? AND status='open' ORDER BY timestamp DESC LIMIT 1", (username,))
    active_trade = c.fetchone()
    
    c.execute("SELECT * FROM bot_activity WHERE username=? ORDER BY timestamp DESC LIMIT 5", (username,))
    history = c.fetchall()
    
    conn.close()
    
    settings = dict(settings) if settings else {}
    active_trade = dict(active_trade) if active_trade else None
    history = [dict(row) for row in history]
    
    return jsonify({
        "settings": settings,
        "active_trade": active_trade,
        "history": history
    })

@app.route('/api/bot/config', methods=['POST'])
def api_bot_configure():
    data = request.json
    username = data.get('username')
    if not username: return jsonify({"error": "Username required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM bot_settings WHERE username=?", (username,))
    exists = c.fetchone()
    
    if exists:
        query = "UPDATE bot_settings SET enabled=?, is_active=?, symbol=?, strategy=?, investment_amount=?, mode=?, risk_level=? WHERE username=?"
        params = (
            int(data.get('enabled', exists['enabled'])),
            int(data.get('enabled', exists['enabled'])),
            data.get('symbol', exists['symbol']),
            data.get('strategy', exists['strategy']),
            float(data.get('investment_amount', exists['investment_amount'])),
            data.get('mode', exists['mode']),
            data.get('risk_level', exists['risk_level']),
            username
        )
    else:
        query = "INSERT INTO bot_settings (enabled, is_active, symbol, strategy, investment_amount, mode, risk_level, username) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        params = (
            int(data.get('enabled', 0)),
            int(data.get('enabled', 0)),
            data.get('symbol', 'BTC/USDT'),
            data.get('strategy', 'advanced_ai'),
            float(data.get('investment_amount', 0)),
            data.get('mode', 'demo'),
            data.get('risk_level', 'medium'),
            username
        )
        
    c.execute(query, params)
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})

@app.route('/api/bot/toggle', methods=['POST'])
def bot_toggle():
    data = request.json
    username = data.get('username')
    enabled = data.get('enabled')
    
    if not username: return jsonify({"error": "Username required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM bot_settings WHERE username=?", (username,))
    exists = c.fetchone()
    
    if exists:
        c.execute("UPDATE bot_settings SET enabled=?, is_active=? WHERE username=?", (int(enabled), int(enabled), username))
    else:
        c.execute("INSERT INTO bot_settings (username, enabled, is_active) VALUES (?, ?, ?)", (username, int(enabled), int(enabled)))
        
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": f"Bot {'enabled' if enabled else 'disabled'}"})

@app.route('/api/orders', methods=['GET'])
def get_orders():
    username = request.args.get('username')
    mode = request.args.get('mode', 'live')
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        query = "SELECT * FROM bot_activity WHERE username=? AND mode=? ORDER BY timestamp DESC LIMIT 50"
        c.execute(query, (username, mode))
        rows = c.fetchall()
    except Exception as e:
        print(f"Error fetching orders: {e}")
        rows = []
        
    conn.close()
    
    orders = []
    for r in rows:
        row_dict = dict(r)
        orders.append({
            "id": row_dict.get('id'),
            "symbol": row_dict.get('symbol'),
            "side": row_dict.get('type'), 
            "price": row_dict.get('price'),
            "amount": row_dict.get('amount'),
            "filled": row_dict.get('amount'), 
            "status": row_dict.get('status', 'closed'),
            "timestamp": row_dict.get('timestamp')
        })
        
    return jsonify({"orders": orders})

@app.route('/api/bot/history', methods=['GET'])
def api_bot_history():
    username = request.args.get('username')
    limit = request.args.get('limit', 20)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if username:
        query = "SELECT * FROM bot_activity WHERE username=? ORDER BY timestamp DESC LIMIT ?"
        c.execute(query, (username, limit))
    else:
        query = "SELECT * FROM bot_activity ORDER BY timestamp DESC LIMIT ?"
        c.execute(query, (limit,))
        
    rows = c.fetchall()
    conn.close()
    
    return jsonify([dict(r) for r in rows])

@app.route('/api/health', methods=['GET'])
async def get_health():
    monitor = HealthMonitor()
    is_healthy = await monitor.run_health_check()
    return jsonify({
        "status": monitor.status,
        "details": {
            "db_connected": is_healthy, 
            "latencies": monitor.exchange_latencies
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
