
import hashlib
import json
import os
import secrets
import hmac
import time
import struct
import base64
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, data_dir="data/users"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        self.sessions_file = os.path.join(self.data_dir, "sessions.json")
        self.sessions = {}
        self._load_sessions()

    def _load_sessions(self):
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r') as f:
                    self.sessions = json.load(f)
            else:
                self.sessions = {}
        except:
            self.sessions = {}

    def _save_sessions(self):
        with open(self.sessions_file, 'w') as f:
            json.dump(self.sessions, f, indent=4)

    def create_session(self, username, remember_me=False):
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expiry_hours = 24 * 30 if remember_me else 24
        expiry = datetime.now() + timedelta(hours=expiry_hours)
        
        # Store hash of the token for security
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        self.sessions[token_hash] = {
            "username": username,
            "expiry": str(expiry),
            "created_at": str(datetime.now()),
            "remember_me": remember_me
        }
        self._save_sessions()
        return token

    def validate_session(self, token):
        if not token:
            return None
            
        # Hash token to lookup session
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if token_hash not in self.sessions:
            return None
        
        session = self.sessions[token_hash]
        expiry = datetime.fromisoformat(session['expiry'])
        
        if datetime.now() > expiry:
            self.revoke_session(token)
            return None
            
        # Auto-renew if close to expiry (e.g., within 2 hours of expiry)
        # Only renew if it's NOT a remember_me session (which is already long)
        # Or just renew anyway to keep active users logged in indefinitely
        if (expiry - datetime.now()) < timedelta(hours=2):
            self.extend_session(token)
            
        return session['username']

    def extend_session(self, token, hours=24):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in self.sessions:
            new_expiry = datetime.now() + timedelta(hours=hours)
            self.sessions[token_hash]['expiry'] = str(new_expiry)
            self._save_sessions()

    def revoke_session(self, token):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in self.sessions:
            del self.sessions[token_hash]
            self._save_sessions()
    
    def cleanup_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired_tokens = []
        for token, data in self.sessions.items():
            if now > datetime.fromisoformat(data['expiry']):
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.sessions[token]
            
        if expired_tokens:
            self._save_sessions()

class TOTP:
    @staticmethod
    def generate_secret():
        # Generate a random 16-byte secret and base32 encode it
        # Standard TOTP uses Base32
        random_bytes = secrets.token_bytes(20)
        return base64.b32encode(random_bytes).decode('utf-8')

    @staticmethod
    def get_totp_token(secret):
        # Decode base32 secret
        try:
            key = base64.b32decode(secret, casefold=True)
        except:
            return None
            
        # Time interval (30s)
        interval = 30
        timestamp = int(time.time())
        counter = int(timestamp / interval)
        
        # Pack counter as big-endian 8-byte string
        msg = struct.pack(">Q", counter)
        
        # HMAC-SHA1
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        
        # Dynamic Truncation
        offset = digest[19] & 0xf
        code = (struct.unpack(">I", digest[offset:offset+4])[0] & 0x7fffffff) % 1000000
        
        return "{:06d}".format(code)

    @staticmethod
    def verify_totp(secret, token, window=1):
        if not secret or not token:
            return False
            
        # Check current, prev, and next intervals for drift
        try:
            key = base64.b32decode(secret, casefold=True)
        except:
            return False
            
        interval = 30
        timestamp = int(time.time())
        current_counter = int(timestamp / interval)
        
        for i in range(-window, window + 1):
            counter = current_counter + i
            msg = struct.pack(">Q", counter)
            digest = hmac.new(key, msg, hashlib.sha1).digest()
            offset = digest[19] & 0xf
            code = (struct.unpack(">I", digest[offset:offset+4])[0] & 0x7fffffff) % 1000000
            if "{:06d}".format(code) == str(token):
                return True
        return False

