import asyncio
import ccxt.async_support as ccxt
import time
from api.db import get_db_connection
from api.core.logger import logger
from api.services.rate_limiter import rate_limit_manager

class RateLimitedExchange:
    """
    Wrapper for CCXT Exchange to enforce centralized rate limits.
    """
    def __init__(self, exchange, exchange_id):
        self.exchange = exchange
        self.exchange_id = exchange_id
        # Forward common attributes
        self.id = exchange.id
        self.urls = getattr(exchange, 'urls', {})
        self.api = getattr(exchange, 'api', {})
        self.timeframes = getattr(exchange, 'timeframes', {})

    def __getattr__(self, name):
        return getattr(self.exchange, name)

    async def fetch_ticker(self, *args, **kwargs):
        await rate_limit_manager.acquire(self.exchange_id)
        try:
            return await self.exchange.fetch_ticker(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                 await rate_limit_manager.handle_429(self.exchange_id)
            raise e

    async def fetch_ohlcv(self, *args, **kwargs):
        await rate_limit_manager.acquire(self.exchange_id)
        try:
            return await self.exchange.fetch_ohlcv(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                 await rate_limit_manager.handle_429(self.exchange_id)
            raise e

    async def create_order(self, *args, **kwargs):
        await rate_limit_manager.acquire(self.exchange_id, cost=2)
        try:
            return await self.exchange.create_order(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                 await rate_limit_manager.handle_429(self.exchange_id)
            raise e

    async def fetch_balance(self, *args, **kwargs):
        await rate_limit_manager.acquire(self.exchange_id)
        try:
            return await self.exchange.fetch_balance(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                 await rate_limit_manager.handle_429(self.exchange_id)
            raise e
            
    async def fetch_open_orders(self, *args, **kwargs):
        await rate_limit_manager.acquire(self.exchange_id)
        try:
            return await self.exchange.fetch_open_orders(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                 await rate_limit_manager.handle_429(self.exchange_id)
            raise e
            
    async def fetch_order(self, *args, **kwargs):
        await rate_limit_manager.acquire(self.exchange_id)
        try:
            return await self.exchange.fetch_order(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                 await rate_limit_manager.handle_429(self.exchange_id)
            raise e

    async def close(self):
        await self.exchange.close()

class VirtualExchange:
    """Mimics CCXT Exchange for Internal Ledger Trading."""
    def __init__(self, username, price_source_exchange=None, mode='demo'):
        self.username = username
        self.id = 'virtual'
        self.has = {'fetchBalance': True, 'createOrder': True, 'fetchTicker': True, 'fetchOHLCV': True}
        self.price_source = price_source_exchange # This should be an async exchange instance or None
        self.mode = mode
        self.table_name = 'live_balances' if mode == 'live' else 'demo_balances'

    def checkRequiredCredentials(self):
        return True
        
    async def close(self):
        """Cleanup resources."""
        if self.price_source:
            # We don't close price_source here because it might be shared.
            # But if it's unique, we should. 
            # For now, let the creator manage price_source lifecycle.
            pass
        return True

    async def fetch_balance(self):
        def _db_fetch():
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(f"SELECT currency, balance FROM {self.table_name} WHERE username=?", (self.username,))
            rows = c.fetchall()
            conn.close()
            return rows

        rows = await asyncio.to_thread(_db_fetch)
        
        balance = {'free': {}, 'total': {}}
        for row in rows:
            curr = row['currency']
            bal = row['balance']
            balance[curr] = {'free': bal, 'total': bal}
            balance['free'][curr] = bal
            balance['total'][curr] = bal
        return balance

    async def fetch_ticker(self, symbol):
        # Handle NGN Pairs Custom Logic
        if 'NGN' in symbol:
            # Approximate Rates
            usdt_ngn = 1650.0 
            
            if symbol == 'USDT/NGN':
                return {'last': usdt_ngn, 'bid': usdt_ngn, 'ask': usdt_ngn}
            elif symbol == 'NGN/USDT':
                return {'last': 1/usdt_ngn, 'bid': 1/usdt_ngn, 'ask': 1/usdt_ngn}
            
            # Cross rates
            base, quote = symbol.split('/')
            if quote == 'NGN':
                try:
                    # Recursively fetch base/USDT
                    base_usdt_ticker = await self.fetch_ticker(f"{base}/USDT")
                    base_usdt = base_usdt_ticker['last']
                    price = base_usdt * usdt_ngn
                    return {'last': price}
                except Exception as e:
                    logger.error(f"Error fetching cross rate for {symbol}: {e}")
                    return {'last': 0.0}
        
        if self.price_source:
            try:
                return await self.price_source.fetch_ticker(symbol)
            except Exception as e:
                logger.warning(f"Price source failed for {symbol}: {e}")
                
        # Fallback Mock
        base_prices = {'BTC': 95000, 'ETH': 2800, 'SOL': 140, 'BNB': 600, 'USDT': 1.0}
        base, quote = symbol.split('/')
        price = base_prices.get(base, 100) / base_prices.get(quote, 1)
        return {'last': price}

    async def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        if self.price_source:
            try:
                return await self.price_source.fetch_ohlcv(symbol, timeframe, limit)
            except Exception as e:
                logger.warning(f"Price source fetch_ohlcv failed: {e}")
        return []

    async def fetch_open_orders(self, symbol=None, since=None, limit=None, params={}):
        return []

    async def fetch_closed_orders(self, symbol=None, since=None, limit=None, params={}):
        return []

    async def create_order(self, symbol, type, side, amount, price=None, params={}):
        if not price:
            ticker = await self.fetch_ticker(symbol)
            price = ticker['last']
            
        base, quote = symbol.split('/') 
        cost = amount * price
        
        def _db_execute():
            conn = get_db_connection()
            c = conn.cursor()
            
            try:
                # Check Balance
                c.execute(f"SELECT balance FROM {self.table_name} WHERE username=? AND currency=?", 
                          (self.username, quote if side == 'buy' else base))
                row = c.fetchone()
                available = row['balance'] if row else 0.0
                
                if side == 'buy':
                    if available < cost:
                        raise Exception(f"Insufficient {quote} balance: {available} < {cost}")
                    # Debit Quote
                    c.execute(f"UPDATE {self.table_name} SET balance = balance - ? WHERE username=? AND currency=?", (cost, self.username, quote))
                    
                    # Credit Base
                    c.execute(f"SELECT balance FROM {self.table_name} WHERE username=? AND currency=?", (self.username, base))
                    if c.fetchone():
                        c.execute(f"UPDATE {self.table_name} SET balance = balance + ? WHERE username=? AND currency=?", (amount, self.username, base))
                    else:
                        c.execute(f"INSERT INTO {self.table_name} (username, currency, balance) VALUES (?, ?, ?)", (self.username, base, amount))
                        
                elif side == 'sell':
                    if available < amount:
                        raise Exception(f"Insufficient {base} balance: {available} < {amount}")
                    # Debit Base
                    c.execute(f"UPDATE {self.table_name} SET balance = balance - ? WHERE username=? AND currency=?", (amount, self.username, base))
                    
                    # Credit Quote
                    c.execute(f"SELECT balance FROM {self.table_name} WHERE username=? AND currency=?", (self.username, quote))
                    if c.fetchone():
                        c.execute(f"UPDATE {self.table_name} SET balance = balance + ? WHERE username=? AND currency=?", (cost, self.username, quote))
                    else:
                        c.execute(f"INSERT INTO {self.table_name} (username, currency, balance) VALUES (?, ?, ?)", (self.username, quote, cost))
                
                # Log Transaction (Only for Live)
                if self.mode == 'live':
                    c.execute("INSERT INTO transactions (username, type, currency, amount, status, tx_ref) VALUES (?, ?, ?, ?, ?, ?)",
                              (self.username, f"trade_{side}", symbol, amount, 'completed', f"tx_{int(time.time())}"))
                
                conn.commit()
                return {'id': f"virtual_{int(time.time())}", 'status': 'closed', 'filled': amount, 'remaining': 0}
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

        return await asyncio.to_thread(_db_execute)

class ExchangeService:
    """
    Main Service for managing Exchange connections.
    Supports creating async exchange instances for price data.
    """
    def __init__(self):
        self._exchange = None

    async def get_shared_price_source(self):
        """
        Returns an async exchange instance for market data.
        Initializes a dedicated async CCXT instance if needed.
        """
        if self._exchange is None:
            # We create a new async instance because we need async support
            # Hardcode to Binance for price source for now.
            try:
                # Use Binance for reliable public data
                self._exchange = ccxt.binance({
                    'enableRateLimit': True, 
                    'timeout': 5000
                })
                # Check connectivity? No, lazy load.
            except Exception as e:
                logger.error(f"Failed to create async exchange source: {e}")
                return None
                
        return self._exchange

    async def close_shared_resources(self):
        if self._exchange:
            try:
                await self._exchange.close()
            except:
                pass
            self._exchange = None
