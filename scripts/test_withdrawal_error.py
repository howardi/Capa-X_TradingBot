
import os
import sys
import json
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.getcwd())

from core.fiat.fiat_manager import FiatManager
from core.fiat.flutterwave import FlutterwaveAdapter
from core.storage import StorageManager
from core.auth import AuthManager

class MockBot:
    def __init__(self):
        self.storage = StorageManager()
        self.auth_manager = AuthManager()
        self.config = {}

def test_withdrawal_flow():
    print("="*60)
    print("🧪 DIAGNOSING WITHDRAWAL ERROR")
    print("="*60)

    bot = MockBot()
    fiat_mgr = FiatManager(bot)
    
    # Simulate loading keys for a user (we need to know the username the user saved keys with)
    # Since we don't know the username, we'll try to load from environment or just check if adapter is initialized
    # If the user saved keys in the dashboard, they are in users_db.json.
    # Let's try to find a user with flutterwave keys.
    
    username = None
    if bot.auth_manager.users:
        for u, data in bot.auth_manager.users.items():
            if 'api_keys' in data and 'flutterwave' in data['api_keys']:
                username = u
                print(f"✅ Found user with Flutterwave keys: {username}")
                break
    
    if username:
        print(f"DEBUG: Attempting to load keys for {username}...")
        keys = bot.auth_manager.get_api_keys(username, "flutterwave")
        print(f"DEBUG: Keys returned: {keys}")
        fiat_mgr.initialize_adapter(username)
    else:
        print("⚠️ No user with Flutterwave keys found. Using Environment Variables.")
        # initialize_adapter will use env vars if no username passed or keys not found
        fiat_mgr.initialize_adapter()

    if not fiat_mgr.adapter:
        print("❌ Adapter failed to initialize.")
        return

    print(f"✅ Adapter Initialized. Mode: {'LIVE' if fiat_mgr.adapter.live_mode else 'TEST'}")

    # 1. Test Account Resolution
    print("\n1️⃣ Testing Account Resolution...")
    bank_code = "100004" # Opay
    account_number = "7032888783"
    
    res = fiat_mgr.resolve_account(account_number, bank_code)
    print(f"   Result: {res}")
    
    if res.get('status') == 'error':
        print(f"❌ Account Resolution Failed: {res.get('message')}")
        if "IP Whitelisting" in res.get('message', ''):
            print("   >>> CONFIRMED: IP Whitelisting is blocking Account Resolution.")
    else:
        print(f"✅ Account Resolved: {res.get('account_name')}")

    print("\n3️⃣ Testing Bank List Fetching...")
    banks = fiat_mgr.get_banks()
    if banks:
        print(f"✅ Successfully fetched {len(banks)} banks.")
        # Check for Opay
        opay = next((b for b in banks if 'opay' in b['name'].lower() or 'paycom' in b['name'].lower()), None)
        if opay:
            print(f"✅ Found Opay: {opay}")
        else:
            print("⚠️ Opay not found in bank list.")
    else:
        print("❌ Failed to fetch banks.")

    print("\n4️⃣ Checking Real Account Balances...")
    balances = fiat_mgr.get_balances()
    print(f"   Balances: {balances}")

    # 5. Test Transfer Initiation (Dry Run / Expect Error)
    # We won't actually succeed if funds are 0, but we want to see the error message.
    print("\n5️⃣ Testing Transfer Initiation (Amount: 100)...")
    
    # Use Manager instead of Adapter to test the new Balance Check Logic
    # Use Opay code if found, else default
    opay_code = opay['code'] if 'opay' in locals() and opay else "000019"
    print(f"   Using Bank Code: {opay_code}")
    res = fiat_mgr.initiate_withdrawal(100, opay_code, "7032888783", account_name="WAKAMA HOWARD")
    print(f"   Result: {res}")

if __name__ == "__main__":
    test_withdrawal_flow()