class AuthManager:
    def __init__(self, data_dir="data/users"):
        self.data_dir = data_dir
        self.users_file = os.path.join(self.data_dir, "users_db.json")
        self._ensure_dir()
        self._load_users()

    def _ensure_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)

    def _load_users(self):
        try:
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except:
            self.users = {}

    def _save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=4)

    def _hash_password(self, password, salt=None):
        if not salt:
            salt = secrets.token_hex(16)
        # Simple hashing for demo (PBKDF2 is better for prod)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return salt, key.hex()

    def register_user(self, username, password, email, role="demo"):
        if username in self.users:
            return False, "Username already exists"
        
        salt, hashed_pw = self._hash_password(password)
        
        self.users[username] = {
            "email": email,
            "salt": salt,
            "password_hash": hashed_pw,
            "role": role,
            "2fa_enabled": False,
            "2fa_secret": None,
            "created_at": str(datetime.now()),
            "last_login": None,
            "settings": {
                "theme": "dark",
                "notifications_enabled": True
            }
        }
        self._save_users()
        
        # Create user specific data directory
        user_path = os.path.join(self.data_dir, username)
        if not os.path.exists(user_path):
            os.makedirs(user_path)
            # Initialize paper wallet
            with open(os.path.join(user_path, "paper_wallet.json"), 'w') as f:
                json.dump({"USDT": 10000.0, "BTC": 0.0, "ETH": 0.0}, f)
            # Initialize trade log
            with open(os.path.join(user_path, "trade_history.json"), 'w') as f:
                json.dump([], f)
                
        return True, "User registered successfully"

    def login_user(self, username, password):
        if username not in self.users:
            return False, "User not found"
        
        user_data = self.users[username]
        salt = user_data["salt"]
        stored_hash = user_data["password_hash"]
        
        _, new_hash = self._hash_password(password, salt)
        
        if new_hash == stored_hash:
            # Update last_login if 2FA is NOT enabled (otherwise verify_2fa_login does it)
            if not user_data.get('2fa_enabled', False):
                self.users[username]["last_login"] = str(datetime.now())
                self._save_users()
                
            return True, user_data
        else:
            return False, "Invalid password"

    def enable_2fa(self, username, secret, code):
        if username not in self.users:
            return False, "User not found"
        
        if TOTP.verify_totp(secret, code):
            self.users[username]['2fa_enabled'] = True
            self.users[username]['2fa_secret'] = secret
            self._save_users()
            return True, "2FA Enabled Successfully"
        else:
            return False, "Invalid 2FA Code"

    def disable_2fa(self, username, password):
        # Re-verify password to disable
        success, _ = self.login_user(username, password)
        if success:
            self.users[username]['2fa_enabled'] = False
            self.users[username]['2fa_secret'] = None
            self._save_users()
            return True, "2FA Disabled"
        return False, "Invalid Password"

    def verify_2fa_login(self, username, code):
        if username not in self.users:
            return False
        
        secret = self.users[username].get('2fa_secret')
        if not secret:
            return True # If 2FA not set, pass (should be handled by logic)
            
        if TOTP.verify_totp(secret, code):
            self.users[username]["last_login"] = str(datetime.now())
            self._save_users()
            return True
        return False

    def update_password(self, username, old_pw, new_pw):
        success, _ = self.login_user(username, old_pw)
        if not success:
            return False, "Invalid current password"
            
        salt, hashed_pw = self._hash_password(new_pw)
        self.users[username]['salt'] = salt
        self.users[username]['password_hash'] = hashed_pw
        self._save_users()
        return True, "Password updated successfully"

    def save_api_keys(self, username, exchange, api_key, api_secret):
        """
        Save API keys for a user. 
        WARNING: Stored in plain text in local JSON. Use with caution.
        """
        if username in self.users:
            if 'api_keys' not in self.users[username]:
                self.users[username]['api_keys'] = {}
            
            self.users[username]['api_keys'][exchange] = {
                'api_key': api_key,
                'api_secret': api_secret
            }
            self._save_users()
            return True
        return False

    def get_api_keys(self, username, exchange):
        """Retrieve API keys for a user and exchange"""
        if username in self.users:
            keys = self.users[username].get('api_keys', {}).get(exchange)
            if keys:
                return keys['api_key'], keys['api_secret']
        return None, None

    def delete_api_keys(self, username, exchange):
        """Remove API keys for a user and exchange"""
        if username in self.users and 'api_keys' in self.users[username]:
            if exchange in self.users[username]['api_keys']:
                del self.users[username]['api_keys'][exchange]
                self._save_users()
                return True
        return False

    def update_email(self, username, password, new_email):
        success, _ = self.login_user(username, password)
        if not success:
            return False, "Invalid password"
        
        self.users[username]['email'] = new_email
        self._save_users()
        return True, "Email updated successfully"

