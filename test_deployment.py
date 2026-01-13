import sys
import os
import json
import time

# Add current dir to path
sys.path.append(os.getcwd())

from api.db import init_db, get_db_connection
import api.db

# Force SQLite for local testing
api.db.DATABASE_URL = None

from api.services.wallet_service import WalletService
from api.services.exchange_service import ExchangeService

def test_deployment():
    print("--- Starting Deployment Verification ---")
    
    # 1. Init DB
    print("[1] Initializing DB...")
    init_db()
    
    username = "deploy_test_user"
    
    # Clean up prev test
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM wallets WHERE username=?", (username,))
    c.execute("DELETE FROM live_balances WHERE username=?", (username,))
    c.execute("DELETE FROM bot_settings WHERE username=?", (username,))
    conn.commit()
    conn.close()
    
    # 2. Generate Wallet
    print("[2] Generating Wallet...")
    ws = WalletService()
    res = ws.generate_wallet(username, chain='EVM')
    print(f"   EVM Wallet Result: {res}")
    print(f"   EVM Wallet: {res.get('address')}")
    if "error" in res:
        print(f"   FAILED: {res['error']}")
        return

    res_tron = ws.generate_wallet(username, chain='TRON')
    print(f"   Tron Wallet: {res_tron.get('address')}")
    
    # 3. Simulate Deposit
    print("[3] Simulating Deposit (1000 USDT)...")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO live_balances (username, currency, balance) VALUES (?, ?, ?)", (username, 'USDT', 1000.0))
    conn.commit()
    conn.close()
    
    # 4. Verify Balance via Exchange Service (Live Mode)
    print("[4] Verifying Balance via ExchangeService...")
    # Set User to Live Mode
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO bot_settings (username, mode, enabled) VALUES (?, ?, ?)", (username, 'live', 1))
    conn.commit()
    conn.close()
    
    es = ExchangeService()
    exchange = es.get_exchange_for_user(username)
    
    if not exchange:
        print("   FAILED: Could not get exchange")
        return
        
    balance = exchange.fetch_balance()
    usdt = balance['USDT']['free']
    print(f"   Balance: {usdt} USDT")
    
    if usdt != 1000.0:
        print("   FAILED: Balance mismatch")
        return

    # 5. Simulate Trade (Buy BTC)
    print("[5] Simulating Trade (Buy 0.01 BTC)...")
    try:
        # Mock price source for VirtualExchange is built-in fallback
        order = exchange.create_order('BTC/USDT', 'market', 'buy', 0.01)
        print(f"   Order: {order}")
    except Exception as e:
        print(f"   FAILED: {e}")
        return
        
    # Check Balance Deducted
    balance = exchange.fetch_balance()
    new_usdt = balance['USDT']['free']
    btc = balance['BTC']['free']
    print(f"   New Balance: {new_usdt} USDT, {btc} BTC")
    
    if new_usdt >= 1000.0 or btc != 0.01:
        print("   FAILED: Balance not updated correctly")
        return

    # 6. Withdraw
    print("[6] Testing Withdrawal...")
    w_res = ws.withdraw_crypto(username, 10.0, 'USDT', '0xExternalAddr', 'EVM')
    print(f"   Withdraw Result: {w_res}")
    
    if "error" in w_res:
        print("   FAILED")
        return
        
    print("--- Verification SUCCESS ---")

if __name__ == "__main__":
    test_deployment()
