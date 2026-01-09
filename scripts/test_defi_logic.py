
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.defi import DeFiManager
import core.defi
print(f"DEBUG: core.defi file: {core.defi.__file__}")

def test_defi_logic_update():
    print("Initializing DeFiManager...")
    defi = DeFiManager()
    
    # Test 1: get_deposit_address returns error message when no wallet loaded
    print("\nTest 1: Check Error Message on empty wallet")
    res = defi.get_deposit_address()
    if "⚠️" in res:
        print(f"PASS: Caught expected error message: {res}")
    else:
        print(f"FAIL: Should have returned error message, got: {res}")

    # Test 2: load_private_key validation (Invalid format)
    print("\nTest 2: Check Invalid Key Validation")
    try:
        defi.load_private_key("invalid_key")
        print("FAIL: Should have raised ValueError for invalid key")
    except ValueError as e:
        print(f"PASS: Caught expected ValueError: {e}")

    # Test 3: load_private_key success (Valid mock key)
    # Generate a real valid key using eth_account for testing
    from eth_account import Account
    acct = Account.create()
    valid_key = acct.key.hex()
    if not valid_key.startswith("0x"):
        valid_key = "0x" + valid_key
    
    print(f"\nTest 3: Load Valid Key: {valid_key}")
    try:
        addr = defi.load_private_key(valid_key)
        print(f"Loaded Address: {addr}")
        
        if addr == acct.address:
            print("PASS: Address matches expected.")
        else:
            print(f"FAIL: Address mismatch. Expected {acct.address}, got {addr}")
            
        # Verify internal state
        expected_key = valid_key if valid_key.startswith("0x") else "0x" + valid_key
        if defi.private_key == expected_key and defi.address == acct.address:
             print("PASS: Internal state updated correctly.")
        else:
             print(f"FAIL: Internal state mismatch. Expected {expected_key}, Got {defi.private_key}")
             
    except Exception as e:
        print(f"FAIL: Exception loading valid key: {e}")

    # Test 4: get_deposit_address success after load
    print("\nTest 4: Get Deposit Address after load")
    try:
        d_addr = defi.get_deposit_address()
        if d_addr == acct.address:
             print("PASS: Correct deposit address returned.")
        else:
             print(f"FAIL: Wrong deposit address. Got {d_addr}")
    except Exception as e:
        print(f"FAIL: Exception getting deposit address: {e}")

    # Test 5: transfer_assets (Mock Web3)
    print("\nTest 5: Transfer Assets (Mock Web3)")
    mock_w3 = MagicMock()
    # Setup mocks
    mock_w3.to_checksum_address.side_effect = lambda x: x
    mock_w3.to_wei.return_value = 1000000000000000000
    mock_w3.eth.get_transaction_count.return_value = 0
    mock_w3.eth.gas_price = 20000000000
    mock_w3.eth.account.sign_transaction.return_value = MagicMock(rawTransaction=b'signed_tx')
    mock_w3.eth.send_raw_transaction.return_value = b'\x00' * 32
    mock_w3.to_hex.return_value = "0x" + "00"*32

    try:
        res = defi.transfer_assets("0xRecipient", 1.0, mock_w3)
        print(f"Transfer Result: {res}")
        if "✅" in res:
            print("PASS: Transfer returned success message.")
        else:
            print(f"FAIL: Transfer failed: {res}")
    except Exception as e:
        print(f"FAIL: Exception during transfer: {e}")

if __name__ == "__main__":
    test_defi_logic_update()
