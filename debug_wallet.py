import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add root to path
sys.path.append(os.getcwd())

from core.bot import TradingBot
import json

def test_wallet():
    print("Initializing Bot for Bybit...")
    bot = TradingBot('bybit')
    
    # Check credentials
    api_key = os.getenv('BYBIT_API_KEY')
    secret = os.getenv('BYBIT_SECRET')
    
    if not api_key or not secret:
        print("Error: BYBIT_API_KEY or BYBIT_SECRET not found in .env")
        return

    print("Updating credentials...")
    bot.data_manager.update_credentials(api_key, secret)
    
    print("Setting mode to CEX_Direct...")
    bot.set_trading_mode('CEX_Direct')
    
    print("Syncing live balance...")
    try:
        # Debug: Print raw balance first
        print("Fetching raw balance...")
        raw_bal = bot.data_manager.get_balance()
        
        # clean for printing
        def safe_dump(d):
            try:
                return json.dumps(d, indent=2, default=str)
            except:
                return str(d)
        
        print(f"RAW BALANCE KEYS: {list(raw_bal.keys())}")
        if 'info' in raw_bal:
             print(f"RAW INFO: {safe_dump(raw_bal['info'])}")
        
        # Check Funding Wallet
        print("\nChecking Funding Wallet...")
        try:
            fund_bal = bot.data_manager.exchange.fetch_balance({'type': 'fund'})
            print(f"FUNDING BALANCE KEYS: {list(fund_bal.keys())}")
            if 'total' in fund_bal:
                print(f"Funding Total: {fund_bal['total']}")
        except Exception as e:
            print(f"Funding fetch failed: {e}")

        bot.sync_live_balance()
        print("\n--- Wallet Balances ---")
        if bot.wallet_balances:
            for item in bot.wallet_balances:
                print(item)
        else:
            print("No wallet balances found (empty list).")
            
        print(f"\nTotal USDT Balance in Risk Manager: {bot.risk_manager.current_capital}")
        
    except Exception as e:
        print(f"Error during sync: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_wallet()
