
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.web3_wallet import Web3Wallet

def test_wallet_features():
    print("Initializing Web3Wallet...")
    wallet_manager = Web3Wallet()
    
    print("\n--- Testing Wallet Generation ---")
    new_wallet = wallet_manager.generate_wallet()
    print(f"Generated Address: {new_wallet['address']}")
    print(f"Private Key: {new_wallet['private_key'][:6]}...{new_wallet['private_key'][-4:]}")
    
    print("\n--- Testing QR Code Generation ---")
    qr_bytes = wallet_manager.generate_qr_code(new_wallet['address'])
    print(f"QR Code generated, size: {len(qr_bytes)} bytes")
    
    print("\n--- Testing Balance Scanning (Mock/Real) ---")
    # Using a known address with some history or the generated one (likely empty)
    # Let's use the generated one to ensure no errors occur even if empty
    balances = wallet_manager.scan_all_balances(new_wallet['address'])
    print("Balances found:")
    for chain, bal in balances.items():
        print(f"  {chain}: {bal}")
        
    print("\n--- Testing Token Scanning (Mock) ---")
    # Define some dummy tokens for testing
    tokens = {
        'Ethereum': [{'symbol': 'USDT', 'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7'}],
        'BSC': [{'symbol': 'BUSD', 'address': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'}]
    }
    token_balances = wallet_manager.scan_tokens(new_wallet['address'], tokens)
    print("Token Balances found:")
    for chain, tokens in token_balances.items():
        print(f"  {chain}:")
        for token, bal in tokens.items():
            print(f"    {token}: {bal}")

if __name__ == "__main__":
    test_wallet_features()
