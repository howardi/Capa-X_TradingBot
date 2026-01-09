import os
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    # Web3.py v6+ compatibility
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
from eth_account import Account

# -----------------------------
# Network and contract configs
# -----------------------------
EVM_NETWORKS = {
    "ethereum": {
        "rpc": os.getenv("RPC_ETHEREUM", "https://mainnet.infura.io/v3/YOUR_KEY"),
        "chain_id": 1,
        "router_v2": "0x7a250d5630B4cF539739df2C5dAcb4c659F2488D",  # Uniswap V2
        "wrapped_native": "0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2",  # WETH
        "poa": False,
    },
    "bsc": {
        "rpc": os.getenv("RPC_BSC", "https://bsc-dataseed.binance.org"),
        "chain_id": 56,
        "router_v2": "0x10ED43C718714eb63d5aA57B78B54704E256024E",  # Pancake V2
        "wrapped_native": "0xBB4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
        "poa": True,
    },
    "polygon": {
        "rpc": os.getenv("RPC_POLYGON", "https://polygon-rpc.com"),
        "chain_id": 137,
        "router_v2": "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506",  # Sushi Polygon
        "wrapped_native": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH (bridged)
        "poa": True,
    },
}

# Minimal ERC-20 ABI
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
     "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
     "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]

# UniswapV2 Router ABI (subset)
UNISWAP_V2_ROUTER_ABI = [
    {"name": "getAmountsOut", "outputs": [{"type": "uint256[]", "name": "amounts"}],
     "inputs": [{"type": "uint256", "name": "amountIn"},
                {"type": "address[]", "name": "path"}],
     "stateMutability": "view", "type": "function"},
    {"name": "swapExactETHForTokens", "outputs": [{"type": "uint256[]", "name": "amounts"}],
     "inputs": [{"type": "uint256", "name": "amountOutMin"},
                {"type": "address[]", "name": "path"},
                {"type": "address", "name": "to"},
                {"type": "uint256", "name": "deadline"}],
     "stateMutability": "payable", "type": "function"},
    {"name": "swapExactTokensForETH", "outputs": [{"type": "uint256[]", "name": "amounts"}],
     "inputs": [{"type": "uint256", "name": "amountIn"},
                {"type": "uint256", "name": "amountOutMin"},
                {"type": "address[]", "name": "path"},
                {"type": "address", "name": "to"},
                {"type": "uint256", "name": "deadline"}],
     "stateMutability": "nonpayable", "type": "function"},
    {"name": "swapExactTokensForTokens", "outputs": [{"type": "uint256[]", "name": "amounts"}],
     "inputs": [{"type": "uint256", "name": "amountIn"},
                {"type": "uint256", "name": "amountOutMin"},
                {"type": "address[]", "name": "path"},
                {"type": "address", "name": "to"},
                {"type": "uint256", "name": "deadline"}],
     "stateMutability": "nonpayable", "type": "function"},
]

