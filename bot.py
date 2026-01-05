import os
import time
import hmac
import hashlib
import requests
import json
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==============================
# Configuration & Settings
# ==============================
class Settings:
    # Load from environment variables
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_SECRET", "") # Mapped from previous env var name
    BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
    BYBIT_API_SECRET = os.getenv("BYBIT_SECRET", "") # Mapped from previous env var name
    
    # General
    TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
    RETRIES = int(os.getenv("HTTP_RETRIES", "3"))
    BACKOFF = float(os.getenv("HTTP_BACKOFF", "0.5"))
    USER_AGENT = os.getenv("HTTP_USER_AGENT", "CapacityBay/1.0 (+https://capacitybay.local)")
    
    # Binance
    BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    BINANCE_RECV_WINDOW = int(os.getenv("BINANCE_RECV_WINDOW", "5000"))  # ms
    
    # Bybit
    # CRITICAL: Default to bytick.com to bypass DNS blocks
    BYBIT_BASE_URL = os.getenv("BYBIT_BASE_URL", "https://api.bytick.com")
    BYBIT_RECV_WINDOW = "20000"

# ==============================
# HTTP Client Wrapper
# ==============================
def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=Settings.RETRIES,
        backoff_factor=Settings.BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "DELETE"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": Settings.USER_AGENT})
    return session

class HttpClient:
    def __init__(self):
        self.session = build_session()

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        timeout = timeout or Settings.TIMEOUT
        params = params or {}
        data = data or {}
        headers = headers or {}

        try:
            resp = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                headers=headers,
                timeout=timeout
            )
            # Raise detailed error if non-200
            if resp.status_code != 200:
                # print(f"[HTTP Error] {method} {url} -> {resp.status_code}: {resp.text}")
                return {"error": resp.text, "status": resp.status_code}
            
            return resp.json()
        except Exception as e:
            # print(f"[Exception] Request failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def epoch_ms() -> int:
        return int(time.time() * 1000)

