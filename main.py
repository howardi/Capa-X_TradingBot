import time
import os
import sys
from dotenv import load_dotenv
from core.bot import TradingBot
from config.settings import DEFAULT_SYMBOL

# Load env vars
load_dotenv()

def main():
    print("==========================================")
    print("   Capa-X Trading Bot | Autonomous Core   ")
    print("==========================================")
    
    # 1. Select Mode
    mode = os.getenv('TRADING_MODE', 'Demo')
    print(f"[*] Initializing in {mode} Mode...")
    
    # 2. Initialize Bot
    # You can specify 'binance' or 'bybit' here
    bot = TradingBot(exchange_id=os.getenv('DEFAULT_EXCHANGE', 'bybit'))
    
    # 3. Configure Mode
    bot.set_trading_mode(mode)
    
    # 4. Connect to API (if applicable)
    if mode in ['CEX_Direct', 'CEX_Proxy']:
        print("[*] Verifying Exchange Credentials...")
        # Note: DataManager loads keys from config/settings.py which now reads .env
        try:
            bot.data_manager.exchange.check_required_credentials()
            print("[+] Credentials Verified.")
        except Exception as e:
            print(f"[-] Credential Warning: {e}")
            print("    Ensure BINANCE_API_KEY / BYBIT_API_KEY are set in .env")
            
    elif mode == 'DEX':
        print("[*] Connecting to Web3...")
        # DEX Manager initialization check
        if not os.getenv('PRIVATE_KEY'):
            print("[-] Warning: No Private Key found in .env for DEX mode.")

    # 5. Start Loop
    print(f"[*] Starting Trading Loop on {DEFAULT_SYMBOL}...")
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n[!] Stop signal received. Shutting down...")
    except Exception as e:
        print(f"\n[!] Critical Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
