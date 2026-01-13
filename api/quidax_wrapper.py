import requests
import time
import hmac
import hashlib

class QuidaxExchange:
    """
    Custom wrapper for Quidax API to mimic CCXT interface.
    Docs: https://docs.quidax.com/
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.quidax.com/api/v1"
        self.id = 'quidax'
        self.has = {'fetchBalance': True, 'createOrder': True, 'fetchTicker': True}

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def fetch_balance(self):
        """Fetch user wallets."""
        url = f"{self.base_url}/users/me/wallets"
        response = requests.get(url, headers=self._headers())
        data = response.json()
        
        if data.get('status') != 'success':
            raise Exception(f"Quidax Error: {data.get('message')}")
            
        balance = {'free': {}, 'total': {}}
        for wallet in data.get('data', []):
            curr = wallet.get('currency').upper()
            bal = float(wallet.get('balance', 0.0))
            balance[curr] = {'free': bal, 'total': bal}
            balance['free'][curr] = bal
            balance['total'][curr] = bal
        return balance

    def fetch_ticker(self, symbol):
        """Fetch ticker for symbol (e.g. BTCUSDT)."""
        # Quidax might use different format, assuming standard
        market = symbol.replace('/', '').lower() # btcusdt
        url = f"{self.base_url}/markets/tickers"
        response = requests.get(url) # Public endpoint usually
        data = response.json()
        
        if data.get('status') != 'success':
            raise Exception(f"Quidax Error: {data.get('message')}")
            
        tickers = data.get('data', {})
        # Find matching ticker
        ticker_data = tickers.get(market)
        if not ticker_data:
             # Try to find by iterating
             for k, v in tickers.items():
                 if k == market:
                     ticker_data = v
                     break
        
        if ticker_data:
            return {
                'symbol': symbol,
                'last': float(ticker_data.get('last', 0.0)),
                'high': float(ticker_data.get('high', 0.0)),
                'low': float(ticker_data.get('low', 0.0)),
                'volume': float(ticker_data.get('volume', 0.0)),
                'timestamp': time.time() * 1000
            }
        return {'last': 0.0}

    def create_order(self, symbol, type, side, amount, price=None, params={}):
        """Create Order."""
        market = symbol.replace('/', '').lower()
        url = f"{self.base_url}/users/me/orders"
        
        payload = {
            "market": market,
            "side": side,
            "ord_type": type, # limit or market
            "total_quantity": amount,
        }
        
        if type == 'limit' and price:
            payload['price'] = price
            
        response = requests.post(url, json=payload, headers=self._headers())
        data = response.json()
        
        if data.get('status') != 'success':
             raise Exception(f"Quidax Order Error: {data.get('message')}")
             
        order_data = data.get('data', {})
        return {
            'id': order_data.get('id'),
            'symbol': symbol,
            'status': order_data.get('state', 'open'),
            'amount': order_data.get('total_quantity'),
            'price': order_data.get('price')
        }
