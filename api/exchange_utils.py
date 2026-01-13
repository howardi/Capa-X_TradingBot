import ccxt
import os
import time
from dotenv import load_dotenv
from api.db import get_db_connection

load_dotenv()

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

# Default Public Exchange
default_exchange = None
for exchange_id in ['binance', 'kucoin', 'kraken', 'bitstamp']:
    try:
        exchange_class = getattr(ccxt, exchange_id)
        default_exchange = exchange_class({'enableRateLimit': True, 'timeout': 3000}) # 3s timeout
        # Force a connectivity check - Skipped to speed up startup
        # default_exchange.load_markets() 
        print(f"✅ Default Exchange Initialized: {exchange_id}")
        break
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize {exchange_id}: {e}")
        default_exchange = None

if not default_exchange:
    print("❌ Critical: No default exchange available for market data.")

class VirtualExchange:
    """Mimics CCXT Exchange for Internal Ledger Trading."""
    def __init__(self, username):
        self.username = username
        self.id = 'virtual'
        self.has = {'fetchBalance': True, 'createOrder': True, 'fetchTicker': True, 'fetchOHLCV': True}

    def checkRequiredCredentials(self):
        return True

    def fetch_balance(self):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT currency, balance FROM live_balances WHERE username=?", (self.username,))
        rows = c.fetchall()
        conn.close()
        
        balance = {'free': {}, 'total': {}}
        for row in rows:
            curr = row['currency']
            bal = row['balance']
            balance[curr] = {'free': bal, 'total': bal}
            balance['free'][curr] = bal
            balance['total'][curr] = bal
        return balance

    def fetch_ticker(self, symbol):
        return default_exchange.fetch_ticker(symbol)

    def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        return default_exchange.fetch_ohlcv(symbol, timeframe, limit)

    def create_order(self, symbol, type, side, amount, price=None):
        # 1. Get Current Price if Market Order
        if not price:
            ticker = self.fetch_ticker(symbol)
            price = ticker['last']
            
        base, quote = symbol.split('/') # e.g. BTC/USDT -> BTC, USDT
        cost = amount * price
        
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            # Check Balance
            c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", 
                      (self.username, quote if side == 'buy' else base))
            row = c.fetchone()
            available = row['balance'] if row else 0.0
            
            if side == 'buy':
                if available < cost:
                    raise Exception(f"Insufficient {quote} balance")
                # Debit Quote, Credit Base
                c.execute("UPDATE live_balances SET balance = balance - ? WHERE username=? AND currency=?", (cost, self.username, quote))
                
                # Credit Base (Insert if not exists)
                c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (self.username, base))
                if c.fetchone():
                    c.execute("UPDATE live_balances SET balance = balance + ? WHERE username=? AND currency=?", (amount, self.username, base))
                else:
                    c.execute("INSERT INTO live_balances (username, currency, balance) VALUES (?, ?, ?)", (self.username, base, amount))
                    
            elif side == 'sell':
                if available < amount:
                    raise Exception(f"Insufficient {base} balance")
                # Debit Base, Credit Quote
                c.execute("UPDATE live_balances SET balance = balance - ? WHERE username=? AND currency=?", (amount, self.username, base))
                
                # Credit Quote
                c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (self.username, quote))
                if c.fetchone():
                    c.execute("UPDATE live_balances SET balance = balance + ? WHERE username=? AND currency=?", (cost, self.username, quote))
                else:
                    c.execute("INSERT INTO live_balances (username, currency, balance) VALUES (?, ?, ?)", (self.username, quote, cost))
            
            # Log Transaction
            c.execute("INSERT INTO transactions (username, type, currency, amount, status, tx_ref) VALUES (?, ?, ?, ?, ?, ?)",
                      (self.username, f"trade_{side}", symbol, amount, 'completed', f"tx_{int(time.time())}"))
            
            conn.commit()
            return {
                'id': f"vt_{int(time.time())}",
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price,
                'status': 'closed',
                'filled': amount
            }
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

def get_exchange(username=None, mode='live'):
    """Get exchange instance for a user."""
    # 1. If Internal/Virtual Mode is preferred (or force checked first for Live Internal Trading)
    # We check if the user has keys. If NOT, we default to VirtualExchange for 'Live' using Internal Funds.
    
    # Check for External Keys first
    external_exchange = None
    if username:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT exchange_id, api_key, secret FROM exchanges WHERE username=?", (username,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                exchange_id = row['exchange_id']
                api_key = row['api_key']
                secret = row['secret']
                
                if hasattr(ccxt, exchange_id):
                    exchange_class = getattr(ccxt, exchange_id)
                    try:
                        external_exchange = exchange_class({
                            'apiKey': api_key,
                            'secret': secret,
                            'enableRateLimit': True,
                            'options': {'defaultType': 'spot'}
                        })
                    except: pass
        except: pass

    if external_exchange:
        return external_exchange

    # 2. If no external keys, return VirtualExchange (for Internal Ledger Trading)
    if username and username != 'admin':
        return VirtualExchange(username)

    # 3. Fallback to Env Vars (Admin)
    if (not username or username == 'admin') and BINANCE_API_KEY and BINANCE_SECRET:
         try:
            return ccxt.binance({
                'apiKey': BINANCE_API_KEY,
                'secret': BINANCE_SECRET,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'} 
            })
         except: pass

    # 4. Fallback to Public
    return default_exchange
