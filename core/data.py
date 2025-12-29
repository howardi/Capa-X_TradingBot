
import ccxt
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional
from config.exchanges import EXCHANGES
from config.settings import HTTP_PROXY, HTTPS_PROXY
import numpy as np

class CustomExchange:
    """
    Fallback class for exchanges not supported by CCXT (e.g. Quidax, NairaEx, Busha).
    Provides a compatible interface to prevent bot crashes.
    """
    def __init__(self, exchange_id, config=None):
        self.id = exchange_id
        self.name = exchange_id.capitalize()
        self.apiKey = config.get('apiKey', '') if config else ''
        self.secret = config.get('secret', '') if config else ''
        self.has = {'fetchOHLCV': False, 'fetchTicker': False, 'createOrder': False}
        self.timeframes = {'1m': '1m', '5m': '5m', '1h': '1h', '1d': '1d'}
        self.markets = {}

    def check_required_credentials(self):
        if not self.apiKey or not self.secret:
            raise Exception("API Key and Secret required")
        return True

    def load_markets(self):
        return {}
    
    def fetch_ticker(self, symbol):
        # Return dummy ticker to allow UI to render
        return {'symbol': symbol, 'last': 0.0, 'bid': 0.0, 'ask': 0.0, 'percentage': 0.0}

    def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        # Return empty list or fallback to yfinance in DataManager
        return []

    def create_order(self, symbol, type, side, amount, price=None):
        raise NotImplementedError(f"Trading via API is not yet implemented for {self.name}. Use Manual Terminal.")

