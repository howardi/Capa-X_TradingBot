
import sys
import os
import pandas as pd
import time

# Add root to path
sys.path.append(os.getcwd())

from core.bot import TradingBot
from core.execution import ExecutionEngine
from core.brain import CapacityBayBrain
from core.web3_wallet import Web3Wallet

def test_integration():
    print("Initializing TradingBot...")
    bot = TradingBot()
    
    print("Testing Bot Properties...")
    print(f"Trading Mode: {bot.trading_mode}")
    bot.trading_mode = 'Live'
    print(f"Open Positions (Live): {bot.open_positions}")
    
    # Test Web3 Injection
    print("Testing Web3 Wallet Integration...")
    bot.web3_wallet = Web3Wallet()
    bot.web3_wallet.chain_id = '1'
    # Mock connection
    bot.web3_wallet.connected = True
    bot.web3_wallet.address = "0x123...Mock"
    
    print("Testing Sync Balance...")
    try:
        # Mock get_balance to avoid network call failure
        bot.web3_wallet.get_balance = lambda: 1.5
        bot.sync_live_balance()
        print(f"Wallet Balances: {bot.wallet_balances}")
    except Exception as e:
        print(f"Sync Balance Failed: {e}")

    print("Testing Execution Engine...")
    try:
        bot.execution.execute_robust('ETH/USDT', 'buy', 0.1, strategy='manual_close')
        print("Manual Close Execution: OK")
    except Exception as e:
        print(f"Execution Failed: {e}")
        
    try:
        bot.execution.close_all()
        print("Close All: OK")
    except Exception as e:
        print(f"Close All Failed: {e}")

    print("Testing AI Brain...")
    try:
        brain = bot.brain
        df = pd.DataFrame({
            'open': [100]*20, 'high': [105]*20, 'low': [95]*20, 'close': [102]*20, 'volume': [1000]*20
        })
        res = brain.analyze_market(df)
        print(f"AI Analysis Result: {res.keys()}")
    except Exception as e:
        print(f"AI Analysis Failed: {e}")

    print("Integration Test Complete.")

if __name__ == "__main__":
    test_integration()
