
import ccxt
import pandas as pd
import logging
import time

try:
    import yfinance as yf
except (ImportError, Exception):
    logging.warning("yfinance not found or failed to load. Stock data fetching will be disabled.")
    yf = None

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

    def fetch_order_book(self, symbol, limit=10):
        # Dummy order book
        return {'bids': [], 'asks': []}

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
        # Use copy to avoid modifying global configuration state
        config = EXCHANGES.get(exchange_id, {}).copy()
        
        # Sanitize credentials to prevent -2008 errors (Invalid Api-Key ID)
        # CCXT throws error if apiKey is empty string "", but works if it is None (public mode)
        if 'apiKey' in config:
            if not config['apiKey'] or not str(config['apiKey']).strip():
                config['apiKey'] = None
            else:
                config['apiKey'] = str(config['apiKey']).strip()
                
        if 'secret' in config:
            if not config['secret'] or not str(config['secret']).strip():
                config['secret'] = None
            else:
                config['secret'] = str(config['secret']).strip()
        
        # Add Proxy if configured and requested
        proxies = {}
        if use_proxy:
            if HTTP_PROXY: proxies['http'] = HTTP_PROXY
            if HTTPS_PROXY: proxies['https'] = HTTPS_PROXY
        
        if proxies:
            config['proxies'] = proxies
            
        # Set default timeout to avoid hanging
        if 'timeout' not in config:
            config['timeout'] = 15000 # 15 seconds

        # Fix Timestamp Error (-1021) by auto-syncing time
        # This applies to all exchanges (Binance, Bybit, etc.)
        if 'options' not in config:
            config['options'] = {}
        config['options']['adjustForTimeDifference'] = True

        # FORCE OVERRIDE for Bybit to bypass DNS blocks
        if exchange_id == 'bybit':
            # 1. Set hostname (CCXT uses this to replace {hostname} in templates)
            config['hostname'] = 'bytick.com'
            
            if 'urls' not in config:
                config['urls'] = {}
            if 'api' not in config['urls']:
                config['urls']['api'] = {}
            
            # 2. Explicitly set common endpoints to bytick.com
            # This ensures we don't use the blocked api.bybit.com
            config['urls']['api']['public'] = 'https://api.bytick.com'
            config['urls']['api']['private'] = 'https://api.bytick.com'
            config['urls']['api']['spot'] = 'https://api.bytick.com'
            config['urls']['api']['futures'] = 'https://api.bytick.com'
            config['urls']['api']['v5'] = 'https://api.bytick.com'
            
            print("[INFO] Applied Bybit DNS Bypass (api.bytick.com)")

        # FORCE OVERRIDE for Binance to bypass DNS blocks
        if exchange_id == 'binance':
            # NOTE: User reported using VPN. Standard endpoints should work best.
            # Using api-gcp might conflict with VPN routing or cause -2008 errors if the cluster doesn't recognize the key.
            # We will use the standard endpoint but keep the logic structure in case we need to revert.
            target_domain = 'api.binance.com' 
            
            if 'urls' not in config:
                config['urls'] = {}
            
            # Initialize 'api' structure if missing
            if 'api' not in config['urls']:
                config['urls']['api'] = {}
                
            # We will manually overwrite the base URLs
            base_url = f"https://{target_domain}"
            
            # Ensure 'api' is a dict (it might be in some versions)
            # We'll just force the main ones we use
            api_config = config['urls'].get('api', {})
            if isinstance(api_config, dict):
                api_config['public'] = f"{base_url}/api/v3"
                api_config['private'] = f"{base_url}/api/v3"
                # sapi (Margin/Futures/Earn)
                # NOTE: api-gcp.binance.com might NOT support sapi endpoints, causing -2008 errors.
                # We will stick to standard api.binance.com or api1.binance.com for sapi.
                api_config['sapi'] = "https://api.binance.com/sapi/v1"
                
                config['urls']['api'] = api_config
                print(f"[INFO] Applied Binance Configuration (Standard: {target_domain})")

        try:
            # Check if exchange is supported by CCXT
            if exchange_id in ccxt.exchanges:
                exchange_class = getattr(ccxt, exchange_id)
                exchange = exchange_class(config)
                
                # NUCLEAR OPTION: Post-Init Force Replace
                if exchange_id == 'bybit':
                    exchange.hostname = 'bytick.com' # Force property
                    
                    # Recursive URL replacement
                    def replace_urls(obj):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                obj[k] = replace_urls(v)
                        elif isinstance(obj, list):
                            return [replace_urls(i) for i in obj]
                        elif isinstance(obj, str):
                            return obj.replace('api.bybit.com', 'api.bytick.com')
                        return obj
                    
                    exchange.urls = replace_urls(exchange.urls)
                    print("[INFO] Post-Init: Replaced all bybit.com URLs with bytick.com")
                
                # --- AUTO-CORRECT TIME DRIFT ---
                if exchange_id == 'binance':
                    try:
                         # Calculate drift using public time endpoint
                         # We use a raw request to avoid auth signing issues
                         print("[INFO] Checking Binance Time Drift...")
                         server_time = exchange.fetch_time()
                         local_time = int(time.time() * 1000)
                         drift = local_time - server_time
                         
                         print(f"[INFO] Time Drift: {drift} ms (Positive = Local Ahead)")
                         
                         if abs(drift) > 1000:
                             print(f"[WARN] Significant time drift detected ({drift} ms). Applying fix.")
                             
                             # Fix 1: Set timeDifference explicitly for CCXT
                             # If local is ahead (drift > 0), we need to subtract drift.
                             # CCXT subtracts timeDifference if adjustForTimeDifference is True.
                             exchange.options['adjustForTimeDifference'] = True
                             
                             # Fix 2: Monkey-patch milliseconds() if drift is positive (Local Ahead)
                             # This is required because recvWindow doesn't fix "ahead" errors.
                             if drift > 500:
                                 # We set a safe offset to ensure we are strictly "behind" server time
                                 # e.g. server_time - 2000ms
                                 # local_time - safe_offset = server_time - 2000
                                 # safe_offset = local_time - server_time + 2000 = drift + 2000
                                 safe_offset = drift + 2000
                                 
                                 original_milliseconds = exchange.milliseconds
                                 exchange.milliseconds = lambda: original_milliseconds() - safe_offset
                                 print(f"[INFO] Applied Monkey-Patch to exchange.milliseconds() with offset -{safe_offset} ms")
                                 
                    except Exception as e:
                        print(f"[WARN] Failed to auto-correct time drift: {e}")
                
                return exchange
            else:
                print(f"[WARN] {exchange_id} not found in CCXT. Using CustomExchange adapter.")
                return CustomExchange(exchange_id, config)
        except Exception as e:
            print(f"[ERROR] Error initializing {exchange_id}: {e}. Falling back to CustomExchange.")
            return CustomExchange(exchange_id, config)

    def set_proxy_mode(self, use_proxy: bool):
        """Re-initialize exchange with or without proxy"""
        print(f"[INFO] Switching Proxy Mode: {'ON' if use_proxy else 'OFF'}")
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
                print(f"[ERROR] Failed to switch to {new_id}: {e}")
                self.offline_mode = False
                return self.switch_exchange()
        else:
            print("[CRITICAL] All backup exchanges failed. Strict LIVE MODE enforced.")
            self.failover_active = False
            self.offline_mode = False
            self.connection_status = "Error"
            self.connection_error = "All exchanges unreachable."
            # Raise exception to stop execution
            raise Exception("All exchanges unreachable. Unable to proceed in LIVE MODE.")

    def update_credentials(self, api_key: str, api_secret: str):
        """Update exchange credentials dynamically"""
        if self.exchange:
            # 1. Aggressive Sanitization
            api_key = str(api_key).strip().replace('\n', '').replace('\r', '').replace(' ', '')
            api_secret = str(api_secret).strip().replace('\n', '').replace('\r', '').replace(' ', '')
            
            self.exchange.apiKey = api_key
            self.exchange.secret = api_secret
            
            # DEBUG: Log key details (masked) to help diagnose -2008 errors
            k_len = len(self.exchange.apiKey)
            k_start = self.exchange.apiKey[:4] if k_len > 4 else "Short"
            print(f"[DEBUG] Updated Credentials. Key Length: {k_len}, Start: {k_start}")
            
            # Check for common copy-paste issues
            if len(self.exchange.apiKey) != 64 and self.exchange_id == 'binance':
                 print(f"[WARN] Binance API Key length is {k_len}, expected 64. This might be the issue.")
            
            # Reset connection status
            self.connection_status = "Connecting..."
            self.offline_mode = False
            self.connection_error = None
            
            try:
                # Force reload of markets with new credentials
                self.markets_loaded = False
                self.ensure_markets_loaded()
                self.connection_status = "Connected"
                print(f"Successfully connected to {self.exchange_id}")
            except Exception as e:
                self.connection_status = "Error"
                self.connection_error = str(e)
                print(f"Failed to connect after credential update: {e}")
                
                # Check for -2008 specifically and invalidate credentials here too
                if "-2008" in str(e) or "Invalid Api-Key ID" in str(e):
                    print("[CRITICAL] Invalid API Key detected in update_credentials. Clearing keys.")
                    self.exchange.apiKey = None
                    self.exchange.secret = None
                
                # Do NOT swallow the error here - let the UI handle it or re-raise
                # We want the user to know it failed immediately
                raise e

    def ensure_markets_loaded(self):
        if not self.markets_loaded and not self.offline_mode:
            try:
                # Set timeout to avoid hanging
                self.exchange.timeout = 20000 # 20 seconds
                
                print(f"[INFO] Loading markets for {self.exchange_id}...")
                self.exchange.load_markets()
                self.markets_loaded = True
                self.connection_status = "Connected"
                self.connection_error = None
                print(f"[SUCCESS] Markets loaded for {self.exchange_id}")
            except Exception as e:
                # RETRY LOGIC for Binance SAPI failures (often caused by permissions or IP blocks on SAPI endpoints)
                # We try to load markets in "Spot Only" mode by disabling fetchCurrencies (which calls sapi/v1/capital/config/getall)
                if self.exchange_id == 'binance' and ("sapi" in str(e) or "config/getall" in str(e)):
                    print(f"[WARN] Failed to load markets with SAPI (Funding/Margin). Retrying with Spot only...")
                    try:
                        # Disable fetching currencies (which uses SAPI)
                        self.exchange.options['fetchCurrencies'] = False
                        self.exchange.load_markets()
                        self.markets_loaded = True
                        self.connection_status = "Connected"
                        self.connection_error = None # Clear error as we successfully loaded Spot
                        print(f"[SUCCESS] Markets loaded (Spot Only mode)")
                        return
                    except Exception as retry_e:
                        print(f"[ERROR] Retry failed: {retry_e}")
                        # Fall through to original error handling
                
                error_msg = str(e)
                print(f"[ERROR] Error loading markets: {error_msg}")
                
                # STRICT LIVE MODE: NEVER fallback to Offline Mode if ANY error occurs.
                self.connection_status = "Error"
                self.connection_error = error_msg
                self.markets_loaded = False
                # Re-raise the exception so the UI knows it failed
                raise e

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
            
            # DNS FIX / SSL FIX: If we see SSLCertVerificationError or similar, it might be due to outdated certs or proxies.
            # We don't want to fall back to YF in LIVE MODE if possible, but for charts it's okay-ish.
            # However, for wallet balance, we never fall back.
            
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
                return pd.DataFrame()

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
            return pd.DataFrame()

    # Mock data generation removed to enforce Strict LIVE MODE
    # def _generate_mock_data(self, limit): ...

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

    def get_balance(self, force_refresh=False):
        # Strict LIVE MODE: No offline fallback
        if self.offline_mode:
            raise Exception("Offline Mode is disabled. Cannot fetch balance.")
            
        # Strict Authentication Check
        if not self.exchange or not self.exchange.apiKey or not self.exchange.secret:
             raise Exception("API Credentials missing. Please configure API Key and Secret.")

        try:
            # Pass params if needed, but standard fetch_balance usually suffices
            return self.exchange.fetch_balance()
        except Exception as e:
            # Re-raise exception so the Bot can handle it (e.g. -2008 check)
            print(f"[ERROR] Error fetching balance: {e}")
            raise e

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
            print(f"[ERROR] Error fetching positions: {e}")
            raise e

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
            raise Exception("Offline Mode is disabled. Cannot fetch order book.")
            
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

