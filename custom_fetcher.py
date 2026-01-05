
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
                print(f"[HTTP Error] {method} {url} -> {resp.status_code}: {resp.text}")
                return {"error": resp.text, "status": resp.status_code}
            
            return resp.json()
        except Exception as e:
            print(f"[Exception] Request failed: {e}")
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
        url = f"{self.base_url}/v5/public/time"
        return self.http.request("GET", url)

    # Wallet balance (unified)
    def balances(self, accountType: str = "UNIFIED") -> Dict[str, Any]:
        recv_window = 5000
        # For GET, Bybit sign string uses: timestamp + api_key + recv_window + queryString
        query = f"accountType={accountType}"
        
        ts = str(self.http.epoch_ms())
        sign_raw = f"{ts}{self.api_key}{recv_window}{query}"
        
        headers = self._headers(recv_window, sign_raw, ts)
        url = f"{self.base_url}/v5/account/wallet-balance"
        return self.http.request("GET", url, params={"accountType": accountType}, headers=headers)

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
class CapacityBayTradingBot:
    def __init__(self, binance_keys: Dict[str, str] = None, bybit_keys: Dict[str, str] = None):
        # Allow passing keys, or fall back to Settings
        b_key = binance_keys.get("api_key") if binance_keys else Settings.BINANCE_API_KEY
        b_secret = binance_keys.get("api_secret") if binance_keys else Settings.BINANCE_API_SECRET
        
        by_key = bybit_keys.get("api_key") if bybit_keys else Settings.BYBIT_API_KEY
        by_secret = bybit_keys.get("api_secret") if bybit_keys else Settings.BYBIT_API_SECRET

        self.binance = Binance(b_key, b_secret)
        self.bybit = BybitV5(by_key, by_secret)

    def fetch_all_balances(self):
        """Fetch balances from all exchanges."""
        return {
            "binance": self.binance.balances(),
            "bybit": self.bybit.balances()
        }

    def fetch_all_open_orders(self, symbol: str = None):
        """Fetch open orders from all exchanges."""
        return {
            "binance": self.binance.open_orders(symbol),
            "bybit": self.bybit.open_orders(symbol=symbol)
        }

# ==============================
# Main Execution (Test)
# ==============================
if __name__ == "__main__":
    bot = CapacityBayTradingBot()
    bot.run()
