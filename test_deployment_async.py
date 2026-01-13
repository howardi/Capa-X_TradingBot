import asyncio
from api.db import init_db, get_db_connection
import api.db
# Force SQLite
api.db.DATABASE_URL = None

from api.services.wallet_service import WalletService
from api.services.exchange_service import ExchangeService
from api.bot import BotEngine

async def test_deployment_async():
    print("--- Starting Deployment Verification (Async) ---")
    
    # Force clean DB
    import os
    if os.path.exists("users.db"):
        os.remove("users.db")

    # 1. Init DB
    init_db()
    
    username = "deploy_test_user_async"
    # Clean up
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM wallets WHERE username=?", (username,))
    c.execute("DELETE FROM live_balances WHERE username=?", (username,))
    c.execute("DELETE FROM bot_settings WHERE username=?", (username,))
    c.execute("DELETE FROM bot_activity WHERE username=?", (username,))
    c.execute("DELETE FROM risk_daily_stats WHERE username=?", (username,))
    conn.commit()
    conn.close()

    # 2. Wallet
    ws = WalletService()
    res = ws.generate_wallet(username, chain='EVM')
    print(f"Wallet: {res}")
    
    # 3. Deposit
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO live_balances (username, currency, balance) VALUES (?, ?, ?)", (username, 'USDT', 1000.0))
    # Enable Bot
    c.execute("INSERT INTO bot_settings (username, mode, enabled, symbol, strategy, investment_amount, risk_level) VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (username, 'live', 1, 'BTC/USDT', 'advanced_ai', 100.0, 'medium'))
    conn.commit()
    conn.close()
    
    # 4. Run Bot Tick
    print("Running Bot Tick...")
    bot = BotEngine()
    try:
        results = await bot.run_tick()
        print(f"Bot Results: {results}")
    finally:
        await bot.close()
    
    # 5. Verify Trade
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bot_activity WHERE username=?", (username,))
    trades = c.fetchall()
    conn.close()
    
    print(f"Trades found: {len(trades)}")
    if trades:
        print(f"Trade: {dict(trades[0])}")
        
        # Verify Risk Stats
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM risk_daily_stats WHERE username=?", (username,))
        stats = c.fetchone()
        conn.close()
        print(f"Risk Stats: {dict(stats) if stats else 'None'}")
        
    else:
        print("No trades executed (might be due to strategy signal or risk check)")
        
    print("--- Verification Finished ---")

if __name__ == "__main__":
    asyncio.run(test_deployment_async())
