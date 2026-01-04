
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
        
        # Router Addresses (Uniswap V2 / PancakeSwap / QuickSwap)
        self.ROUTERS = {
            'ethereum': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D', # Uniswap V2
            'bsc': '0x10ED43C718714eb63d5aA57B78B54704E256024E',      # PancakeSwap
            'polygon': '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff',  # QuickSwap
            'avalanche': '0x60aE616a2155Ee3d9A68541Ba4544862310933d4' # Trader Joe
        }

        # Common Token Addresses (Simplified Map)
        self.TOKEN_MAP = {
            'ethereum': {
                'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'ETH': '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE' # Placeholder for Native
            },
            'bsc': {
                'USDT': '0x55d398326f99059fF775485246999027B3197955',
                'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
                'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
                'BNB': '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
            },
            'polygon': {
                'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
                'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
                'WMATIC': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
                'MATIC': '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
            }
        }
        
        # ABIs
        self.ERC20_ABI = [
            {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
            {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
            {"constant":False,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
            {"constant":True,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"}
        ]
        
        self.ROUTER_ABI = [
            {"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},
            {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}
        ]

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
        
        target = wallet_address if wallet_address else (self.account.address if hasattr(self.account, 'address') else None)
        if not target: return 0.0
        
        try:
            contract = self.w3.eth.contract(address=self.w3.to_checksum_address(token_address), abi=abi)
            balance = contract.functions.balanceOf(target).call()
            decimals = contract.functions.decimals().call()
            return balance / (10 ** decimals)
        except Exception as e:
            print(f"Error fetching token balance: {e}")
            return 0.0

    def get_swap_quote(self, token_in: str, token_out: str, amount: float) -> float:
        """
        Get estimated output amount for a swap.
        """
        chain_type = self.CHAINS[self.current_chain]['type']
        
        if chain_type == 'evm':
            if not self.w3: return 0.0
            
            router_address = self.ROUTERS.get(self.current_chain)
            if not router_address: return 0.0
            
            token_map = self.TOKEN_MAP.get(self.current_chain, {})
            token_in_addr = token_map.get(token_in, token_in)
            token_out_addr = token_map.get(token_out, token_out)
            
            is_native_in = token_in in ['ETH', 'BNB', 'MATIC', 'AVAX']
            is_native_out = token_out in ['ETH', 'BNB', 'MATIC', 'AVAX']
            
            # Determine Path
            weth_addr = token_map.get('WETH') or token_map.get('WBNB') or token_map.get('WMATIC')
            path = []
            
            if is_native_in:
                path = [weth_addr, token_out_addr]
            elif is_native_out:
                path = [token_in_addr, weth_addr]
            else:
                path = [token_in_addr, token_out_addr]
                
            # Checksum addresses
            path = [self.w3.to_checksum_address(a) for a in path]
            router = self.w3.eth.contract(address=self.w3.to_checksum_address(router_address), abi=self.ROUTER_ABI)
            
            decimals_in = 6 if 'USD' in token_in else 18
            amount_in_wei = int(amount * (10 ** decimals_in))
            
            try:
                amounts = router.functions.getAmountsOut(amount_in_wei, path).call()
                amount_out_wei = amounts[-1]
                
                decimals_out = 6 if 'USD' in token_out else 18
                return float(amount_out_wei) / (10 ** decimals_out)
            except Exception as e:
                print(f"Quote Error: {e}")
                return 0.0
                
        elif chain_type == 'solana':
            # Simulated Quote
            return amount * 1.05 # Mock price impact
            
        return 0.0

    def execute_swap(self, symbol: str, side: str, amount: float):
        """
        Execute a swap on the current chain's DEX.
        Returns transaction details for frontend signing or executes if private key loaded.
        """
        try:
            # Determine Token Addresses based on Symbol (e.g., 'ETH/USDT')
            if '/' in symbol:
                base, quote = symbol.split('/')
            else:
                base, quote = symbol, 'USDT' # Default
                
            # Logic to swap Base -> Quote (Sell) or Quote -> Base (Buy)
            if side.lower() == 'buy':
                token_in = quote
                token_out = base
            else:
                token_in = base
                token_out = quote
                
            return self.swap_tokens(token_in, token_out, amount)
            
        except Exception as e:
            print(f"Swap Error: {e}")
            return {'status': 'Failed', 'error': str(e)}

    def swap_tokens(self, token_in: str, token_out: str, amount: float, slippage: float = 0.5):
        """
        Execute a token swap on the current chain's primary DEX.
        """
        chain_type = self.CHAINS[self.current_chain]['type']
        print(f"Initiating Swap on {self.current_chain}: {amount} {token_in} -> {token_out}")
        
        if chain_type == 'evm':
            if not self.w3:
                return {'status': 'Failed', 'error': 'Web3 not initialized'}

            router_address = self.ROUTERS.get(self.current_chain)
            if not router_address:
                return {'status': 'Failed', 'error': 'DEX Router not found for this chain'}
            
            # Resolve Token Addresses
            token_map = self.TOKEN_MAP.get(self.current_chain, {})
            token_in_addr = token_map.get(token_in, token_in) # Use map or assume raw address
            token_out_addr = token_map.get(token_out, token_out)
            
            # Helper to check if native
            is_native_in = token_in in ['ETH', 'BNB', 'MATIC', 'AVAX']
            is_native_out = token_out in ['ETH', 'BNB', 'MATIC', 'AVAX']
            
            # Decimals (Heuristic for Demo)
            decimals_in = 6 if 'USD' in token_in else 18
            amount_wei = int(amount * (10 ** decimals_in))
            
            # Setup Contract
            router_contract = self.w3.eth.contract(address=self.w3.to_checksum_address(router_address), abi=self.ROUTER_ABI)
            deadline = int(time.time()) + 1200 # 20 mins
            
            user_address = self.account.address if self.account else "0x0000000000000000000000000000000000000000" # Placeholder if no backend wallet
            
            # 1. Handle Approval for Tokens
            if not is_native_in:
                try:
                    token_contract = self.w3.eth.contract(address=self.w3.to_checksum_address(token_in_addr), abi=self.ERC20_ABI)
                    allowance = token_contract.functions.allowance(self.w3.to_checksum_address(user_address), self.w3.to_checksum_address(router_address)).call()
                    
                    if allowance < amount_wei:
                        # Construct Approve Transaction
                        data = token_contract.encodeABI(fn_name="approve", args=[self.w3.to_checksum_address(router_address), 2**256 - 1])
                        return {
                            'status': 'Pending_Approve',
                            'payload': {
                                'to': token_in_addr,
                                'value': "0",
                                'data': data,
                                'chainId': self.CHAINS[self.current_chain]['id']
                            },
                            'message': f'Approval needed for {token_in}. Please sign the approve transaction.'
                        }
                except Exception as e:
                    print(f"Allowance check failed (simulating approval): {e}")
                    # If backend check fails (e.g. no wallet connected), we might still want to return an approve payload for frontend
                    pass

            # 2. Construct Swap Transaction
            path = []
            try:
                # WETH/WBNB address needed for path
                weth_addr = token_map.get('WETH') or token_map.get('WBNB') or token_map.get('WMATIC')
                
                # Determine Path
                if is_native_in:
                    path = [weth_addr, token_out_addr]
                elif is_native_out:
                    path = [token_in_addr, weth_addr]
                else:
                    path = [token_in_addr, token_out_addr]
                
                # Checksum Path
                path = [self.w3.to_checksum_address(a) for a in path]

                # Calculate AmountOutMin (Slippage Protection)
                try:
                    amounts_out = router_contract.functions.getAmountsOut(amount_wei, path).call()
                    expected_out = amounts_out[-1]
                    amount_out_min = int(expected_out * (1 - slippage / 100))
                    print(f"Slippage Calcs: Expected {expected_out}, Min {amount_out_min} (Slippage {slippage}%)")
                except Exception as e:
                    print(f"Error calculating slippage: {e}")
                    amount_out_min = 0 # Fallback to 0 (risky but allows tx to proceed if view fails)

                if is_native_in:
                    # swapExactETHForTokens
                    data = router_contract.encodeABI(fn_name="swapExactETHForTokens", args=[amount_out_min, path, self.w3.to_checksum_address(user_address), deadline])
                    value = str(amount_wei)
                elif is_native_out:
                    # swapExactTokensForETH
                    data = router_contract.encodeABI(fn_name="swapExactTokensForETH", args=[amount_wei, amount_out_min, path, self.w3.to_checksum_address(user_address), deadline])
                    value = "0"
                else:
                    # swapExactTokensForTokens
                    data = router_contract.encodeABI(fn_name="swapExactTokensForTokens", args=[amount_wei, amount_out_min, path, self.w3.to_checksum_address(user_address), deadline])
                    value = "0"
                    
                return {
                    'status': 'Pending_Sign',
                    'payload': {
                        'to': router_address,
                        'value': value,
                        'data': data,
                        'chainId': self.CHAINS[self.current_chain]['id']
                    },
                    'message': f'Please sign the swap transaction ({amount} {token_in} -> {token_out}).'
                }
                
            except Exception as e:
                return {'status': 'Failed', 'error': f"Tx Construction Failed: {e}"}

        elif chain_type == 'solana':
            # Solana Swap Simulation (Jupiter Aggregator style payload)
            return {
                'status': 'Pending_Sign',
                'payload': {
                    'type': 'solana_transaction',
                    'instructions': [
                        {
                            'programId': 'JUP4Fb2cqi88N462Gzm763...Placeholder',
                            'data': 'base64_encoded_swap_instruction_data...',
                            'keys': [
                                {'pubkey': 'UserWallet...', 'isSigner': True, 'isWritable': True},
                                {'pubkey': 'TokenInVault...', 'isSigner': False, 'isWritable': True},
                                # ... more keys
                            ]
                        }
                    ]
                },
                'message': f'Please sign the Solana swap ({amount} {token_in} -> {token_out}).'
            }

        return {'status': 'Failed', 'error': 'Chain type not supported'}


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

