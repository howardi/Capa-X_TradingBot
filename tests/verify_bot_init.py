
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from core.bot import TradingBot
    print("Initializing TradingBot...")
    bot = TradingBot()
    print("TradingBot initialized successfully.")
    print(f"Bot Symbol: {bot.symbol}")
    print(f"AutoTrader Symbols: {bot.auto_trader.symbols}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