# Staking pool ABI
STAKE_POOL_ABI = [
    {"name": "stake", "type": "function", "stateMutability": "nonpayable", 
     "inputs": [{"name": "amount", "type": "uint256"}], "outputs": []}, 
    {"name": "withdraw", "type": "function", "stateMutability": "nonpayable", 
     "inputs": [{"name": "amount", "type": "uint256"}], "outputs": []}, 
    {"name": "claim", "type": "function", "stateMutability": "nonpayable", 
     "inputs": [], "outputs": []}, 
    {"name": "earned", "type": "function", "stateMutability": "view", 
     "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]}, 
    {"name": "userStake", "type": "function", "stateMutability": "view", 
     "inputs": [{"name": "", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]}, 
]


# -----------------------------
# Core clients
# -----------------------------
@dataclass
class NetworkClient:
    name: str
    w3: Web3
    chain_id: int
    router_v2: Optional[str]
    wrapped_native: Optional[str]

    @staticmethod
    def from_config(name: str) -> "NetworkClient":
        cfg = EVM_NETWORKS.get(name)
        if not cfg:
            raise ValueError(f"Network {name} not found in configuration")
            
        rpc_url = cfg["rpc"].replace("`", "").strip()
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if cfg.get("poa"):
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
        return NetworkClient(
            name=name,
            w3=w3,
            chain_id=cfg["chain_id"],
            router_v2=cfg.get("router_v2"),
            wrapped_native=cfg.get("wrapped_native"),
        )


@dataclass
class Wallet:
    address: str
    private_key: Optional[str] = None

    @staticmethod
    def from_address(address: str) -> "Wallet":
        return Wallet(address=Web3.to_checksum_address(address))

    @staticmethod
    def from_private_key(private_key: str) -> "Wallet":
        acct = Account.from_key(private_key)
        return Wallet(address=acct.address, private_key=private_key)


# -----------------------------
# Utilities
# -----------------------------
# def get_native_balance(nc: NetworkClient, address: str) -> float:
#    wei = nc.w3.eth.get_balance(Web3.to_checksum_address(address))
#    return float(nc.w3.from_wei(wei, "ether"))

# -----------------------------
# Gas estimator (EIP-1559 aware)
# -----------------------------
def estimate_eip1559_gas(nc: NetworkClient, priority_gwei: float = 1.5, max_multiplier: float = 2.0) -> Dict[str, int]:
    block = nc.w3.eth.get_block("latest")
    base_fee = block.get("baseFeePerGas", None)
    if base_fee is None:
        # Fallback to legacy gas price networks
        gas_price = int(nc.w3.eth.gas_price)
        return {"gasPrice": gas_price}
    base_fee_int = int(base_fee)
    priority = nc.w3.to_wei(priority_gwei, "gwei")
    max_fee = int(base_fee_int * max_multiplier + priority)
    return {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": int(priority)}

def build_base_tx(nc: NetworkClient, wallet: Wallet, value_wei: int = 0) -> Dict[str, Any]:
    nonce = nc.w3.eth.get_transaction_count(wallet.address)
    gas_params = estimate_eip1559_gas(nc)
    tx = {
        "from": wallet.address,
        "nonce": nonce,
        "value": value_wei,
        "chainId": nc.chain_id,
    }
    tx.update(gas_params)
    return tx

def sign_and_send(nc: NetworkClient, wallet: Wallet, tx: Dict[str, Any]) -> str:
    assert wallet.private_key, "Private key required for signing."
    signed = nc.w3.eth.account.sign_transaction(tx, wallet.private_key)
    tx_hash = nc.w3.eth.send_raw_transaction(signed.rawTransaction)
    return nc.w3.to_hex(tx_hash)

def wait_for_receipt(nc: NetworkClient, tx_hash: str, timeout: int = 180):
    return nc.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)


# -----------------------------
# ERC-20 helpers
# -----------------------------
def erc20(nc: NetworkClient, token: str):
    return nc.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)

def token_decimals(nc: NetworkClient, token: str) -> int:
    return erc20(nc, token).functions.decimals().call()

def token_balance(nc: NetworkClient, token: str, holder: str) -> float:
    c = erc20(nc, token)
    dec = c.functions.decimals().call()
    bal = c.functions.balanceOf(Web3.to_checksum_address(holder)).call()
    return bal / (10 ** dec)


# -----------------------------
# Transfers (native & ERC-20)
# -----------------------------
def transfer_native(nc: NetworkClient, wallet: Wallet, to: str, amount_eth: float) -> str:
    value_wei = nc.w3.to_wei(amount_eth, "ether")
    tx = build_base_tx(nc, wallet, value_wei=value_wei)
    tx["to"] = Web3.to_checksum_address(to)
    tx["gas"] = 21000
    return sign_and_send(nc, wallet, tx)

def approve_erc20(nc: NetworkClient, wallet: Wallet, token: str, spender: str, amount: int) -> str:
    contract = erc20(nc, token)
    tx = contract.functions.approve(Web3.to_checksum_address(spender), amount).build_transaction(
        build_base_tx(nc, wallet)
    )
    tx["gas"] = nc.w3.eth.estimate_gas(tx)
    return sign_and_send(nc, wallet, tx)

def transfer_erc20(nc: NetworkClient, wallet: Wallet, token: str, to: str, amount_tokens: float) -> str:
    contract = erc20(nc, token)
    decimals = contract.functions.decimals().call()
    amount = int(amount_tokens * (10 ** decimals))
    tx = contract.functions.transfer(Web3.to_checksum_address(to), amount).build_transaction(
        build_base_tx(nc, wallet)
    )
    tx["gas"] = nc.w3.eth.estimate_gas(tx)
    return sign_and_send(nc, wallet, tx)


# -----------------------------
# DEX swaps (Uniswap V2-style)
# -----------------------------
def router(nc: NetworkClient):
    return nc.w3.eth.contract(address=Web3.to_checksum_address(nc.router_v2), abi=UNISWAP_V2_ROUTER_ABI)

def quote_out(nc: NetworkClient, amount_in_wei: int, path: List[str]) -> List[int]:
    r = router(nc)
    return r.functions.getAmountsOut(amount_in_wei, [Web3.to_checksum_address(p) for p in path]).call()

def swap_exact_eth_for_tokens(nc: NetworkClient, wallet: Wallet, amount_in_eth: float,
                              min_out_tokens_wei: int, path: List[str], deadline_secs: int = 300) -> str:
    r = router(nc)
    deadline = int(time.time()) + deadline_secs
    tx = r.functions.swapExactETHForTokens(
        min_out_tokens_wei,
        [Web3.to_checksum_address(p) for p in path],
        wallet.address,
        deadline
    ).build_transaction(build_base_tx(nc, wallet, value_wei=nc.w3.to_wei(amount_in_eth, "ether")))
    tx["gas"] = nc.w3.eth.estimate_gas(tx)
    return sign_and_send(nc, wallet, tx)

def ensure_approval(nc: NetworkClient, wallet: Wallet, token: str, spender: str, amount_wei: int):
    c = erc20(nc, token)
    allowance = c.functions.allowance(wallet.address, Web3.to_checksum_address(spender)).call()
    if allowance < amount_wei:
        tx = c.functions.approve(Web3.to_checksum_address(spender), amount_wei).build_transaction(build_base_tx(nc, wallet))
        tx["gas"] = nc.w3.eth.estimate_gas(tx)
        h = sign_and_send(nc, wallet, tx)
        wait_for_receipt(nc, h)

def swap_exact_tokens_for_tokens(nc: NetworkClient, wallet: Wallet, token_in: str, token_out: str,
                                 amount_in_tokens: float, min_out_tokens_wei: int,
                                 path: Optional[List[str]] = None, deadline_secs: int = 300) -> str:
    c_in = erc20(nc, token_in)
    dec_in = c_in.functions.decimals().call()
    amount_in_wei = int(amount_in_tokens * (10 ** dec_in))

    if path is None:
        path = [token_in, nc.wrapped_native, token_out]

    ensure_approval(nc, wallet, token_in, nc.router_v2, amount_in_wei)
    r = router(nc)
    deadline = int(time.time()) + deadline_secs
    tx = r.functions.swapExactTokensForTokens(
        amount_in_wei,
        min_out_tokens_wei,
        [Web3.to_checksum_address(p) for p in path],
        wallet.address,
        deadline
    ).build_transaction(build_base_tx(nc, wallet))
    tx["gas"] = nc.w3.eth.estimate_gas(tx)
    return sign_and_send(nc, wallet, tx)

# -----------------------------
# Staking interactions
# -----------------------------
def stake_pool(nc: NetworkClient, pool_address: str):
    return nc.w3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=STAKE_POOL_ABI)

