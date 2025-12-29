import os
import shutil
import json
from core.auth import AuthManager, UserManager

def test_pnl_tracking():
    print("--- Starting PnL Tracking Verification ---")
    
    # 1. Setup Test User
    test_user = "pnl_tester"
    auth = AuthManager()
    
    # Clean up previous test
    user_dir = os.path.join("data/users", test_user)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
        # Remove from users_db
        if test_user in auth.users:
            del auth.users[test_user]
            auth._save_users()
            
    auth.register_user(test_user, "password123", "test@example.com")
    user_mgr = UserManager(test_user)
    
    print(f"User {test_user} created.")
    
    # 2. Execute Buy
    # Buy 1 BTC at $50,000
    symbol = "BTC/USDT"
    buy_price = 50000.0
    amount = 1.0
    
    print(f"Executing Buy: {amount} {symbol} @ ${buy_price}")
    user_mgr.execute_trade(symbol, "buy", amount, buy_price)
    
    # Verify Position
    positions = user_mgr.get_positions()
    assert symbol in positions
    assert positions[symbol]['amount'] == 1.0
    assert positions[symbol]['entry_price'] == 50000.0
    print("Buy Position Verified.")
    
    # 3. Execute Sell (Profit)
    # Sell 0.5 BTC at $55,000 (10% Profit)
    sell_price = 55000.0
    sell_amount = 0.5
    
    print(f"Executing Sell: {sell_amount} {symbol} @ ${sell_price}")
    trade_record = user_mgr.execute_trade(symbol, "sell", sell_amount, sell_price)
    
    # Verify PnL
    # PnL = (55000 - 50000) * 0.5 = 2500
    expected_pnl = 2500.0
    print(f"Trade PnL: {trade_record['pnl']}")
    
    assert trade_record['pnl'] == expected_pnl
    print("PnL Calculation Verified.")
    
    # Verify Remaining Position
    positions = user_mgr.get_positions()
    assert positions[symbol]['amount'] == 0.5
    assert positions[symbol]['realized_pnl'] == 2500.0
    print("Remaining Position Verified.")
    
    # 4. Check Metrics
    metrics = user_mgr.get_performance_metrics()
    print("Performance Metrics:", metrics)
    assert metrics['total_pnl'] == 2500.0
    assert metrics['win_rate'] == 100.0
    assert metrics['total_trades'] == 1
    
    print("--- PnL Verification Successful ---")

if __name__ == "__main__":
    try:
        test_pnl_tracking()
    except Exception as e:
        print(f"FAILED: {e}")
