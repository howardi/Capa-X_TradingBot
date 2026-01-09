import requests
import json

address = "UQD1pDaHs4zISB7UWOY-2S1P1pUWZV0Ztn4FJ7HY2_DL8gAC"

def check_address(addr, network="Mainnet"):
    print(f"--- Checking {network} for {addr} ---")
    
    # Base URL
    base_url = "https://tonapi.io/v2" if network == "Mainnet" else "https://testnet.tonapi.io/v2"
    
    # 1. Native Balance
    try:
        url = f"{base_url}/accounts/{addr}"
        print(f"Fetching: {url}")
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            balance = int(data.get('balance', 0)) / 1e9
            status = data.get('status')
            print(f"Native Balance: {balance} TON")
            print(f"Account Status: {status}")
        else:
            print(f"Error fetching native: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Exception native: {e}")

    # 2. Jetton Balances (USDT, etc.)
    try:
        url = f"{base_url}/accounts/{addr}/jettons"
        print(f"Fetching: {url}")
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            balances = data.get('balances', [])
            print(f"Found {len(balances)} Jettons")
            for b in balances:
                amt = float(b.get('balance', 0))
                decimals = int(b.get('jetton', {}).get('decimals', 9))
                symbol = b.get('jetton', {}).get('symbol', '?')
                name = b.get('jetton', {}).get('name', '?')
                readable = amt / (10**decimals)
                print(f" - {symbol} ({name}): {readable}")
        else:
            print(f"Error fetching jettons: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Exception jettons: {e}")

if __name__ == "__main__":
    # check_address(address, "Mainnet")
    # print("\n" + "="*30 + "\n")
    check_address(address, "Testnet") # Optional, but good to verify