class DataManager:
    def __init__(self, exchange_id: str = 'binance'):
        self.exchange_id = exchange_id
        self.primary_exchange_id = exchange_id
        self.backup_exchanges = ['kraken', 'kucoin', 'bitstamp']
        self.current_exchange_index = -1
        
        self.exchange = self._initialize_exchange(exchange_id)
        self.markets_loaded = False
        self.connection_status = "Disconnected"
        self.connection_error = None
        self.offline_mode = False
        self.use_yfinance_fallback = True
        self.failover_active = False

    def _initialize_exchange(self, exchange_id: str, use_proxy: bool = True):
        config = EXCHANGES.get(exchange_id, {})
        
        # Add Proxy if configured and requested
        proxies = {}
        if use_proxy:
            if HTTP_PROXY: proxies['http'] = HTTP_PROXY
            if HTTPS_PROXY: proxies['https'] = HTTPS_PROXY
        
        if proxies:
            config['proxies'] = proxies
            
        try:
            # Check if exchange is supported by CCXT
            if exchange_id in ccxt.exchanges:
                exchange_class = getattr(ccxt, exchange_id)
                return exchange_class(config)
            else:
                print(f"⚠️ {exchange_id} not found in CCXT. Using CustomExchange adapter.")
                return CustomExchange(exchange_id, config)
        except Exception as e:
            print(f"❌ Error initializing {exchange_id}: {e}. Falling back to CustomExchange.")
            return CustomExchange(exchange_id, config)

    def set_proxy_mode(self, use_proxy: bool):
        """Re-initialize exchange with or without proxy"""
        print(f"🔄 Switching Proxy Mode: {'ON' if use_proxy else 'OFF'}")
        self.exchange = self._initialize_exchange(self.exchange_id, use_proxy)
        self.markets_loaded = False
        self.ensure_markets_loaded()

    def switch_exchange(self):
        """Failover to next available backup exchange"""
        if self.offline_mode:
            return False

        print(f"⚠️ Initiating Failover from {self.exchange_id}...")
        
        # Move to next backup
        self.current_exchange_index += 1
        
        if self.current_exchange_index < len(self.backup_exchanges):
            new_id = self.backup_exchanges[self.current_exchange_index]
            print(f"🔄 Switching to Backup Exchange: {new_id}")
            
            try:
                self.exchange = self._initialize_exchange(new_id)
                self.exchange_id = new_id
                self.failover_active = True
                
                # Attempt to connect immediately
                self.markets_loaded = False
                self.ensure_markets_loaded()
                
                if self.connection_status == "Connected":
                    print(f"✅ Successfully failed over to {new_id}")
                    return True
                else:
                    # Recursive call if this one fails too
                    print(f"⚠️ Connection to {new_id} failed. Trying next...")
                    self.offline_mode = False # Reset to allow next attempt
                    return self.switch_exchange()
            except Exception as e:
                print(f"❌ Failed to switch to {new_id}: {e}")
                self.offline_mode = False
                return self.switch_exchange()
        else:
            print("❌ All backup exchanges failed. Switching to Offline Mode.")
            self.failover_active = False
            self.offline_mode = True
            self.connection_status = "Offline"
            self.connection_error = "All exchanges unreachable."
            return False

    def update_credentials(self, api_key: str, api_secret: str):
        """Update exchange credentials dynamically"""
        if self.exchange:
            self.exchange.apiKey = api_key
            self.exchange.secret = api_secret
            self.exchange.check_required_credentials()
            
            # Reset connection state to force reconnection
            self.markets_loaded = False
            self.connection_status = "Disconnected"
            self.offline_mode = False
            self.ensure_markets_loaded()

    def ensure_markets_loaded(self):
        if not self.markets_loaded and not self.offline_mode:
            try:
                # Set timeout to avoid hanging
                self.exchange.timeout = 5000 # 5 seconds
                self.exchange.load_markets()
                self.markets_loaded = True
                self.connection_status = "Connected"
                self.connection_error = None
            except Exception as e:
                # Always switch to offline mode on error to prevent UI blocking
                self.offline_mode = True
                # Set status to Offline instead of Error to be less alarming
                self.connection_status = "Offline"
                self.connection_error = f"Connection failed ({str(e)}). Using Offline Mode."
                print(f"Error loading markets: {e}")

    def measure_latency(self) -> int:
        """Measure API latency in milliseconds"""
        if self.offline_mode:
            return 0
            
        try:
            start = pd.Timestamp.now()
            # Lightweight call to check responsiveness
            self.exchange.fetch_time() 
            end = pd.Timestamp.now()
            return int((end - start).total_seconds() * 1000)
        except:
            try:
                # Fallback if fetch_time not supported
                start = pd.Timestamp.now()
                self.exchange.fetch_ticker('BTC/USDT')
                end = pd.Timestamp.now()
                return int((end - start).total_seconds() * 1000)
            except:
                return -1 # Timeout/Error

    def check_connection_health(self):
        """Diagnose connection quality"""
        if self.offline_mode:
            return {"status": "Offline", "latency": 0, "quality": "N/A"}
            
        latency = self.measure_latency()
        
        if latency == -1:
             self.connection_status = "Unstable"
             
             # Trigger Failover if unstable
             # Only trigger if not already in a hopeless state to avoid infinite loops
             # We use a simple counter or just try once per check call? 
             # Better: If unstable, try to switch.
             if not self.failover_active: # If we haven't failed over yet, try it.
                 print("Connection Unstable. Attempting Failover...")
                 if self.switch_exchange():
                     return self.check_connection_health()
             
             return {"status": "Unstable", "latency": 9999, "quality": "Critical"}
             
        quality = "Excellent"
        if latency > 500: quality = "Good"
        if latency > 1000: quality = "Fair"
        if latency > 2000: quality = "Poor"
        
        return {"status": "Connected", "latency": latency, "quality": quality}

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data and return as DataFrame"""
        if self.offline_mode:
            if self.use_yfinance_fallback:
                return self._fetch_yfinance_data(symbol, timeframe, limit)
            return self._generate_mock_data(limit)
            
        try:
            self.ensure_markets_loaded()
            if self.offline_mode: 
                if self.use_yfinance_fallback:
                    return self._fetch_yfinance_data(symbol, timeframe, limit)
                return self._generate_mock_data(limit)
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            if self.use_yfinance_fallback:
                return self._fetch_yfinance_data(symbol, timeframe, limit)
            return pd.DataFrame()

    def _fetch_yfinance_data(self, symbol, timeframe, limit):
        """Fetch real data from Yahoo Finance as fallback"""
        try:
            # Map CCXT symbol to YF symbol
            # BTC/USDT -> BTC-USD
            yf_symbol = symbol.replace('/', '-')
            if 'USDT' in yf_symbol:
                yf_symbol = yf_symbol.replace('USDT', 'USD')
            
            # Map timeframe
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '4h': '1h', # YF 4h is tricky, use 1h and resample if needed, or just 1h
                '1d': '1d', '1w': '1wk'
            }
            interval = interval_map.get(timeframe, '1h')
            
            # YF period calculation
            period = '1mo'
            if timeframe == '1m': period = '1d'
            elif timeframe == '5m': period = '5d'
            elif timeframe == '15m': period = '5d'
            
            df = yf.download(tickers=yf_symbol, interval=interval, period=period, progress=False)
            
            if df.empty:
                print(f"YFinance returned empty for {yf_symbol}")
                return self._generate_mock_data(limit)

            # Reset index to make Date a column
            df = df.reset_index()

            # Handle MultiIndex columns (YF 0.2.x+)
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten columns: Use the first level (Price Type)
                # Example: ('Close', 'BTC-USD') -> 'Close'
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            
            # Convert to strings and lowercase
            df.columns = [str(c).lower() for c in df.columns]

            # Rename Date/Datetime to timestamp
            rename_map = {'date': 'timestamp', 'datetime': 'timestamp'}
            df = df.rename(columns=rename_map)
            
            # Remove Duplicate Columns (Crucial fix for ValueError)
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Ensure required columns exist
            required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
            # Check if we have all required columns
            missing = [col for col in required if col not in df.columns]
            if missing:
                print(f"YFinance missing columns: {missing}")
                return self._generate_mock_data(limit)

            # Filter to limit
            df = df.tail(limit)
            
            # Ensure numeric
            cols = ['open', 'high', 'low', 'close', 'volume']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            
            return df[required]
        except Exception as e:
            print(f"YFinance Fallback Failed: {e}")
            return self._generate_mock_data(limit)

    def _generate_mock_data(self, limit):
        """Generate realistic mock data for offline mode"""
        dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq='h')
        base_price = 50000
        volatility = 0.02
        
        prices = [base_price]
        for _ in range(limit-1):
            change = np.random.normal(0, base_price * volatility)
            prices.append(prices[-1] + change)
            
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'volume': np.random.randint(1000, 5000, limit)
        })
        return df

    def fetch_ticker(self, symbol: str) -> dict:
        if self.offline_mode and self.use_yfinance_fallback:
             # Try to get real price from YF
             try:
                 yf_symbol = symbol.replace('/', '-')
                 if 'USDT' in yf_symbol: yf_symbol = yf_symbol.replace('USDT', 'USD')
                 ticker = yf.Ticker(yf_symbol)
                 # Fast fetch info
                 info = ticker.fast_info
                 price = info.last_price
                 if price:
                     return {'last': price, 'ask': price, 'bid': price, 'high': price, 'low': price, 'volume': 0}
             except:
                 pass # Fallback to empty if YF fails
                 
        try:
            self.ensure_markets_loaded()
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            print(f"Error fetching ticker for {symbol}: {e}")
            if self.use_yfinance_fallback:
                # Same fallback logic
                try:
                     yf_symbol = symbol.replace('/', '-')
                     if 'USDT' in yf_symbol: yf_symbol = yf_symbol.replace('USDT', 'USD')
                     ticker = yf.Ticker(yf_symbol)
                     info = ticker.fast_info
                     price = info.last_price
                     if price:
                         return {'last': price, 'ask': price, 'bid': price, 'high': price, 'low': price, 'volume': 0}
                except:
                    pass
            return {}
            
    def get_current_price(self, symbol: str) -> float:
        """Get the latest price for a symbol"""
        ticker = self.fetch_ticker(symbol)
        if ticker and 'last' in ticker:
            return float(ticker['last'])
        return 0.0

    def get_balance(self):
        if self.offline_mode:
            return {'USDT': {'free': 10000.0, 'used': 0.0, 'total': 10000.0}}
            
        try:
            return self.exchange.fetch_balance()
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return {}

    def fetch_positions(self, symbol: str = None):
        if self.offline_mode:
            return []
            
        try:
            self.ensure_markets_loaded()
            # Some exchanges use different methods for positions
            if hasattr(self.exchange, 'fetch_positions'):
                return self.exchange.fetch_positions(symbol) if symbol else self.exchange.fetch_positions()
            else:
                return []
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    def fetch_orders(self, symbol: str = None, limit: int = 10):
        try:
            self.ensure_markets_loaded()
            if symbol:
                return self.exchange.fetch_orders(symbol, limit=limit)
            else:
                return self.exchange.fetch_orders(limit=limit)
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []

    def create_order(self, symbol, type, side, amount, price=None):
        try:
            self.ensure_markets_loaded()
            return self.exchange.create_order(symbol, type, side, amount, price)
        except Exception as e:
            print(f"Error creating order: {e}")
            raise e

    def fetch_order_book(self, symbol: str, limit: int = 20) -> dict:
        """Fetch current order book (depth)"""
        if self.offline_mode:
            # Generate mock high-liquidity order book
            price = 50000.0
            bids = [[price * (1 - i*0.0001), 1.0] for i in range(limit)]
            asks = [[price * (1 + i*0.0001), 1.0] for i in range(limit)]
            return {'bids': bids, 'asks': asks, 'timestamp': 0, 'datetime': ''}
            
        try:
            self.ensure_markets_loaded()
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {e}")
            return {}

    def fetch_funding_rate(self, symbol: str) -> float:
        """Fetch current funding rate"""
        if self.offline_mode:
            return 0.0001 # Positive funding
            
        try:
            self.ensure_markets_loaded()
            # Try specific method first, then ticker fallback
            if hasattr(self.exchange, 'fetch_funding_rate'):
                data = self.exchange.fetch_funding_rate(symbol)
                return data.get('fundingRate', 0.0)
            return 0.0
        except Exception as e:
            # print(f"Funding rate not available: {e}")
            return 0.0

