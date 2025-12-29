
import requests
import json
from config.settings import COINAPI_KEY, CRYPTOAPIS_KEY, CMC_API_KEY

class FundamentalAnalysis:
    def __init__(self):
        # CoinMarketCap
        self.cmc_key = CMC_API_KEY
        self.cmc_url = "https://pro-api.coinmarketcap.com/v1" # Production URL
        self.cmc_headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.cmc_key,
        }

        # CoinAPI
        self.coinapi_key = COINAPI_KEY
        self.coinapi_url = "https://rest.coinapi.io/v1"
        self.coinapi_headers = {'X-CoinAPI-Key': self.coinapi_key}
        
        # CryptoAPIs
        self.cryptoapis_key = CRYPTOAPIS_KEY
        self.cryptoapis_url = "https://rest.cryptoapis.io/v2"
        self.cryptoapis_headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.cryptoapis_key
        }

    def get_asset_details(self, symbol: str) -> dict:
        """
        Fetch fundamental asset data.
        Priority: CoinMarketCap -> CoinAPI -> CoinGecko -> CryptoAPIs
        """
        try:
            # Extract base currency
            base_currency = symbol.split('/')[0] if '/' in symbol else symbol
            
            # 1. Try CoinMarketCap (Highest Quality)
            cmc_data = self.get_coinmarketcap_data(base_currency)
            if cmc_data:
                return cmc_data

            # 2. Fallback to CoinAPI
            url = f"{self.coinapi_url}/assets/{base_currency}"
            response = requests.get(url, headers=self.coinapi_headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    asset = data[0]
                    return {
                        'name': asset.get('name', 'Unknown'),
                        'asset_id': asset.get('asset_id', base_currency),
                        'volume_1day_usd': asset.get('volume_1day_usd', 0),
                        'volume_1mth_usd': asset.get('volume_1mth_usd', 0),
                        'price_usd': asset.get('price_usd', 0),
                        'supply_current': asset.get('supply_current', 0),
                        'supply_total': asset.get('supply_total', 0),
                        'market_cap': asset.get('price_usd', 0) * asset.get('supply_current', 0)
                    }
            
            # 3. Fallback to CoinGecko (Free Public API)
            cg_data = self.get_coingecko_asset_details(base_currency)
            if cg_data:
                return cg_data

            # 4. Fallback to CryptoAPIs
            return self.get_cryptoapis_asset_details(base_currency)

        except Exception as e:
            print(f"Error fetching fundamentals: {e}")
            return {}

    def get_coinmarketcap_data(self, symbol: str) -> dict:
        """
        Fetch data from CoinMarketCap Pro API
        """
        try:
            url = f"{self.cmc_url}/cryptocurrency/quotes/latest"
            parameters = {
                'symbol': symbol,
                'convert': 'USD'
            }
            
            response = requests.get(url, headers=self.cmc_headers, params=parameters, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # CMC structure: data -> {SYMBOL} -> [quote_data] or {quote_data}
                # Check for error status in body
                if data.get('status', {}).get('error_code') != 0:
                    return {}

                symbol_data = data.get('data', {}).get(symbol)
                
                # Handling if symbol_data is a list (duplicate symbols) or dict
                if isinstance(symbol_data, list):
                    item = symbol_data[0]
                else:
                    item = symbol_data
                
                if not item: return {}

                quote = item.get('quote', {}).get('USD', {})
                
                return {
                    'name': item.get('name', symbol),
                    'asset_id': item.get('symbol', symbol),
                    'rank': item.get('cmc_rank', 0),
                    'volume_1day_usd': quote.get('volume_24h', 0),
                    'volume_change_24h': quote.get('volume_change_24h', 0),
                    'price_usd': quote.get('price', 0),
                    'percent_change_1h': quote.get('percent_change_1h', 0),
                    'percent_change_24h': quote.get('percent_change_24h', 0),
                    'percent_change_7d': quote.get('percent_change_7d', 0),
                    'supply_current': item.get('circulating_supply', 0),
                    'supply_total': item.get('total_supply', 0),
                    'market_cap': quote.get('market_cap', 0),
                    'market_dominance': quote.get('market_cap_dominance', 0),
                    'source': 'CoinMarketCap'
                }
        except Exception as e:
            print(f"CoinMarketCap Error: {e}")
        return {}

    def get_coingecko_asset_details(self, base_currency: str) -> dict:
        """
        Fallback using CoinGecko Public API (Free)
        """
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'symbols': base_currency.lower()
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    asset = data[0]
                    return {
                        'name': asset.get('name', base_currency),
                        'asset_id': asset.get('id', base_currency),
                        'volume_1day_usd': asset.get('total_volume', 0),
                        'volume_1mth_usd': 0,
                        'price_usd': asset.get('current_price', 0),
                        'supply_current': asset.get('circulating_supply', 0),
                        'supply_total': asset.get('total_supply', 0),
                        'market_cap': asset.get('market_cap', 0)
                    }
        except Exception as e:
            print(f"CoinGecko Fallback Error: {e}")
            
        return {}


    def get_cryptoapis_asset_details(self, base_currency: str) -> dict:
        """
        Fallback/Alternative fetch using CryptoAPIs
        """
        try:
            # Using 'market-data' endpoint to get asset details
            # https://rest.cryptoapis.io/v2/market-data/assets/{assetId}
            url = f"{self.cryptoapis_url}/market-data/assets/{base_currency}"
            response = requests.get(url, headers=self.cryptoapis_headers)
            
            if response.status_code == 200:
                data = response.json()
                # Structure depends on API response, assuming standard 'data' envelope
                # This is a best-effort implementation based on common patterns
                item = data.get('data', {}).get('item', {})
                if item:
                    return {
                        'name': item.get('name', base_currency),
                        'asset_id': item.get('symbol', base_currency),
                        'volume_1day_usd': 0, # Might not be directly available in this endpoint
                        'volume_1mth_usd': 0,
                        'price_usd': float(item.get('originalSymbol', {}).get('price', 0) or 0), # Hypothetical path
                        'supply_current': float(item.get('circulatingSupply', 0) or 0),
                        'supply_total': float(item.get('totalSupply', 0) or 0),
                        'market_cap': float(item.get('marketCap', 0) or 0)
                    }
        except Exception as e:
            print(f"CryptoAPIs Fallback Error: {e}")
        return {}

    def get_on_chain_data(self, symbol: str) -> dict:
        """
        Fetch On-Chain data using CryptoAPIs.
        """
        try:
            base_currency = symbol.split('/')[0] if '/' in symbol else symbol
            # Example endpoint for blockchain data
            # url = f"{self.cryptoapis_url}/blockchain-data/{base_currency.lower()}/mainnet/blocks/last"
            # response = requests.get(url, headers=self.cryptoapis_headers)
            # if response.status_code == 200:
            #     return response.json()
            return {}
        except Exception as e:
            print(f"CryptoAPIs Error: {e}")
            return {}

    def get_market_sentiment(self):
        """
        Fetch Fear & Greed Index from Alternative.me (Public/Free).
        """
        try:
            response = requests.get("https://api.alternative.me/fng/")
            if response.status_code == 200:
                data = response.json()
                return data['data'][0]
        except:
            return {'value': 50, 'value_classification': 'Neutral'}
