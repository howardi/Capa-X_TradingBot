import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8080"

def test_health():
    try:
        res = requests.get(f"{BASE_URL}/health")
        if res.status_code == 200:
            print("✅ Health Check Passed")
            return True
        else:
            print(f"❌ Health Check Failed: {res.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        return False

def test_deposit():
    try:
        payload = {
            "amount": 5000,
            "email": "test@caparox.com",
            "username": "test_user"
        }
        res = requests.post(f"{BASE_URL}/api/flutterwave/pay", json=payload)
        data = res.json()
        if res.status_code == 200 and data.get('status') == 'success':
            print("✅ Deposit Init Passed (Flutterwave)")
            return True
        else:
            print(f"❌ Deposit Init Failed: {data}")
            return False
    except Exception as e:
        print(f"❌ Deposit Test Error: {e}")
        return False

def test_bot_toggle():
    try:
        payload = {"username": "test_user", "enabled": True}
        res = requests.post(f"{BASE_URL}/api/bot/toggle", json=payload)
        data = res.json()
        if res.status_code == 200 and data.get('status') == 'success':
             print("✅ Bot Toggle Passed")
             return True
        else:
             print(f"❌ Bot Toggle Failed: {data}")
             return False
    except Exception as e:
        print(f"❌ Bot Toggle Error: {e}")
        return False

def test_copy_trade():
    try:
        res = requests.get(f"{BASE_URL}/api/copy-trade/traders")
        data = res.json()
        if res.status_code == 200 and isinstance(data, list) and len(data) > 0:
            print("✅ Copy Trade Traders List Passed")
            return True
        else:
            print(f"❌ Copy Trade Failed: {data}")
            return False
    except Exception as e:
        print(f"❌ Copy Trade Error: {e}")
        return False

def test_arbitrage():
    try:
        res = requests.get(f"{BASE_URL}/api/web3/arbitrage?symbol=ETH")
        data = res.json()
        if res.status_code == 200 and 'cex_price' in data:
            print("✅ Arbitrage Scanner Passed")
            return True
        else:
            print(f"❌ Arbitrage Failed: {data}")
            return False
    except Exception as e:
        print(f"❌ Arbitrage Error: {e}")
        return False

if __name__ == "__main__":
    print("⏳ Waiting for server to start...")
    time.sleep(5) # Give it a moment
    
    checks = [
        test_health(),
        test_deposit(),
        test_bot_toggle(),
        test_copy_trade(),
        test_arbitrage()
    ]
    
    if all(checks):
        print("\n🎉 ALL TESTS PASSED! Backend is ready.")
        sys.exit(0)
    else:
        print("\n⚠️ SOME TESTS FAILED.")
        sys.exit(1)
