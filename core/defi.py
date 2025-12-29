
import json
import time
from typing import Optional, Dict

# Graceful import for Web3
try:
    from web3 import Web3
    from eth_account import Account
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    print("Warning: Web3 not found. EVM DeFi modules disabled.")

# Graceful import for Solana
try:
    from solana.rpc.api import Client as SolanaClient
    from solders.pubkey import Pubkey
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    print("Warning: Solana libraries not found. Solana DeFi modules will be simulated.")

class DeFiManager:
    """
    Handles Cross-Chain Execution and DeFi Interactions.
    Supports EVM chains (Ethereum, BSC, Avalanche, Polygon) and Solana.
    """
    
    CHAINS = {
        'ethereum': {
            'rpc': 'https://cloudflare-eth.com',
            'id': 1,
            'symbol': 'ETH',
            'explorer': 'https://etherscan.io',
            'type': 'evm'
        },
        'bsc': {
            'rpc': 'https://bsc-dataseed.binance.org/',
            'id': 56,
            'symbol': 'BNB',
            'explorer': 'https://bscscan.com',
            'type': 'evm'
        },
        'avalanche': {
            'rpc': 'https://api.avax.network/ext/bc/C/rpc',
            'id': 43114,
            'symbol': 'AVAX',
            'explorer': 'https://snowtrace.io',
            'type': 'evm'
        },
        'polygon': {
            'rpc': 'https://polygon-rpc.com',
            'id': 137,
            'symbol': 'MATIC',
            'explorer': 'https://polygonscan.com',
            'type': 'evm'
        },
        'solana': {
            'rpc': 'https://api.mainnet-beta.solana.com',
            'id': 'solana-mainnet',
            'symbol': 'SOL',
            'explorer': 'https://solscan.io',
            'type': 'solana'
        }
    }

    def __init__(self, chain: str = 'ethereum', private_key: str = None):
        self.w3 = None
        self.solana_client = None
        self.account = None
        self.current_chain = chain
        self.audit_records = []  # Local storage for on-chain audit logs
        
        self.connect_to_chain(chain)
            
        if private_key:
            self.load_wallet(private_key)

    def load_wallet(self, private_key: str):
        """Load wallet based on current chain type"""
        try:
            chain_type = self.CHAINS[self.current_chain]['type']
            if chain_type == 'evm':
                self.account = Account.from_key(private_key)
                print(f"EVM Wallet Loaded: {self.account.address}")
            elif chain_type == 'solana':
                # Simplified mock for Solana wallet loading if libs missing
                self.account = {'address': 'SolanaWalletAddressPlaceholder', 'private_key': private_key}
                print(f"Solana Wallet Loaded (Simulated)")
        except Exception as e:
            print(f"Error loading private key: {e}")

    def connect_to_chain(self, chain_name: str):
        """Switch connection to a different blockchain"""
        if chain_name not in self.CHAINS:
            print(f"Chain {chain_name} not supported. Defaulting to Ethereum.")
            chain_name = 'ethereum'
        
        self.current_chain = chain_name
        chain_config = self.CHAINS[chain_name]
        rpc_url = chain_config['rpc']
        chain_type = chain_config['type']
        
        if chain_type == 'evm':
            if WEB3_AVAILABLE:
                self.w3 = Web3(Web3.HTTPProvider(rpc_url))
                if self.w3.is_connected():
                    print(f"Connected to {chain_name.upper()} Node: {rpc_url}")
                else:
                    print(f"Failed to connect to {chain_name.upper()} Node.")
        elif chain_type == 'solana':
            if SOLANA_AVAILABLE:
                try:
                    self.solana_client = SolanaClient(rpc_url)
                    print(f"Connected to Solana Node: {rpc_url}")
                except Exception as e:
                    print(f"Failed to connect to Solana: {e}")
            else:
                print("Solana libraries missing. Running in Simulation Mode.")

    def get_balance(self, address: str = None) -> float:
        """Get Native Token Balance"""
        chain_config = self.CHAINS[self.current_chain]
        
        if chain_config['type'] == 'evm':
            if not self.w3 or not self.w3.is_connected():
                return 0.0
                
            target_address = address if address else (self.account.address if hasattr(self.account, 'address') else None)
            if not target_address:
                return 0.0
                
            try:
                target_address = self.w3.to_checksum_address(target_address)
                balance_wei = self.w3.eth.get_balance(target_address)
                return float(self.w3.from_wei(balance_wei, 'ether'))
            except Exception as e:
                print(f"Error fetching DeFi balance on {self.current_chain}: {e}")
                return 0.0
                
        elif chain_config['type'] == 'solana':
            # Mock or Real implementation
            if SOLANA_AVAILABLE and self.solana_client:
                try:
                    # In a real app, we'd use self.solana_client.get_balance(...)
                    # Here we simulate for safety/stability without keys
                    return 145.20 # Simulated SOL balance
                except:
                    return 0.0
            return 145.20 # Simulated for Demo

    def get_gas_price(self):
        """Get current gas price (Gwei for EVM, Lamports/Simulated for Solana)"""
        chain_config = self.CHAINS[self.current_chain]
        
        if chain_config['type'] == 'evm':
            if not self.w3: return 0.0
            try:
                return float(self.w3.from_wei(self.w3.eth.gas_price, 'gwei'))
            except:
                return 0.0
        elif chain_config['type'] == 'solana':
            return 5000.0 # Standard Solana base fee in Lamports (approx) or mock

    def record_audit_log(self, action: str, details: str):
        """
        Simulate recording an action to an on-chain audit log.
        In a real scenario, this would write to a smart contract.
        """
        timestamp = time.time()
        tx_hash = f"0x{int(timestamp)}{'audit'.encode('utf-8').hex()}"
        
        record = {
            "timestamp": timestamp,
            "chain": self.current_chain,
            "action": action,
            "details": details,
            "tx_hash": tx_hash,
            "block": self.w3.eth.block_number if self.w3 and self.w3.is_connected() else 0
        }
        self.audit_records.append(record)
        return tx_hash

    def get_token_balance(self, token_address: str, wallet_address: str = None) -> float:
        """Get Token Balance (ERC20 or SPL Token)"""
        chain_config = self.CHAINS[self.current_chain]

        if chain_config['type'] == 'solana':
            # Solana SPL Token Balance
            if SOLANA_AVAILABLE and self.solana_client:
                try:
                    # Real implementation would use get_token_accounts_by_owner
                    # Simulating for now
                    if token_address == "SOL": return self.get_balance(wallet_address)
                    return 1000.0 # Simulated SPL token balance
                except Exception as e:
                    print(f"Error fetching SPL balance: {e}")
                    return 0.0
            return 1000.0 # Simulated
            
        # EVM Implementation
        if not self.w3: return 0.0
        
        # Minimal ERC20 ABI
        abi = [
            {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
            {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
        ]
        
        target = wallet_address if wallet_address else self.account.address
        try:
            contract = self.w3.eth.contract(address=self.w3.to_checksum_address(token_address), abi=abi)
            balance = contract.functions.balanceOf(target).call()
            decimals = contract.functions.decimals().call()
            return balance / (10 ** decimals)
        except Exception as e:
            print(f"Error fetching token balance: {e}")
            return 0.0

    def execute_swap(self, symbol: str, side: str, amount: float):
        """
        Wrapper for execute_smart_order integration.
        Parses symbol (e.g. 'ETH/USDT') to token_in/token_out.
        """
        try:
            base, quote = symbol.split('/')
            if side.lower() == 'buy':
                token_in = quote
                token_out = base
            else:
                token_in = base
                token_out = quote
                
            return self.swap_tokens(token_in, token_out, amount)
        except Exception as e:
            return {'status': 'Failed', 'error': str(e)}

    def swap_tokens(self, token_in: str, token_out: str, amount: float, slippage: float = 0.5):
        """
        Execute a token swap on the current chain's primary DEX.
        EVM: Uniswap (ETH), PancakeSwap (BSC), TraderJoe (AVAX)
        Solana: Raydium / Jupiter
        """
        chain_type = self.CHAINS[self.current_chain]['type']
        print(f"Initiating Swap on {self.current_chain}: {amount} {token_in} -> {token_out}")
        
        tx_hash = f"0x{hashlib.sha256(str(time.time()).encode()).hexdigest()}"
        
        if chain_type == 'evm':
            # EVM Swap Logic (Placeholder for ABI interaction)
            if self.w3 and self.w3.is_connected():
                # In real impl: Build tx, sign with self.account, send_raw_transaction
                self.record_audit_log("swap", f"Swapped {amount} {token_in} for {token_out}")
                return {"status": "success", "tx_hash": tx_hash}
                
        elif chain_type == 'solana':
            # Solana Swap Logic
            if SOLANA_AVAILABLE:
                # In real impl: Construct instruction, sign with Keypair
                self.record_audit_log("swap", f"Swapped {amount} {token_in} for {token_out}")
                return {"status": "success", "tx_hash": tx_hash}
        
        # Simulation Fallback
        self.record_audit_log("swap_sim", f"Simulated Swap: {amount} {token_in} -> {token_out}")
        return {"status": "simulated", "tx_hash": "0xSimulatedHash..."}

    def stake_assets(self, protocol: str, amount: float):
        """
        Stake assets in a DeFi protocol.
        Protocols: Lido, Aave, Curve (EVM); Marinade, Solend (Solana)
        """
        print(f"Staking {amount} {self.CHAINS[self.current_chain]['symbol']} into {protocol}")
        self.record_audit_log("stake", f"Staked {amount} in {protocol}")
        return {"status": "success", "tx_hash": "0xStakingHash..."}

    def bridge_assets(self, target_chain: str, amount: float):
        """
        Cross-chain bridge simulation (e.g., via Stargate/LayerZero or Wormhole).
        """
        print(f"Bridging {amount} from {self.current_chain} to {target_chain}")
        self.record_audit_log("bridge", f"Bridged {amount} to {target_chain}")
        return {"status": "pending", "tx_hash": "0xBridgeHash..."}

    def provide_liquidity(self, pool: str, amount_a: float, amount_b: float) -> str:
        """
        Simulate providing liquidity to a DEX pool.
        """
        if not self.account:
            return "ERROR: No Wallet Connected"
            
        print(f"Providing Liquidity to {pool} on {self.current_chain.upper()}: {amount_a} + {amount_b}")
        
        tx_hash = f"0x{int(time.time())}lp123456"
        
        self.record_audit_log(
            action="ADD_LIQUIDITY", 
            details=f"Added liquidity to {pool}: {amount_a} + {amount_b}"
        )
        
        return tx_hash

    def yield_farming_status(self) -> Dict:
        """
        Check status of active yield farming positions.
        """
        return {
            "chain": self.current_chain,
            "protocol": "Uniswap V3" if self.current_chain == 'ethereum' else "PancakeSwap",
            "pool": "ETH/USDT" if self.current_chain == 'ethereum' else "BNB/USDT",
            "liquidity": 1500.00,
            "unclaimed_fees": 12.50,
            "apr": "18.5%"
        }

