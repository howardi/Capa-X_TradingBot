import requests
import time

BASE_URL = "https://caparox-bot-971646936342.us-central1.run.app"

def check_endpoint(endpoint):
    url = f"{BASE_URL}{endpoint}"
    print(f"Checking {url}...")
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {str(response.json())[:200]}...")
            return True
        else:
            print(f"Error: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def verify():
    print("Verifying deployment...")
    
    # 1. Health check
    if not check_endpoint("/health"):
        print("Health check failed!")
        
    # 2. Version
    check_endpoint("/api/version")
    
    # 3. CoinCodex
    check_endpoint("/api/coincodex/coin/BTC")
    
    # 4. Bot Logic (Integration disabled if no API keys or local run, but endpoint should exist)
    check_endpoint("/api/bot/logic")

if __name__ == "__main__":
    verify()
