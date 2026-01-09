import time
from typing import List, Dict, Optional
from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    try:
        from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
    except ImportError:
        geth_poa_middleware = None

# Common V2 Router ABI (simplified for swap + quote)
UNISWAP_V2_ROUTER_ABI = [
    {"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}
]

# -------------------------
# Utilities
# -------------------------
def make_web3(rpc: str, poa: bool = False) -> Web3:
    rpc = rpc.replace("`", "").strip()
    w3 = Web3(Web3.HTTPProvider(rpc))
    if poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def checksum(addr: str) -> str:
    return Web3.to_checksum_address(addr)

def now_deadline(seconds: int = 300) -> int:
    return int(time.time()) + seconds

# -------------------------
# DexClient
# -------------------------
class DexClient:
    """
    DexClient supports V2-style routers (getAmountsOut + swapExact...).
    For Uniswap V3, a separate quoter integration is recommended.
    """
    def __init__(self, name: str, router_address: str, network_cfg: dict):
        self.name = name
        self.router_address = checksum(router_address)
        self.network_cfg = network_cfg
        self.w3 = make_web3(network_cfg["rpc"], poa=network_cfg.get("poa", False))
        self.chain_id = network_cfg["chain_id"]
        self.router = self.w3.eth.contract(address=self.router_address, abi=UNISWAP_V2_ROUTER_ABI)

    def get_quote_v2(self, amount_in_wei: int, path: List[str]) -> List[int]:
        """
        Calls getAmountsOut on V2 router. Returns list of amounts along path.
        """
        path_cs = [checksum(p) for p in path]
        return self.router.functions.getAmountsOut(amount_in_wei, path_cs).call()

    def build_swap_exact_tokens_for_tokens(self, from_addr: str, to_addr: str, amount_in_wei: int, amount_out_min_wei: int, path: List[str], deadline: int) -> Dict:
        tx = self.router.functions.swapExactTokensForTokens(
            amount_in_wei,
            amount_out_min_wei,
            [checksum(p) for p in path],
            checksum(to_addr),
            deadline
        ).build_transaction({
            "from": checksum(from_addr),
            "nonce": self.w3.eth.get_transaction_count(checksum(from_addr)),
            "chainId": self.chain_id,
        })
        return tx

    def build_swap_exact_eth_for_tokens(self, from_addr: str, to_addr: str, amount_out_min_wei: int, path: List[str], deadline: int, value_wei: int) -> Dict:
        tx = self.router.functions.swapExactETHForTokens(
            amount_out_min_wei,
            [checksum(p) for p in path],
            checksum(to_addr),
            deadline
        ).build_transaction({
            "from": checksum(from_addr),
            "nonce": self.w3.eth.get_transaction_count(checksum(from_addr)),
            "chainId": self.chain_id,
            "value": value_wei
        })
        return tx

    def estimate_gas(self, tx: Dict) -> int:
        return self.w3.eth.estimate_gas(tx)

    def send_signed_tx(self, signed_raw: bytes) -> str:
        tx_hash = self.w3.eth.send_raw_transaction(signed_raw)
        return self.w3.to_hex(tx_hash)

    def tx_receipt(self, tx_hash: str, timeout: int = 120, poll_interval: float = 3.0) -> Optional[dict]:
        start = time.time()
        while time.time() - start < timeout:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                return dict(receipt)
            time.sleep(poll_interval)
        return None

    def gas_price_params(self, priority_gwei: float = 1.5, max_multiplier: float = 2.0) -> Dict:
        """
        Return gas params: either legacy gasPrice or EIP-1559 fields.
        """
        try:
            latest = self.w3.eth.get_block("latest")
            base_fee = latest.get("baseFeePerGas", None)
            if base_fee is None:
                return {"gasPrice": int(self.w3.eth.gas_price)}
            base_fee_int = int(base_fee)
            priority = self.w3.to_wei(priority_gwei, "gwei")
            max_fee = int(base_fee_int * max_multiplier + priority)
            return {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": int(priority)}
        except Exception:
            return {"gasPrice": int(self.w3.eth.gas_price)}
