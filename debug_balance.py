
import os
import sys
import logging
import json
import traceback

# Add project root to path
sys.path.append(os.getcwd())

from core.data import DataManager

# Setup logging
logging.basicConfig(level=logging.INFO)

def debug_balance_fetch():
    print("--- Debugging Bybit Balance Fetch ---")
    
    # Check Environment Variables
    api_key = os.getenv('BYBIT_API_KEY')
    print(f"API Key present: {bool(api_key)}")
    
    try:
        # Initialize DataManager
        dm = DataManager('bybit')
        
        # Verify URL Override
        print(f"Exchange URLs: {dm.exchange.urls.get('api', 'Not Found')}")
        
        # Force load markets first
        print("Loading markets...")
        dm.ensure_markets_loaded()
        print("Markets loaded.")
        
        # Fetch Balance (Default)
        print("Fetching balance (Default)...")
        balance = dm.get_balance()
        print(f"Default Balance Result: {json.dumps(balance.get('total', {}), indent=2)}")

        # Fetch Funding Wallet
        print("\nFetching Funding Wallet...")
        try:
            fund_bal = dm.exchange.fetch_balance({'type': 'fund'}) # or accountType='FUND'
            print(f"Funding Wallet: {json.dumps(fund_bal.get('total', {}), indent=2)}")
            if 'info' in fund_bal:
                 print(f"Funding Raw Info: {json.dumps(fund_bal['info'], default=str)[:200]}")
        except Exception as e:
            print(f"Funding fetch failed: {e}")

        # Fetch Unified/Contract explicitly
        print("\nFetching Unified/Contract...")
        try:
            uni_bal = dm.exchange.fetch_balance({'type': 'swap'})
            print(f"Unified/Swap Wallet: {json.dumps(uni_bal.get('total', {}), indent=2)}")
        except Exception as e:
            print(f"Unified fetch failed: {e}")
            
        # Fetch Spot explicitly
        print("\nFetching Spot...")
        try:
            spot_bal = dm.exchange.fetch_balance({'type': 'spot'})
            print(f"Spot Wallet: {json.dumps(spot_bal.get('total', {}), indent=2)}")
        except Exception as e:
            print(f"Spot fetch failed: {e}")

    except Exception as e:
        print("\n❌ CRITICAL ERROR:")
        traceback.print_exc()

if __name__ == "__main__":
    debug_balance_fetch()
