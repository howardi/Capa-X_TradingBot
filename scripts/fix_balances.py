import sqlite3
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.auth import AuthManager

DB_PATH = "trading_bot.db"
USERS_DB_PATH = "data/users/users_db.json"

def fix_balances():
    print("Starting Balance Fix...")
    
    # 1. Update SQLite Settings (NGN and USDT Credit)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current values
    cursor.execute("SELECT value FROM settings WHERE key='fiat_balance_ngn'")
    res = cursor.fetchone()
    current_ngn = float(res[0]) if res else 0.0
    print(f"Current NGN Balance: {current_ngn}")
    
    cursor.execute("SELECT value FROM settings WHERE key='virtual_usdt_credit_usd'")
    res = cursor.fetchone()
    current_usdt = float(res[0]) if res else 0.0
    print(f"Current USDT Credit: {current_usdt}")
    
    # Update if needed (Force overwrite as per user request to restore "previous" balance)
    new_ngn = 400.0
    new_usdt = 0.99
    
    # Only update if current is 0 or user specifically requested restore (which they did)
    # But let's be safe: if current is HIGHER, keep it? 
    # The user said "not showing", implying they see 0 or less than expected.
    # I'll force set it to what they asked, or add to it if it's non-zero but small?
    # User said "previous live deposited balance of 400... was not showing".
    # I will set it to MAX(current, 400) to be safe, but likely it is 0.
    
    final_ngn = max(current_ngn, new_ngn)
    final_usdt = max(current_usdt, new_usdt)
    
    cursor.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", 
                   ("fiat_balance_ngn", str(final_ngn)))
    
    cursor.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", 
                   ("virtual_usdt_credit_usd", str(final_usdt)))
                   
    conn.commit()
    conn.close()
    
    print(f"✅ Updated NGN Balance to: {final_ngn}")
    print(f"✅ Updated USDT Credit to: {final_usdt}")
    
    # 2. Update Flutterwave Keys in Users DB
    # Public key FLWPUBK-aded1251ab1fccfd69b058608f38f7a8-X 
    # Secret key FLWSECK-2d9e29e2c7e85214e55fa642cff59b99-19b9abc3310vt-X 
    # Encryption key 2d9e29e2c7e8eaa49db18d1b
    
    auth = AuthManager()
    username = "howardino"
    
    # Verify user exists
    if username not in auth.users:
        print(f"❌ User {username} not found. Cannot save keys.")
    else:
        # Save keys
        # We need to construct the keys dict/tuple expected by AuthManager
        # AuthManager.save_api_keys takes (username, exchange, api_key, api_secret)
        # But for Flutterwave, it might be different.
        # FiatManager loads keys via: auth_manager.get_api_keys(username, 'flutterwave')
        # returning (api_key, api_secret) or dict.
        
        # Let's see how save_api_keys stores it.
        # It usually stores as a dict in users[username]['api_keys'][exchange]
        
        keys = {
            "api_key": "FLWPUBK-aded1251ab1fccfd69b058608f38f7a8-X",
            "api_secret": "FLWSECK-2d9e29e2c7e85214e55fa642cff59b99-19b9abc3310vt-X",
            "encryption_key": "2d9e29e2c7e8eaa49db18d1b"
        }
        
        # We can manually update the user dict and save, since AuthManager might not have a dedicated method for 3-part keys (enc key)
        # or we can use save_api_keys for the first two and then manually add the third.
        
        # Let's just update the user dict directly to be sure.
        if 'api_keys' not in auth.users[username]:
            auth.users[username]['api_keys'] = {}
            
        auth.users[username]['api_keys']['flutterwave'] = keys
        auth._save_users()
        print(f"✅ Flutterwave keys saved for user {username}")

if __name__ == "__main__":
    fix_balances()