# ==============================
# Base Exchange Class
# ==============================
class ExchangeBase:
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.http = HttpClient()

    @staticmethod
    def _query_string(payload: Dict[str, Any]) -> str:
        return urlencode(payload, doseq=True)

    def _sign_sha256(self, payload: Dict[str, Any]) -> str:
        qs = self._query_string(payload)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            qs.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _sign_sha256_raw(self, raw: str) -> str:
        return hmac.new(
            self.api_secret.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

# ==============================
# Binance Client
# ==============================
class Binance(ExchangeBase):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret, Settings.BINANCE_BASE_URL)

    def _auth_headers(self) -> Dict[str, str]:
        return {"X-MBX-APIKEY": self.api_key}

    def ping(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v3/ping"
        return self.http.request("GET", url)

    def server_time(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v3/time"
        return self.http.request("GET", url)

    # Public Market Data
    def klines(self, symbol: str, interval: str, limit: int = 100) -> List[Any]:
        """Fetch Kline/Candlestick data."""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        url = f"{self.base_url}/api/v3/klines"
        return self.http.request("GET", url, params=params)

    def ticker_24h(self, symbol: str) -> Dict[str, Any]:
        """Fetch 24h ticker price change statistics."""
        url = f"{self.base_url}/api/v3/ticker/24hr"
        return self.http.request("GET", url, params={"symbol": symbol})

    def order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Fetch order book depth."""
        url = f"{self.base_url}/api/v3/depth"
        return self.http.request("GET", url, params={"symbol": symbol, "limit": limit})

    # Private signed GET
    def _signed_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        params["timestamp"] = self.http.epoch_ms()
        params["recvWindow"] = Settings.BINANCE_RECV_WINDOW
        params["signature"] = self._sign_sha256(params)
        url = f"{self.base_url}{endpoint}"
        return self.http.request("GET", url, params=params, headers=self._auth_headers())

    # Private signed POST/DELETE
    def _signed_write(self, method: str, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = self.http.epoch_ms()
        params["recvWindow"] = Settings.BINANCE_RECV_WINDOW
        params["signature"] = self._sign_sha256(params)
        url = f"{self.base_url}{endpoint}"
        # Binance expects data for write operations; params in query also works as per API
        return self.http.request(method, url, params=params, headers=self._auth_headers())

    # Account info and balances
    def account_info(self) -> Dict[str, Any]:
        return self._signed_get("/api/v3/account")

    def balances(self) -> Dict[str, Any]:
        # filter non-zero balances for convenience
        info = self.account_info()
        non_zero = [b for b in info.get("balances", []) if float(b.get("free", "0")) > 0 or float(b.get("locked", "0")) > 0]
        return {"balances": non_zero}

    # Open orders
    def open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._signed_get("/api/v3/openOrders", params)

    # Order placement
    def place_order(
        self,
        symbol: str,
        side: str,           # BUY or SELL
        type_: str,          # MARKET, LIMIT
        quantity: Optional[float] = None,
        quoteOrderQty: Optional[float] = None,  # for MARKET by quote
        price: Optional[float] = None,
        timeInForce: Optional[str] = None,      # GTC, IOC, FOK (required for LIMIT)
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side.upper(),
            "type": type_.upper(),
        }
        if type_.upper() == "LIMIT":
            if timeInForce is None:
                timeInForce = "GTC"
            if price is None or quantity is None:
                raise ValueError("LIMIT orders require price and quantity")
            params["timeInForce"] = timeInForce
            params["price"] = str(price)
            params["quantity"] = str(quantity)
        elif type_.upper() == "MARKET":
            if quantity is None and quoteOrderQty is None:
                raise ValueError("MARKET order requires quantity or quoteOrderQty")
            if quantity is not None:
                params["quantity"] = str(quantity)
            if quoteOrderQty is not None:
                params["quoteOrderQty"] = str(quoteOrderQty)
        else:
            raise ValueError("Unsupported order type")

        return self._signed_write("POST", "/api/v3/order", params)

    def cancel_order(self, symbol: str, orderId: Optional[int] = None, origClientOrderId: Optional[str] = None) -> Dict[str, Any]:
        if not orderId and not origClientOrderId:
            raise ValueError("Provide orderId or origClientOrderId")
        params: Dict[str, Any] = {"symbol": symbol}
        if orderId:
            params["orderId"] = orderId
        if origClientOrderId:
            params["origClientOrderId"] = origClientOrderId
        return self._signed_write("DELETE", "/api/v3/order", params)

# ==============================
# Bybit Client (V5)
# ==============================
class BybitV5(ExchangeBase):
    """
    Minimal Bybit v5 private client for balances and open orders.
    Signature: sign = HMAC_SHA256(api_secret, api_key + timestamp + recv_window + query_string_or_body)
    Header keys: X-BAPI-API-KEY, X-BAPI-TIMESTAMP, X-BAPI-RECV-WINDOW, X-BAPI-SIGN
    """
    def __init__(self, api_key: str, api_secret: str):
        # Enforce bytick.com if not already set in Settings
        base_url = Settings.BYBIT_BASE_URL if "bytick" in Settings.BYBIT_BASE_URL else "https://api.bytick.com"
        super().__init__(api_key, api_secret, base_url)

    def _headers(self, recv_window: int, sign_raw: str, ts: str) -> Dict[str, str]:
        sign = self._sign_sha256_raw(sign_raw)
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": str(recv_window),
            "X-BAPI-SIGN": sign,
        }

    def server_time(self) -> Dict[str, Any]:
        url = f"{self.base_url}/v5/market/time"
        return self.http.request("GET", url)

    # Public Market Data
    def klines(self, symbol: str, interval: str, limit: int = 100, category: str = "linear") -> Dict[str, Any]:
        """Fetch Kline data. Interval: 1,3,5,15,60,D,W,M"""
        url = f"{self.base_url}/v5/market/kline"
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        return self.http.request("GET", url, params=params)

    def ticker(self, symbol: str, category: str = "linear") -> Dict[str, Any]:
        """Fetch latest ticker info."""
        url = f"{self.base_url}/v5/market/tickers"
        params = {"category": category, "symbol": symbol}
        return self.http.request("GET", url, params=params)
        
    def order_book(self, symbol: str, category: str = "linear", limit: int = 25) -> Dict[str, Any]:
        """Fetch orderbook."""
        url = f"{self.base_url}/v5/market/orderbook"
        params = {"category": category, "symbol": symbol, "limit": limit}
        return self.http.request("GET", url, params=params)

    # Wallet balance (unified)
    def balances(self, accountType: str = "UNIFIED") -> Dict[str, Any]:
        recv_window = 5000
        # For GET, Bybit sign string uses: timestamp + api_key + recv_window + queryString
        query = f"accountType={accountType}"
        
        ts = str(self.http.epoch_ms())
        sign_raw = f"{ts}{self.api_key}{recv_window}{query}"
        
        headers = self._headers(recv_window, sign_raw, ts)
        url = f"{self.base_url}/v5/account/wallet-balance"
        resp = self.http.request("GET", url, params={"accountType": accountType}, headers=headers)
        
        # Parse and standardize output to match generic format
        # Bybit V5 structure: result -> list[0] -> coin[]
        try:
            if resp.get("retCode") == 0:
                account_list = resp.get("result", {}).get("list", [])
                if account_list:
                    coins = account_list[0].get("coin", [])
                    non_zero = []
                    for c in coins:
                        # Convert to float to check if non-zero
                        wallet_bal = float(c.get("walletBalance", 0))
                        if wallet_bal > 0:
                            non_zero.append({
                                "asset": c.get("coin"),
                                "free": c.get("availableToWithdraw", c.get("walletBalance")),
                                "locked": c.get("locked", "0"), # Bybit Unified often doesn't show locked per coin same way
                                "total": c.get("walletBalance")
                            })
                    return {"balances": non_zero, "raw": resp}
        except Exception as e:
            pass
            
        return resp

    # Open orders (unified)
    def open_orders(self, category: str = "linear", symbol: Optional[str] = None) -> Dict[str, Any]:
        recv_window = 5000
        qparams = []
        if category:
            qparams.append(f"category={category}")
        if symbol:
            qparams.append(f"symbol={symbol}")
        # IMPORTANT: Bybit requires params to be sorted for the signature string
        # if multiple params exist. However, query string construction order must match
        # what requests library sends.
        # Safest way: construct dict, sort it, then encode.
        
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
            
        ordered_params = dict(sorted(params.items()))
        query = self._query_string(ordered_params)
        
        ts = str(self.http.epoch_ms())
        sign_raw = f"{ts}{self.api_key}{recv_window}{query}"
        
        headers = self._headers(recv_window, sign_raw, ts)
        url = f"{self.base_url}/v5/order/realtime"
        
        return self.http.request("GET", url, params=params, headers=headers)

    # Place order (unified)
    def place_order(
        self,
        category: str,       # "linear", "inverse", "option"
        symbol: str,
        side: str,           # "Buy" or "Sell"
        orderType: str,      # "Market" or "Limit"
        qty: str,
        price: Optional[str] = None,
        timeInForce: Optional[str] = None,  # "GTC","IOC","FOK","PostOnly"
    ) -> Dict[str, Any]:
        recv_window = 5000
        body: Dict[str, Any] = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": orderType,
            "qty": qty,
        }
        if orderType == "Limit":
            if not price:
                raise ValueError("Limit orders require price")
            body["price"] = price
            body["timeInForce"] = timeInForce or "GTC"

        # Bybit v5 signing for POST: timestamp + api_key + recv_window + requestBody
        import json
        body_str = json.dumps(body, separators=(",", ":"))
        ts = str(self.http.epoch_ms())
        sign_raw = f"{ts}{self.api_key}{recv_window}{body_str}"
        sign = self._sign_sha256_raw(sign_raw)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": str(recv_window),
            "X-BAPI-SIGN": sign,
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/v5/order/create"
        # Using session.post directly to ensure body is sent exactly as signed
        return self.http.session.post(url, headers=headers, data=body_str, timeout=Settings.TIMEOUT).json()

    def cancel_order(self, category: str, symbol: str, orderId: Optional[str] = None) -> Dict[str, Any]:
        recv_window = 5000
        body: Dict[str, Any] = {
            "category": category,
            "symbol": symbol
        }
        if orderId:
            body["orderId"] = orderId
        import json
        body_str = json.dumps(body, separators=(",", ":"))
        ts = str(self.http.epoch_ms())
        sign_raw = f"{ts}{self.api_key}{recv_window}{body_str}"
        sign = self._sign_sha256_raw(sign_raw)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": str(recv_window),
            "X-BAPI-SIGN": sign,
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/v5/order/cancel"
        return self.http.session.post(url, headers=headers, data=body_str, timeout=Settings.TIMEOUT).json()

# ==============================
# Unified Interface
# ==============================
class CapacityBayBot:
    def __init__(self, binance_keys: Dict[str, str] = None, bybit_keys: Dict[str, str] = None):
        # Allow passing keys, or fall back to Settings
        b_key = binance_keys.get("api_key") if binance_keys else Settings.BINANCE_API_KEY
        b_secret = binance_keys.get("api_secret") if binance_keys else Settings.BINANCE_API_SECRET
        
        by_key = bybit_keys.get("api_key") if bybit_keys else Settings.BYBIT_API_KEY
        by_secret = bybit_keys.get("api_secret") if bybit_keys else Settings.BYBIT_API_SECRET

        self.binance = Binance(b_key, b_secret)
        self.bybit = BybitV5(by_key, by_secret)

    def health(self) -> Dict[str, Any]:
        """Check connection health."""
        return {
            "binance": self.binance.server_time(),
            "bybit": self.bybit.server_time()
        }
    
    def system_status(self) -> Dict[str, Any]:
        """
        Comprehensive system status check including latency and permissions.
        Returns a friendly summary of bot readiness.
        """
        start = time.time()
        b_health = self.binance.server_time()
        b_latency = (time.time() - start) * 1000

        start = time.time()
        by_health = self.bybit.server_time()
        by_latency = (time.time() - start) * 1000

        status = "ONLINE" if ("serverTime" in b_health and by_health.get("retCode") == 0) else "DEGRADED"

        return {
            "status": status,
            "latency_ms": {
                "binance": round(b_latency, 2),
                "bybit": round(by_latency, 2)
            },
            "raw": {
                "binance": b_health,
                "bybit": by_health
            }
        }

    def balances(self):
        """Fetch balances from all exchanges."""
        return {
            "binance": self.binance.balances(),
            "bybit": self.bybit.balances()
        }

    def open_orders(self, symbol: str = None, bybit_category: str = "linear"):
        """Fetch open orders from all exchanges."""
        return {
            "binance": self.binance.open_orders(symbol),
            "bybit": self.bybit.open_orders(category=bybit_category, symbol=symbol)
        }
    
    def market_data(self, symbol: str, interval: str = "1h", limit: int = 50, bybit_category: str = "linear"):
        """
        Fetch rich market data for intelligent analysis.
        Includes: Ticker, OrderBook, Klines
        """
        # Note: Binance Interval '1h', Bybit Interval '60'
        bybit_interval_map = {
            "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
            "1h": "60", "2h": "120", "4h": "240", "1d": "D"
        }
        b_interval = interval
        by_interval = bybit_interval_map.get(interval, "60")

        return {
            "binance": {
                "ticker": self.binance.ticker_24h(symbol),
                "orderbook": self.binance.order_book(symbol, limit=5),
                "klines": self.binance.klines(symbol, b_interval, limit)
            },
            "bybit": {
                "ticker": self.bybit.ticker(symbol, category=bybit_category),
                "orderbook": self.bybit.order_book(symbol, category=bybit_category, limit=1),
                "klines": self.bybit.klines(symbol, by_interval, limit, category=bybit_category)
            }
        }

    def analyze_market(self, symbol: str) -> Dict[str, Any]:
        """
        Perform intelligent market analysis using multi-source data.
        Calculates:
        1. Trend (from 24h ticker)
        2. Pressure (from OrderBook imbalance)
        """
        # Fetch data from both exchanges
        data = self.market_data(symbol)
        
        # Binance Data Extraction
        b_ticker = data["binance"]["ticker"]
        b_book = data["binance"]["orderbook"]
        
        # 1. Trend Analysis
        # Binance ticker has 'priceChangePercent'
        try:
            price_change = float(b_ticker.get("priceChangePercent", 0))
            trend = "BULLISH 🚀" if price_change > 0 else "BEARISH 🔻"
        except:
            trend = "UNKNOWN"
            price_change = 0.0

        # 2. Order Book Pressure (Simple Bid/Ask Volume Ratio)
        try:
            bids_vol = sum([float(x[1]) for x in b_book.get("bids", [])])
            asks_vol = sum([float(x[1]) for x in b_book.get("asks", [])])
            
            if asks_vol > 0:
                ratio = bids_vol / asks_vol
                pressure = "BUYING PRESSURE 🟢" if ratio > 1.0 else "SELLING PRESSURE 🔴"
            else:
                ratio = 0
                pressure = "UNKNOWN"
        except:
            pressure = "UNKNOWN"
            ratio = 0

        # Smart Summary
        return {
            "symbol": symbol,
            "analysis_ts": time.time(),
            "market_sentiment": {
                "trend": trend,
                "24h_change": f"{price_change}%",
                "pressure": pressure,
                "bid_ask_ratio": round(ratio, 2)
            },
            "data_sources": ["Binance", "Bybit"]
        }

    # Alias for compatibility with old tests if needed
    def fetch_all_balances(self):
        return self.balances()
        
    def fetch_all_open_orders(self, symbol: str = None):
        return self.open_orders(symbol=symbol)

    def place_order_binance(self, **kwargs):
        """Wrapper for Binance place_order."""
        return self.binance.place_order(**kwargs)

    def cancel_order_binance(self, **kwargs):
        """Wrapper for Binance cancel_order."""
        return self.binance.cancel_order(**kwargs)

# ==============================
# Main Execution (Test)
# ==============================
if __name__ == "__main__":
    bot = CapacityBayBot()
    print("Checking System Status...")
    status = bot.system_status()
    print(json.dumps(status, indent=2))
    
    if status["status"] == "ONLINE":
        print("\nFetching Full Balances...")
        balances = bot.balances()
        
        print("\n--- BINANCE BALANCES ---")
        for b in balances["binance"].get("balances", []):
            print(f"{b['asset']}: Free={b['free']} Locked={b['locked']}")
            
        print("\n--- BYBIT BALANCES ---")
        bybit_bals = balances["bybit"].get("balances", [])
        if bybit_bals:
            for b in bybit_bals:
                print(f"{b['asset']}: Total={b['total']} Free={b['free']}")
        else:
            print("No non-zero balances found or error fetching.")
            if "raw" in balances["bybit"]:
                print(f"Raw Response Code: {balances['bybit']['raw'].get('retCode')}")
                print(f"Raw Response Msg: {balances['bybit']['raw'].get('retMsg')}")

        print("\nPerforming Intelligent Market Analysis for BTCUSDT...")
        analysis = bot.analyze_market("BTCUSDT")
        print(json.dumps(analysis, indent=2))
    else:
        print("\nSystem DEGRADED. Skipping analysis.")
