import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from core.evm_client import (
        NetworkClient, Wallet, fetch_balances, quote_out, 
        swap_exact_eth_for_tokens, stake_tokens, read_staking_status, 
        wait_for_receipt
    )
except ImportError:
    print("Error: Could not import core.evm_client. Make sure you are running this from the project root or scripts directory.")
    sys.exit(1)

def example_flow():
    print("--- Starting EVM Example Flow ---")
    
    # Setup
    try:
        nc = NetworkClient.from_config("ethereum")
    except ValueError:
        print("Error: 'ethereum' configuration not found. Please check EVM_NETWORKS in core/evm_client.py")
        return

    pk = os.getenv("WALLET_PRIVATE_KEY")  # Load securely (env/vault)
    if not pk:
        print("Error: WALLET_PRIVATE_KEY environment variable not set.")
        print("Please set it to a valid private key to run this example.")
        return

    try:
        wallet = Wallet.from_private_key(pk)
        print(f"Loaded wallet: {wallet.address}")
    except Exception as e:
        print(f"Error loading wallet: {e}")
        return

    # Balances
    # USDT and USDC on Mainnet
    tokens = [
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    ]
    
    print("Fetching balances...")
    balances = fetch_balances(nc, wallet, tokens)
    print("Balances:", balances)

    # Quote and swap ETH -> USDC via WETH path
    amount_in_eth = 0.001 # Reduced amount for safety in example
    amount_in_wei = nc.w3.to_wei(amount_in_eth, "ether")
    
    # Path: WETH -> USDC
    if not nc.wrapped_native:
        print("Error: Wrapped native token not defined for this network.")
        return

    path = [nc.wrapped_native, tokens[1]]
    
    print(f"Getting quote for {amount_in_eth} ETH -> USDC...")
    try:
        amounts = quote_out(nc, amount_in_wei, path)
        print(f"Quote received: {amounts}")
        
        expected_out_wei = amounts[-1]
        min_out_wei = int(expected_out_wei * 0.995)  # 0.5% slippage
        
        print(f"Swapping {amount_in_eth} ETH for min {min_out_wei} Wei of USDC...")
        # Uncomment to execute real transaction
        # tx_hash = swap_exact_eth_for_tokens(nc, wallet, amount_in_eth, min_out_wei, path)
        # print("Swap tx:", tx_hash)
        # wait_for_receipt(nc, tx_hash)
        print("Swap simulated (uncomment lines in script to execute)")
        
    except Exception as e:
        print(f"Swap/Quote failed: {e}")

    # Stake USDC into a sample pool (replace with your deployed pool address)
    pool_addr = "0xYourStakePoolAddress"
    stake_token = tokens[1]
    
    # Stake 5 USDC
    # print(f"Staking 5 USDC into {pool_addr}...")
    # try:
    #     tx_hash2 = stake_tokens(nc, wallet, pool_addr, stake_token, 5.0)
    #     print("Stake tx:", tx_hash2)
    #     wait_for_receipt(nc, tx_hash2)
    # except Exception as e:
    #     print(f"Staking failed: {e}")

    # Read staking status
    # try:
    #     status = read_staking_status(nc, pool_addr, wallet.address)
    #     print("Staking status:", status)
    # except Exception as e:
    #     print(f"Reading status failed: {e}")

if __name__ == "__main__":
    example_flow()
