
import ccxt
import time
from config.exchanges import EXCHANGES

def debug_bybit_connection():
    print("--- Debugging Bybit Connection ---")
    
    config = EXCHANGES['bybit']
    print(f"API Key: {config['apiKey'][:4]}...{config['apiKey'][-4:]}")
    print(f"Options: {config['options']}")
    
    exchange = ccxt.bybit(config)
    
    # Connectivity Test
    import socket
    try:
        print("\n0. Testing Connectivity...")
        socket.gethostbyname("google.com")
        print("✅ Google.com is reachable")
        socket.gethostbyname("api.bybit.com")
        print("✅ api.bybit.com is reachable")
    except socket.gaierror as e:
        print(f"❌ DNS Resolution Failed: {e}")
        print("⚠️ ACTION REQUIRED: You might be in a restricted region or have DNS issues.")
        print("   If you are in the US/UK/Canada, Bybit might be blocked by your ISP.")
        print("   Please use a VPN or change your DNS settings.")
        return
    
    try:
        print("\n1. Loading Markets...")
        exchange.load_markets()
        print("✅ Markets Loaded Successfully")
    except Exception as e:
        import traceback
        print(f"❌ Failed to load markets: {e}")
        traceback.print_exc()
        return

    try:
        print("\n2. Fetching Balance...")
        balance = exchange.fetch_balance()
        print("✅ Balance Fetched Successfully")
        print(f"Total USDT: {balance['total'].get('USDT', 0)}")
        print(f"Free USDT: {balance['free'].get('USDT', 0)}")
    except Exception as e:
        print(f"❌ Failed to fetch balance: {e}")
        print("Possible causes: IP Restriction, Invalid Permissions, or UTA configuration.")

    try:
        print("\n3. Fetching Positions (BTC/USDT:USDT)...")
        # Bybit swap symbols often need specific formatting
        positions = exchange.fetch_positions(['BTC/USDT:USDT'])
        print(f"✅ Positions Fetched: {len(positions)}")
        for p in positions:
            if float(p['contracts']) > 0:
                print(f"  - {p['symbol']}: {p['side']} {p['contracts']}")
    except Exception as e:
        print(f"❌ Failed to fetch positions: {e}")

if __name__ == "__main__":
    debug_bybit_connection()
