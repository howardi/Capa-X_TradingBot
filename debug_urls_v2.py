
import ccxt
import json
import os
from dotenv import load_dotenv
from core.data import DataManager

load_dotenv()

def inspect_urls_detailed():
    print("--- Inspecting Bybit URLs in DataManager ---")
    
    # Initialize DataManager (which applies the overrides)
    dm = DataManager('bybit')
    
    # Inspect the urls dictionary
    urls = dm.exchange.urls
    print(json.dumps(urls, indent=2))
    
    # Check if there are any other URL properties
    print(f"\nHostname: {dm.exchange.hostname}")
    
    # Try to reproduce the error call
    # The error was: GET https://api.bybit.com/v5/asset/coin/query-info?
    # This looks like it might be triggered by fetch_currencies or load_markets
    
    print("\n--- Attempting to trigger the specific URL ---")
    
    try:
        # Check if we can find which method uses this endpoint
        # v5/asset/coin/query-info is likely 'private_get_v5_asset_coin_query_info'
        if hasattr(dm.exchange, 'private_get_v5_asset_coin_query_info'):
             print("Found method: private_get_v5_asset_coin_query_info")
             # We can't easily see the URL it generates without running it and failing or mocking
    except:
        pass

    # Try to reproduce with fetch_order_book
    print("\nCalling fetch_order_book('BTC/USDT')...")
    try:
        dm.exchange.fetch_order_book('BTC/USDT', limit=5)
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_urls_detailed()
