import requests
import time
import uuid
import sys

# LIVE URL
BASE_URL = "https://caparox-bot-971646936342.us-central1.run.app"

def test_health():
    print(f"Testing Health at {BASE_URL}/health...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Health Check: {r.status_code} - {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"Health Check Failed: {e}")
        return False

def test_register():
    username = f"live_test_{uuid.uuid4().hex[:6]}"
    password = "password123"
    print(f"Testing Register for {username}...")
    try:
        r = requests.post(f"{BASE_URL}/api/register", json={"username": username, "password": password}, timeout=10)
        print(f"Register: {r.status_code} - {r.text}")
        if r.status_code == 201 or r.status_code == 200:
            return username
        return None
    except Exception as e:
        print(f"Register Failed: {e}")
        return None

def test_bot_status(username):
    print(f"Testing Bot Status for {username}...")
    try:
        r = requests.get(f"{BASE_URL}/api/bot/status?username={username}", timeout=10)
        print(f"Bot Status: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Bot Status Failed: {e}")

def test_deposit_demo(username):
    print(f"Testing Deposit Demo for {username}...")
    try:
        # Using the unified deposit endpoint or provider specific
        # Based on index.py, we have /api/deposit/paystack, /api/deposit/flutterwave
        # And the demo one /api/deposit (which was renamed to api_deposit_demo)
        
        # Let's try the generic demo one if available, or paystack
        r = requests.post(f"{BASE_URL}/api/deposit", json={"amount": 1000, "currency": "NGN"}, timeout=10)
        print(f"Deposit Demo: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Deposit Demo Failed: {e}")

def test_deposit_flutterwave(username):
    print(f"Testing Deposit Flutterwave for {username}...")
    try:
        # Based on index.py route: @app.route('/api/deposit/flutterwave', methods=['POST'])
        r = requests.post(f"{BASE_URL}/api/deposit/flutterwave", json={"username": username, "amount": 2000, "currency": "NGN", "email": "test@example.com"}, timeout=10)
        print(f"Deposit Flutterwave: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Deposit Flutterwave Failed: {e}")

if __name__ == "__main__":
    print("Running Live Deployment Tests...")
    if test_health():
        user = test_register()
        if user:
            test_bot_status(user)
            test_deposit_demo(user)
            test_deposit_flutterwave(user)
    else:
        print("Skipping other tests as Health Check failed.")
