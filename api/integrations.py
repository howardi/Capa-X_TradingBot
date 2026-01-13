import requests
import os
from api.services.exchange_service import ExchangeService

# Initialize Service
exchange_service = ExchangeService()

# --- CoinCodex Data ---
def get_coin(symbol="BTC"):
    try:
        url = f"https://coincodex.com/api/coincodex/get_coin/{symbol}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Failed to fetch coin data: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_coin_history(symbol="BTC", start="2025-01-01", end="2025-01-10", samples=20):
    try:
        url = f"https://coincodex.com/api/coincodex/get_coin_history/{symbol}/{start}/{end}/{samples}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Failed to fetch coin history: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# --- Exchange Wrappers (Delegating to ExchangeService) ---

def kucoin_place_order(symbol="BTC-USDT", side="buy", size="0.001", price="40000"):
    """Wrapper for KuCoin order via ExchangeService."""
    return exchange_service.create_order('kucoin', symbol, 'limit', side, float(size), float(price))

def bybit_place_order(symbol="BTCUSDT", side="Buy", qty=0.001, price=40000):
    """Wrapper for Bybit order via ExchangeService."""
    return exchange_service.create_order('bybit', symbol, 'limit', side.lower(), float(qty), float(price))

def okx_place_order(symbol="BTC-USDT", side="buy", size="0.001", price="40000"):
    """Wrapper for OKX order via ExchangeService."""
    return exchange_service.create_order('okx', symbol, 'limit', side.lower(), float(size), float(price))

def luno_get_balance():
    """Wrapper for Luno balance via ExchangeService."""
    exchange = exchange_service.get_exchange_by_id('luno')
    if exchange:
        try:
            return exchange.fetch_balance()
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Luno not configured"}

# --- Example Bot Logic ---
def run_bot_logic():
    try:
        btc_data = get_coin("BTC")
        if "error" in btc_data:
            return btc_data
            
        # CoinCodex returns different structures, usually 'last_price_usd' or similar
        price = btc_data.get("last_price_usd")
        
        result = {
            "coin": "BTC",
            "price": price,
            "signal": "Hold"
        }

        if price and float(price) < 40000:
            result["signal"] = "Buy BTC"
            # We can optionally execute here using exchange_service
            
        return result
    except Exception as e:
        return {"error": str(e)}