class UserManager:
    """
    Manages user-specific data (Paper Wallet, Trade History, Settings)
    """
    def __init__(self, username, data_dir="data/users"):
        self.username = username
        self.user_dir = os.path.join(data_dir, username)
        self.wallet_file = os.path.join(self.user_dir, "paper_wallet.json")
        self.history_file = os.path.join(self.user_dir, "trade_history.json")
        self.positions_file = os.path.join(self.user_dir, "positions.json")
        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(self.positions_file):
            with open(self.positions_file, 'w') as f:
                json.dump({}, f)

    def get_paper_balance(self):
        try:
            with open(self.wallet_file, 'r') as f:
                return json.load(f)
        except:
            return {"USDT": 10000.0}

    def update_paper_balance(self, asset, amount, operation="add"):
        balances = self.get_paper_balance()
        current = balances.get(asset, 0.0)
        
        if operation == "add":
            balances[asset] = current + amount
        elif operation == "subtract":
            balances[asset] = max(0.0, current - amount)
        elif operation == "set":
            balances[asset] = amount
            
        with open(self.wallet_file, 'w') as f:
            json.dump(balances, f, indent=4)
        return balances

    def get_positions(self):
        try:
            with open(self.positions_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_positions(self, positions):
        with open(self.positions_file, 'w') as f:
            json.dump(positions, f, indent=4)

    def log_trade(self, trade_data):
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
            
        history.append(trade_data)
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=4)

    def execute_trade(self, symbol, side, amount, price, fee=0.0):
        """
        Executes a simulated trade:
        1. Updates Wallet Balances
        2. Updates Positions (Avg Entry Price)
        3. Calculates PnL (for Sells)
        4. Logs Trade
        """
        base_asset = symbol.split('/')[0]
        quote_asset = symbol.split('/')[1]
        cost = amount * price
        
        # 1. Update Balances
        if side.lower() == 'buy':
            self.update_paper_balance(quote_asset, cost + fee, "subtract")
            self.update_paper_balance(base_asset, amount, "add")
        else: # Sell
            self.update_paper_balance(base_asset, amount, "subtract")
            self.update_paper_balance(quote_asset, cost - fee, "add")

        # 2. Update Positions & Calculate PnL
        positions = self.get_positions()
        position = positions.get(symbol, {'amount': 0.0, 'entry_price': 0.0, 'realized_pnl': 0.0})
        
        realized_pnl = 0.0
        
        if side.lower() == 'buy':
            # Weighted Average Entry Price
            current_amt = position['amount']
            current_entry = position['entry_price']
            
            if current_amt + amount > 0:
                new_entry = ((current_amt * current_entry) + (amount * price)) / (current_amt + amount)
                position['entry_price'] = new_entry
                position['amount'] += amount
            else:
                # Should not happen ideally
                position['entry_price'] = price
                position['amount'] = amount
                
        elif side.lower() == 'sell':
            # Calculate PnL based on difference between Exit Price and Avg Entry Price
            avg_entry = position['entry_price']
            # PnL = (Exit - Entry) * Amount
            trade_pnl = (price - avg_entry) * amount
            realized_pnl = trade_pnl - fee
            
            position['amount'] = max(0.0, position['amount'] - amount)
            position['realized_pnl'] += realized_pnl
            
            # If position closed, reset entry price (optional, or keep 0)
            if position['amount'] <= 0.000001:
                position['amount'] = 0.0
                position['entry_price'] = 0.0

        positions[symbol] = position
        self._save_positions(positions)

        # 3. Log Trade
        trade_record = {
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'cost': cost,
            'fee': fee,
            'pnl': realized_pnl if side.lower() == 'sell' else 0.0,
            'timestamp': str(datetime.now()),
            'avg_entry_price': position['entry_price'] if side.lower() == 'buy' else 0.0 # Snapshot
        }
        self.log_trade(trade_record)
        
        return trade_record

    def get_trade_history(self):
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def get_performance_metrics(self):
        history = self.get_trade_history()
        if not history:
            return {
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }
            
        closed_trades = [t for t in history if t['side'].lower() == 'sell']
        if not closed_trades:
             return {
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }
            
        total_pnl = sum(t['pnl'] for t in closed_trades)
        wins = [t for t in closed_trades if t['pnl'] > 0]
        losses = [t for t in closed_trades if t['pnl'] <= 0]
        
        win_rate = (len(wins) / len(closed_trades)) * 100 if closed_trades else 0.0
        
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0

        # Advanced Metrics
        pnl_series = [t['pnl'] for t in closed_trades]
        
        # Sharpe Ratio (Simplified assuming risk-free rate = 0)
        import numpy as np
        if len(pnl_series) > 1:
            mean_pnl = np.mean(pnl_series)
            std_pnl = np.std(pnl_series)
            sharpe = mean_pnl / std_pnl if std_pnl > 0 else 0.0
        else:
            sharpe = 0.0

        # Max Drawdown
        cumulative = np.cumsum(pnl_series)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0.0
        
        return {
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "total_trades": len(closed_trades),
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd
        }

    def get_equity_curve(self):
        """Reconstruct equity curve from trade history"""
        history = self.get_trade_history()
        # Assume starting equity is static or we just track cumulative PnL
        # Better: Track Cumulative PnL over time
        
        curve = [{'timestamp': 'Start', 'pnl': 0.0, 'cumulative_pnl': 0.0}]
        cumulative = 0.0
        
        for trade in history:
            if trade['side'].lower() == 'sell':
                cumulative += trade['pnl']
                curve.append({
                    'timestamp': trade['timestamp'],
                    'pnl': trade['pnl'],
                    'cumulative_pnl': cumulative
                })
        return curve

    def get_periodic_breakdown(self):
        """Aggregate PnL by Day/Week/Month"""
        import pandas as pd
        history = self.get_trade_history()
        df = pd.DataFrame(history)
        if df.empty:
            return {}
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['side'] == 'sell'] # Only closed trades
        
        if df.empty:
            return {}

        daily = df.resample('D', on='timestamp')['pnl'].sum().to_dict()
        weekly = df.resample('W', on='timestamp')['pnl'].sum().to_dict()
        monthly = df.resample('M', on='timestamp')['pnl'].sum().to_dict()
        
        return {'daily': daily, 'weekly': weekly, 'monthly': monthly}

    def check_achievements(self):
        """
        Gamification: Unlock badges based on performance metrics.
        """
        metrics = self.get_performance_metrics()
        badges = []
        
        # 1. First Blood (First Trade)
        if metrics['total_trades'] >= 1:
            badges.append({
                "id": "first_blood",
                "name": "First Blood",
                "desc": "Completed your first trade.",
                "icon": "🩸"
            })
            
        # 2. Sniper (High Win Rate)
        if metrics['total_trades'] >= 5 and metrics['win_rate'] >= 80.0:
            badges.append({
                "id": "sniper",
                "name": "Market Sniper",
                "desc": "Maintained >80% Win Rate over 5+ trades.",
                "icon": "🎯"
            })
            
        # 3. Diamond Hands (High PnL)
        if metrics['total_pnl'] >= 1000.0:
            badges.append({
                "id": "diamond_hands",
                "name": "Diamond Hands",
                "desc": "Accumulated over $1,000 in profits.",
                "icon": "💎"
            })
            
        # 4. Veteran (Volume)
        if metrics['total_trades'] >= 50:
            badges.append({
                "id": "veteran",
                "name": "Veteran Trader",
                "desc": "Executed over 50 trades.",
                "icon": "🎖️"
            })

        return badges

