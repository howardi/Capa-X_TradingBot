
import ccxt
import requests
import json

def test_connectivity():
    print("Testing Connectivity...")

    # 1. Test Bybit (Primary)
    print("\n1. Testing Bybit...")
    try:
        bybit = ccxt.bybit()
        bybit.fetch_ticker('BTC/USDT')
        print("✅ Bybit: Connected")
    except Exception as e:
        print(f"❌ Bybit: Failed ({str(e)[:50]}...)")

    # 2. Test Binance (Public Fallback)
    print("\n2. Testing Binance (Public)...")
    try:
        binance = ccxt.binance()
        binance.fetch_ticker('BTC/USDT')
        print("✅ Binance: Connected")
    except Exception as e:
        print(f"❌ Binance: Failed ({str(e)[:50]}...)")

    # 3. Test CoinAPI via CCXT
    print("\n3. Testing CoinAPI via CCXT...")
    try:
        coinapi = ccxt.coinapi({
            'apiKey': '729d83da-285b-4ef5-9a71-933a5c56d275'
        })
        # CoinAPI requires specific symbol formats sometimes, but ccxt handles it
        # However, free keys often have limitations.
        ticker = coinapi.fetch_ticker('BTC/USD')
        print("✅ CoinAPI (CCXT): Connected")
        print(ticker)
    except Exception as e:
        print(f"❌ CoinAPI (CCXT): Failed ({str(e)[:100]}...)")

    # 4. Test CryptoAPIs
    print("\n4. Testing CryptoAPIs...")
    key = "5bf465481226e6debc6cb635437761e73cbcea8e"
    # Basic endpoint check
    url = "https://rest.cryptoapis.io/v2/market-data/assets/details/BTC" # Example endpoint
    headers = {'Content-Type': 'application/json', 'X-API-Key': key}
    try:
        response = requests.get(url, headers=headers)
        # Note: CryptoAPIs might require more specific setup, just checking generic reachability
        if response.status_code == 200:
             print("✅ CryptoAPIs: Connected")
        else:
             print(f"❌ CryptoAPIs: Failed ({response.status_code}) - {response.text[:50]}")
    except Exception as e:
         print(f"❌ CryptoAPIs: Failed ({str(e)[:50]}...)")

if __name__ == "__main__":
    test_connectivity()
