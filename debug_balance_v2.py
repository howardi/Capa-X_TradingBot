
import os
import time
from dotenv import load_dotenv
from core.bot import TradingBot

# Load env vars
load_dotenv()

def debug_balance():
    print("--- Debugging Balance Fetching ---", flush=True)
    
    # Initialize Bot with Bybit
    try:
        bot = TradingBot('bybit')
        
        # Load keys from env
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_SECRET')
        
        if not api_key or not api_secret:
            print("Error: BYBIT_API_KEY or BYBIT_SECRET not found in .env", flush=True)
            return
            
        print(f"API Key found: {api_key[:5]}...", flush=True)
        
        # Update credentials
        bot.data_manager.update_credentials(api_key, api_secret)
        
        # Switch to Live Mode
        bot.set_trading_mode('CEX_Direct')
        
        # Sync Balance
        print("\nCalling sync_live_balance()...", flush=True)
        # Debug: Print raw balance
        raw_balance = bot.data_manager.get_balance()
        print(f"Raw Balance Keys: {list(raw_balance.keys())}", flush=True)
        if 'info' in raw_balance:
            print(f"Raw Info: {raw_balance['info']}", flush=True)
        if 'USDT' in raw_balance:
            print(f"USDT Balance: {raw_balance['USDT']}", flush=True)
            
        bot.sync_live_balance()
        
        print(f"\nFinal Risk Manager Capital: {bot.risk_manager.current_capital}", flush=True)
        
    except Exception as e:
        print(f"Crash: {e}", flush=True)

if __name__ == "__main__":
    debug_balance()
