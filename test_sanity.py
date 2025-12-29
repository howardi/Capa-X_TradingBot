
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import TradingBot...")
    from core.bot import TradingBot
    print("Import successful.")
    
    print("Initializing TradingBot...")
    bot = TradingBot()
    print("TradingBot initialized successfully.")
    
    print("Checking strategies...")
    for name, strategy in bot.strategies.items():
        print(f" - {name}: OK")
        
    print("Sanity check passed!")
except Exception as e:
    print(f"Sanity check FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
