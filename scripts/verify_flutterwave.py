import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load Env
load_dotenv()

from core.fiat.flutterwave import FlutterwaveAdapter

def verify_flutterwave_connection():
    print("--- Verifying Flutterwave Integration ---")
    
    pk = os.getenv("FLUTTERWAVE_PUBLIC_KEY")
    sk = os.getenv("FLUTTERWAVE_SECRET_KEY")
    enc = os.getenv("FLUTTERWAVE_ENCRYPTION_KEY")
    
    if not pk or not sk:
        print("❌ Error: Keys not found in environment.")
        return

    print(f"🔑 Keys Loaded: PK=...{pk[-4:]}, SK=...{sk[-4:]}, ENC=...{enc[-4:] if enc else 'None'}")
    
    adapter = FlutterwaveAdapter(pk, sk, encryption_key=enc)
    
    print("\n📡 Testing Connectivity (Fetching Banks)...")
    try:
        banks = adapter.get_banks()
        if banks:
            print(f"✅ Success! Retrieved {len(banks)} banks.")
            print(f"   Sample: {banks[0]}")
        else:
            print("⚠️  Connected, but returned 0 banks (or failed silently). Check logs.")
            
    except Exception as e:
        print(f"❌ Connection Failed: {str(e)}")

if __name__ == "__main__":
    verify_flutterwave_connection()
