import requests
import time
import uuid
import sys

BASE_URL = "http://127.0.0.1:8080"

def test_health():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Health Check: {r.status_code} - {r.json()}")
        return True
    except Exception as e:
        print(f"Health Check Failed: {e}")
        return False

def test_register():
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    password = "password123"
    try:
        r = requests.post(f"{BASE_URL}/api/register", json={"username": username, "password": password}, timeout=5)
        print(f"Register: {r.status_code} - {r.json()}")
        return username
    except Exception as e:
        print(f"Register Failed: {e}")
        return None

def test_deposit_init(username):
    try:
        r = requests.post(f"{BASE_URL}/api/deposit/paystack", json={"username": username, "amount": 5000}, timeout=5)
        print(f"Deposit Init (Paystack): {r.status_code} - {r.json()}")
        return r.json().get('tx_ref')
    except Exception as e:
        print(f"Deposit Init Failed: {e}")
        return None

def test_deposit_verify(username, tx_ref):
    try:
        # Mock verify for Paystack (simulated in service)
        r = requests.post(f"{BASE_URL}/api/deposit/verify", json={"username": username, "tx_ref": tx_ref, "provider": "paystack"}, timeout=5)
        print(f"Deposit Verify: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"Deposit Verify Failed: {e}")

def test_withdraw(username):
    try:
        # Test generic withdraw
        r = requests.post(f"{BASE_URL}/api/withdraw", json={
            "username": username, 
            "amount": 100, 
            "provider": "flutterwave", 
            "account_bank": "044", 
            "account_number": "0690000000"
        }, timeout=5)
        print(f"Withdraw: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"Withdraw Failed: {e}")

def test_bot_status(username):
    try:
        r = requests.get(f"{BASE_URL}/api/bot/status?username={username}", timeout=5)
        print(f"Bot Status: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"Bot Status Failed: {e}")

if __name__ == "__main__":
    print("Waiting for server to start...")
    time.sleep(5)
    print("Running Tests...")
    if test_health():
        user = test_register()
        if user:
            tx_ref = test_deposit_init(user)
            if tx_ref:
                test_deposit_verify(user, tx_ref)
            test_withdraw(user)
            test_bot_status(user)
    else:
        print("Server not reachable.")