def stake_tokens(nc: NetworkClient, wallet: Wallet, pool_address: str, stake_token: str, amount_tokens: float) -> str:
    c = erc20(nc, stake_token)
    dec = c.functions.decimals().call()
    amount_wei = int(amount_tokens * (10 ** dec))

    # Approve stake token to pool
    ensure_approval(nc, wallet, stake_token, pool_address, amount_wei)

    # Stake
    pool = stake_pool(nc, pool_address)
    tx = pool.functions.stake(amount_wei).build_transaction(build_base_tx(nc, wallet))
    tx["gas"] = nc.w3.eth.estimate_gas(tx)
    return sign_and_send(nc, wallet, tx)

def withdraw_stake(nc: NetworkClient, wallet: Wallet, pool_address: str, amount_tokens: float, stake_token: str) -> str:
    c = erc20(nc, stake_token)
    dec = c.functions.decimals().call()
    amount_wei = int(amount_tokens * (10 ** dec))
    pool = stake_pool(nc, pool_address)
    tx = pool.functions.withdraw(amount_wei).build_transaction(build_base_tx(nc, wallet))
    tx["gas"] = nc.w3.eth.estimate_gas(tx)
    return sign_and_send(nc, wallet, tx)

def claim_rewards(nc: NetworkClient, wallet: Wallet, pool_address: str) -> str:
    pool = stake_pool(nc, pool_address)
    tx = pool.functions.claim().build_transaction(build_base_tx(nc, wallet))
    tx["gas"] = nc.w3.eth.estimate_gas(tx)
    return sign_and_send(nc, wallet, tx)

def read_staking_status(nc: NetworkClient, pool_address: str, user: str) -> Dict[str, float]:
    pool = stake_pool(nc, pool_address)
    user_stake_wei = pool.functions.userStake(Web3.to_checksum_address(user)).call()
    earned_wei = pool.functions.earned(Web3.to_checksum_address(user)).call()
    return {
        "userStakeWei": float(user_stake_wei),
        "earnedWei": float(earned_wei),
    }

# -----------------------------
# Balance fetching (address or private key)
# -----------------------------
def native_balance(nc: NetworkClient, address: str) -> float:
    wei = nc.w3.eth.get_balance(Web3.to_checksum_address(address))
    return float(nc.w3.from_wei(wei, "ether"))

def fetch_balances(nc: NetworkClient, wallet: Wallet, tokens: Optional[List[str]] = None) -> Dict[str, Any]:
    res = {"native": native_balance(nc, wallet.address), "tokens": {}}
    if tokens:
        for t in tokens:
            try:
                res["tokens"][Web3.to_checksum_address(t)] = token_balance(nc, t, wallet.address)
            except Exception as e:
                res["tokens"][Web3.to_checksum_address(t)] = f"error: {e}"
    return res
