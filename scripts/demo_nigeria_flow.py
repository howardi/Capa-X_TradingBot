import time
import os
import sys
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Ensure project root is in path
sys.path.append(os.getcwd())

from core.fiat.fiat_manager import FiatManager
from core.storage import StorageManager

class RealBot:
    def __init__(self):
        self.storage = StorageManager()
        self.config = {'fiat_provider': 'flutterwave'}
        self.auth_manager = None 

def run_demo():
    print("="*60)
    print("🚀 NIGERIAN FIAT-CRYPTO LIVE FLOW (FLUTTERWAVE ONLY)")
    print("="*60)
    
    # 1. Initialize System
    print("\n[1] Initializing System...")
    bot = RealBot()
    fiat_mgr = FiatManager(bot)
    
    if not fiat_mgr.adapter:
        print("❌ Error: Flutterwave Adapter not initialized. Check API Keys.")
        return

    print(f"ℹ️  Active Provider: {fiat_mgr.provider.upper()}")
    print(f"ℹ️  Live Mode: {fiat_mgr.adapter.live_mode}")
    
    # 2. Deposit Flow
    print("\n[2] Initiating NGN Deposit (Real Funds)...")
    user_email = "wakcl@example.com" # User's email
    amount = 1000.0 # Small test amount
    
    # Initiate
    print(f"    -> Requesting deposit of ₦{amount:,.2f}")
    dep_res = fiat_mgr.initiate_deposit(amount, user_email)
    
    if dep_res['status'] == 'success':
        ref = dep_res['reference']
        print(f"    ✅ Deposit Initiated! Ref: {ref}")
        print(f"    🔗 PAY HERE: {dep_res.get('authorization_url')}")
        print("\n    ⚠️  ACTION REQUIRED: Open the link above and complete payment.")
        print("    ... Waiting 30s for user to pay (Ctrl+C to skip) ...")
        
        try:
            # Poll for status a few times
            for i in range(6):
                time.sleep(5)
                print(f"    Checking status... ({i+1}/6)")
                verify_res = fiat_mgr.verify_deposit(ref)
                if verify_res['status'] == 'success':
                    print(f"    ✅ Payment Confirmed! New Balance: ₦{verify_res['new_balance']:,.2f}")
                    break
                elif verify_res['status'] == 'error':
                    # verification might fail if transaction not found yet
                    pass
        except KeyboardInterrupt:
            print("    Skipping wait...")
            
    else:
        print(f"    ❌ Deposit Failed: {dep_res}")
        return

    # 3. Swap Flow (NGN -> USDT)
    print("\n[3] Testing Swap Quote (NGN -> USDT)...")
    swap_amount = 1000.0
    
    # Get Quote
    quote = fiat_mgr.swap_manager.get_quote("NGN", "USDT", swap_amount)
    if quote['status'] == 'success':
        print(f"    ℹ️  Quote: {quote['amount_out_net']:.2f} USDT @ {quote['rate']:.2f}")
    else:
        print(f"    ❌ Quote Failed: {quote}")

    print("\n" + "="*60)
    print("✅ LIVE FLOW CHECK COMPLETE")
    print("="*60)

if __name__ == "__main__":
    run_demo()
