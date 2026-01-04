
import ccxt
import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Import DataManager to verify the actual fix in codebase
try:
    from core.data import DataManager
    USE_DATAMANAGER = True
except ImportError:
    print("[WARN] Could not import DataManager. Falling back to direct CCXT.")
    USE_DATAMANAGER = False

def diagnose():
    print("--- Binance Diagnostic ---")
    
    api_key = os.getenv('BINANCE_API_KEY')
    secret = os.getenv('BINANCE_SECRET')
    
    if not api_key or not secret:
        print("[FAIL] Missing API Credentials in .env")
        return

    print(f"API Key: {api_key[:4]}...{api_key[-4:]}")
    
    if USE_DATAMANAGER:
        print("\n[Step 0] Initializing DataManager (Testing Core Fix)...")
        try:
            dm = DataManager('binance')
            exchange = dm.exchange
            print("[PASS] DataManager initialized.")
        except Exception as e:
            print(f"[FAIL] DataManager init failed: {e}")
            return
    else:
        print("\n[Step 0] Initializing CCXT Direct...")
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'options': {'defaultType': 'spot'}
        })
    
    # 1. Test Time Sync
    print("\n[Step 1] Checking Time Drift...")
    try:
        local_time = int(time.time() * 1000)
        server_time = exchange.fetch_time()
        drift = local_time - server_time
        
        print(f"Local Time:  {local_time}")
        print(f"Server Time: {server_time}")
        print(f"Drift:       {drift} ms")
        
        if drift > 1000:
            print("[WARN] Local time is significantly AHEAD of server.")
        elif drift < -1000:
            print("[WARN] Local time is significantly BEHIND server.")
        else:
            print("[PASS] Time drift is within acceptable range.")
        
    except Exception as e:
        import traceback
        print(f"[FAIL] Failed to fetch server time: {e}")
        traceback.print_exc()
        return

    # 2. Test Private Request
    print("\n[Step 2] Testing Private Request (Fetch Balance)...")
    try:
        # If using DataManager, the fix should already be applied automatically.
        # We don't need manual patching here unless we are testing direct CCXT (fallback).
        
        if not USE_DATAMANAGER and abs(drift) > 500:
             print("Applying manual patch for direct CCXT test...")
             safe_offset = drift + 2000
             original_milliseconds = exchange.milliseconds
             exchange.milliseconds = lambda: original_milliseconds() - safe_offset

        print("Calling fetch_balance...", flush=True)
        balance = exchange.fetch_balance()
        print("[PASS] Balance fetch successful!", flush=True)
        
        if 'total' in balance:
             print(f"Assets found: {list(balance['total'].keys())[:5]}...")
        
    except ccxt.InvalidNonce as e:
        print(f"[FAIL] Invalid Nonce (Time Issue): {e}")
    except ccxt.AuthenticationError as e:
        print(f"[FAIL] Authentication Error (Check Permissions/IP): {e}")
    except Exception as e:
        print(f"[FAIL] Request Failed: {e}")

if __name__ == "__main__":
    diagnose()
