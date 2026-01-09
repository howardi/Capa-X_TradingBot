
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure project root is in path
sys.path.append(os.getcwd())

from core.fiat.fiat_manager import FiatManager
from core.fiat.flutterwave import FlutterwaveAdapter
from core.storage import StorageManager

class MockBot:
    def __init__(self):
        self.storage = StorageManager()
        self.config = {}

def verify_integration():
    print("="*60)
    print("🔐 VERIFYING FLUTTERWAVE LIVE INTEGRATION")
    print("="*60)

    # 1. Check Environment Variables
    pub_key = os.environ.get("FLUTTERWAVE_PUBLIC_KEY")
    sec_key = os.environ.get("FLUTTERWAVE_SECRET_KEY")
    enc_key = os.environ.get("FLUTTERWAVE_ENCRYPTION_KEY")

    if not pub_key or not sec_key:
        print("❌ CRITICAL: Flutterwave Keys missing in environment!")
        return
    
    print(f"✅ Public Key Found: {pub_key[:8]}...{pub_key[-4:]}")
    print(f"✅ Secret Key Found: {sec_key[:8]}...{sec_key[-4:]}")
    if enc_key:
        print(f"✅ Encryption Key Found: {enc_key[:4]}...{enc_key[-4:]}")
    else:
        print("⚠️  Encryption Key Missing (Required for some endpoints)")

    # 2. Initialize Adapter
    try:
        bot = MockBot()
        fiat_mgr = FiatManager(bot)
        
        if not fiat_mgr.adapter:
            print("❌ Failed to initialize Flutterwave Adapter via FiatManager.")
            return

        print(f"✅ FiatManager Initialized with Provider: {fiat_mgr.provider}")
        print(f"✅ Adapter Mode: {'LIVE 🔴' if fiat_mgr.adapter.live_mode else 'TEST 🟡'}")

        if not fiat_mgr.adapter.live_mode:
            print("⚠️  WARNING: Adapter detected Test Mode keys. Please check your keys if you expect Live Mode.")
        
        # 3. Test API Connectivity (Get Banks)
        print("\nTesting API Connectivity (Fetching Banks)...")
        banks = fiat_mgr.adapter.get_banks()
        if banks:
            print(f"✅ Successfully fetched {len(banks)} banks from Flutterwave.")
            print(f"   Sample: {banks[0]['name']} ({banks[0]['code']})")
        else:
            print("❌ Failed to fetch banks. Check internet connection or API keys.")
            return

        # 4. Test Payment Link Generation (Real Fund Test)
        print("\nTesting Deposit Link Generation (₦500)...")
        # We use a dummy email for link generation check
        res = fiat_mgr.initiate_deposit(500.0, "integration_test@capacitybay.org")
        
        if res['status'] == 'success':
            print("✅ Successfully generated Payment Link!")
            print(f"   Ref: {res['reference']}")
            print(f"   Link: {res['authorization_url']}")
        else:
            print(f"❌ Failed to generate link: {res.get('message')}")

    except Exception as e:
        print(f"❌ Exception during verification: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("✅ INTEGRATION VERIFICATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    verify_integration()
