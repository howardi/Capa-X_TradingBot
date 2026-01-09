import os
import sys
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.storage import StorageManager

def reset_balance():
    print("🧹 Cleaning up Mock/Fake Balances...")
    
    # Initialize Storage
    storage = StorageManager()
    
    # 1. Reset NGN Balance
    old_bal = storage.get_setting("fiat_balance_ngn", 0.0)
    print(f"   Found existing NGN Balance: ₦{old_bal:,.2f}")
    
    storage.save_setting("fiat_balance_ngn", 0.0)
    print("   ✅ Reset NGN Balance to ₦0.00")
    
    # 2. Reset Transaction History (Clear Mock Transactions)
    try:
        storage.cursor.execute("DELETE FROM fiat_transactions")
        storage.conn.commit()
        print("   ✅ Cleared Fiat Transaction History (Removed Mocks)")
    except Exception as e:
        print(f"   ⚠️ Failed to clear transaction history: {e}")
    
    # 3. Verify
    new_bal = storage.get_setting("fiat_balance_ngn", -1.0)
    if new_bal == 0.0:
        print("   ✅ Verification Successful: Balance is now 0.00")
    else:
        print(f"   ❌ Verification Failed: Balance is {new_bal}")

if __name__ == "__main__":
    reset_balance()
