
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.defi import DeFiManager

def test_ton_integration():
    print("Initializing DeFiManager...")
    defi = DeFiManager()
    
    # Switch to TON
    print("\nTest 1: Connect to TON chain")
    defi.connect_to_chain('ton')
    if defi.current_chain == 'ton':
        print("PASS: Connected to TON.")
    else:
        print(f"FAIL: Expected ton, got {defi.current_chain}")
        return

    # Load TON Address (Mock)
    print("\nTest 2: Load TON Address")
    ton_addr = "EQD1pDaHs4zISB7UWOY-2S1P1pUWZV0Ztn4FJ7HY2_DL8gAC"
    loaded_addr = defi.load_private_key(ton_addr)
    print(f"Loaded: {loaded_addr}")
    if loaded_addr == ton_addr and defi.private_key == "WATCH_ONLY_OR_SEED":
        print("PASS: Loaded TON address correctly.")
    else:
        print(f"FAIL: Address mismatch or key not set. Got {loaded_addr}")

    # Check Balance
    print("\nTest 3: Check Native Balance")
    # nc can be a dummy object since we don't use it for TON in the updated method
    class DummyNC:
        w3 = None
        name = "TON"
        
    nc = DummyNC()
    bal = defi.native_balance(nc)
    print(f"Balance: {bal}")
    # TonConnectManager fallback simulates a balance between 10.5 and 5000.0
    if bal > 0:
        print(f"PASS: Got positive balance {bal}")
    else:
        print(f"FAIL: Balance is {bal}")

    # Check Transfer
    print("\nTest 4: Transfer Native")
    res = defi.transfer_native(nc, "EQRecipient...", 1.0)
    print(f"Transfer Result: {res}")
    if "✅" in res:
        print("PASS: Transfer simulation successful.")
    else:
        print(f"FAIL: Transfer failed: {res}")

if __name__ == "__main__":
    test_ton_integration()
