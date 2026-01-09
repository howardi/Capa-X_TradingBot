import json
import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def deploy_contract():
    print("🚀 Preparing to deploy ERC20StakePool...")

    # 1. Connect to Blockchain
    # Default to a testnet RPC (e.g., BSC Testnet or similar) or localhost
    # User should replace this with their desired RPC URL
    rpc_url = os.getenv("RPC_URL", "https://data-seed-prebsc-1-s1.binance.org:8545") 
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print(f"❌ Connection to {rpc_url} failed.")
        return

    print(f"✅ Connected to {rpc_url}")
    print(f"   Chain ID: {w3.eth.chain_id}")

    # 2. Setup Account
    # WARNING: Never hardcode private keys in production
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("❌ PRIVATE_KEY not found in environment variables.")
        print("   Please create a .env file with PRIVATE_KEY=your_key")
        return

    account = w3.eth.account.from_key(private_key)
    print(f"   Deployer Address: {account.address}")
    print(f"   Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH/BNB")

    # 3. Load Artifacts
    try:
        with open('contracts/ERC20StakePool_abi.json', 'r') as f:
            abi = json.load(f)
        with open('contracts/ERC20StakePool_bytecode.json', 'r') as f:
            bytecode = json.load(f)
    except FileNotFoundError:
        print("❌ Artifacts not found. Run compile_contract.py first.")
        return

    # 4. Constructor Arguments
    # The contract constructor requires: 
    # constructor(address _stakeToken, address _rewardToken)
    # User must provide these addresses
    stake_token = input("Enter Stake Token Address (ERC20): ").strip()
    reward_token = input("Enter Reward Token Address (ERC20): ").strip()

    if not Web3.is_address(stake_token) or not Web3.is_address(reward_token):
        print("❌ Invalid address provided.")
        return

    # 5. Build Transaction
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    print("Build transaction...")
    construct_txn = Contract.constructor(stake_token, reward_token).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price
    })

    # 6. Sign & Send
    print("Signing transaction...")
    signed_txn = w3.eth.account.sign_transaction(construct_txn, private_key=private_key)
    
    print("Sending transaction... (Please wait)")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"   Tx Hash: {tx_hash.hex()}")

    # 7. Wait for Receipt
    print("Waiting for confirmation...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"🎉 Contract Deployed!")
    print(f"   Contract Address: {tx_receipt.contractAddress}")
    
    # Save address to file for future use
    with open('contracts/deployed_address.txt', 'w') as f:
        f.write(tx_receipt.contractAddress)

if __name__ == "__main__":
    deploy_contract()
