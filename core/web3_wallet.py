from web3 import Web3
from eth_account import Account
import logging
import requests
import time
import io
try:
    import qrcode
except ImportError:
    qrcode = None

try:
    from tronpy import Tron
except ImportError:
    Tron = None

class Web3Wallet:
    def __init__(self):
        # Chain Configuration
        self.CHAINS = {
            '1': {'name': 'Ethereum', 'rpc': 'https://eth.llamarpc.com', 'symbol': 'ETH', 'type': 'evm'},
            '56': {'name': 'BNB Chain', 'rpc': 'https://bsc-dataseed.binance.org', 'symbol': 'BNB', 'type': 'evm'},
            '137': {'name': 'Polygon', 'rpc': 'https://polygon-rpc.com', 'symbol': 'MATIC', 'type': 'evm'},
            '42161': {'name': 'Arbitrum', 'rpc': 'https://arb1.arbitrum.io/rpc', 'symbol': 'ETH', 'type': 'evm'},
            '10': {'name': 'Optimism', 'rpc': 'https://mainnet.optimism.io', 'symbol': 'ETH', 'type': 'evm'},
            '43114': {'name': 'Avalanche', 'rpc': 'https://api.avax.network/ext/bc/C/rpc', 'symbol': 'AVAX', 'type': 'evm'},
            '8453': {'name': 'Base', 'rpc': 'https://mainnet.base.org', 'symbol': 'ETH', 'type': 'evm'},
            '250': {'name': 'Fantom', 'rpc': 'https://rpc.ftm.tools', 'symbol': 'FTM', 'type': 'evm'},
            '25': {'name': 'Cronos', 'rpc': 'https://evm.cronos.org', 'symbol': 'CRO', 'type': 'evm'},
            '100': {'name': 'Gnosis', 'rpc': 'https://rpc.gnosischain.com', 'symbol': 'xDAI', 'type': 'evm'},
            '324': {'name': 'zkSync Era', 'rpc': 'https://mainnet.era.zksync.io', 'symbol': 'ETH', 'type': 'evm'},
            '59144': {'name': 'Linea', 'rpc': 'https://rpc.linea.build', 'symbol': 'ETH', 'type': 'evm'},
            'solana': {'name': 'Solana', 'rpc': 'https://api.mainnet-beta.solana.com', 'symbol': 'SOL', 'type': 'svm'},
            'ton': {'name': 'TON', 'rpc': 'https://toncenter.com/api/v2/jsonRPC', 'symbol': 'TON', 'type': 'tvm'},
            'tron': {'name': 'Tron Network (TRC-20)', 'rpc': 'https://api.trongrid.io', 'symbol': 'TRX', 'type': 'tron'},
            'bitcoin': {'name': 'Bitcoin', 'rpc': 'https://blockchain.info', 'symbol': 'BTC', 'type': 'utxo'},
            'litecoin': {'name': 'Litecoin', 'rpc': 'https://api.blockcypher.com/v1/ltc/main', 'symbol': 'LTC', 'type': 'utxo'},
            'dogecoin': {'name': 'Dogecoin', 'rpc': 'https://dogechain.info/api/v1', 'symbol': 'DOGE', 'type': 'utxo'},
            'cosmos': {'name': 'Cosmos Hub', 'rpc': 'https://cosmos-rpc.publicnode.com', 'api': 'https://cosmos-lcd.publicnode.com', 'symbol': 'ATOM', 'type': 'cosmos'}
        }
        
        # Default to Ethereum
        self.chain_id = '1'
        self.rpc_url = self.CHAINS['1']['rpc']
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        self.address = None
        self.private_key = None # Securely store key for signing (if provided)
        self.wallet_provider = None # e.g., 'MetaMask', 'Phantom', 'Manual'
        self.connected = False
        self.mode = 'read_only' # 'read_only' or 'read_write'

        # Minimal ERC20 ABI for Balance Fetching
        self.ERC20_ABI = [
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
        ]

    def add_custom_chain(self, chain_id, rpc_url, name, symbol, chain_type='evm'):
        """Dynamically add a new network configuration"""
        self.CHAINS[str(chain_id)] = {
            'name': name,
            'rpc': rpc_url,
            'symbol': symbol,
            'type': chain_type
        }

    def is_connected(self):
        return self.connected

    def connect(self, input_str, chain_id='1', provider='Unknown'):
        """
        Connects a user wallet.
        Input can be an Address (Read-Only) or Private Key (Read-Write/Trading Enabled).
        """
        self.provider = provider
        self.private_key = None
        self.mode = 'read_only'
        self.chain_id = str(chain_id)
        
        # Clean input
        input_str = input_str.strip()
        
        # 1. Check if input is a Private Key (EVM mainly)
        # EVM Keys are 64 hex chars (32 bytes), sometimes with 0x
        is_private_key = False
        if len(input_str) >= 64:
            try:
                # Try deriving address from key (EVM)
                account = Account.from_key(input_str)
                self.address = account.address
                self.private_key = input_str
                self.mode = 'read_write'
                is_private_key = True
                
                # Auto-detect EVM chain from key (fallback to default if unknown)
                self.chain_id = '1' # Default to Ethereum
                self.rpc_url = self.CHAINS['1']['rpc']
                self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
                
                self.connected = True
                return True
            except Exception:
                # Not a valid EVM key, check for Solana/Tron
                if input_str.startswith('5') or input_str.startswith('6'): # Simple heuristic for Sol PK
                     # Solana private key
                     try:
                         from solders.keypair import Keypair
                         # Assuming input_str is base58 encoded
                         import base58
                         kp = Keypair.from_base58_string(input_str)
                         self.chain_id = 'solana'
                         self.address = str(kp.pubkey())
                         self.private_key = input_str
                         self.connected = True
                         return True
                     except ImportError:
                         # Fail if solders not installed - do not mock
                         logging.error("Solana libraries not installed. Cannot derive address from private key.")
                         return False
                     except Exception as e:
                         logging.error(f"Invalid Solana Private Key: {e}")
                         return False
                         
                elif input_str.startswith('T'):
                     # Tron private key logic would go here
                     pass
                pass

        if is_private_key:
            return True

        # 2. Treat as Address (Read-Only) - Auto-Detect Chain
        detected_chain = None

        # Tron
        if input_str.startswith('T') and len(input_str) == 34:
            detected_chain = 'tron'
        
        # Cosmos
        elif input_str.startswith('cosmos1'):
            detected_chain = 'cosmos'
            
        # Bitcoin (P2PKH, P2SH, Bech32)
        elif input_str.startswith('1') or input_str.startswith('3') or input_str.startswith('bc1'):
            detected_chain = 'bitcoin'
            
        # Litecoin
        elif input_str.startswith('L') or input_str.startswith('M') or input_str.startswith('ltc1'):
            detected_chain = 'litecoin'
            
        # Dogecoin
        elif input_str.startswith('D') and len(input_str) == 34:
            detected_chain = 'dogecoin'
            
        # EVM (0x...)
        elif input_str.startswith('0x') and len(input_str) == 42:
            # If currently selected chain is NOT EVM, default to Ethereum
            # If user selected an EVM chain (e.g. BNB), keep it.
            current_type = self.CHAINS.get(str(chain_id), {}).get('type', 'evm')
            if current_type != 'evm':
                detected_chain = '1'
            else:
                detected_chain = str(chain_id)

        # Solana (Fallback for Base58-like strings)
        elif 32 <= len(input_str) <= 44:
            detected_chain = 'solana'

        # Apply Detection
        if detected_chain:
            self.chain_id = detected_chain
        else:
            self.chain_id = str(chain_id)

        # Handle Specific Chains based on resolved self.chain_id
        
        # Handle Solana/SVM Addresses
        if self.chain_id == 'solana':
            self.address = input_str
            self.connected = True
            return True

        # Handle Tron Addresses
        if self.chain_id == 'tron':
            self.address = input_str
            self.connected = True
            return True

        # Handle Bitcoin/UTXO Addresses
        if self.chain_id in ['bitcoin', 'litecoin', 'dogecoin']:
            self.address = input_str
            self.connected = True
            return True

        # Handle Cosmos Addresses
        if self.chain_id == 'cosmos':
            self.address = input_str
            self.connected = True
            return True

        # Handle TON Addresses
        if self.chain_id == 'ton':
            self.address = input_str
            self.connected = True
            return True
            
        # Handle EVM Addresses
        if Web3.is_address(input_str):
            self.address = Web3.to_checksum_address(input_str)
            self.chain_id = str(chain_id)
            self.connected = True
            
            # Update RPC if chain known
            if self.chain_id in self.CHAINS:
                self.rpc_url = self.CHAINS[self.chain_id]['rpc']
                self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
                
            return True
        
        # Fallback for ANY string if manual mode (allows partial addresses for demo)
        if provider == 'Manual':
             self.address = input_str
             self.chain_id = chain_id
             self.connected = True
             return True
             
        return False

    def disconnect(self):
        self.address = None
        self.connected = False
        self.chain_id = '1'
        self.provider = None

    def get_balance(self):
        """Get native balance of the connected wallet"""
        if not self.connected or not self.address:
            return 0.0

        chain_info = self.CHAINS.get(self.chain_id, {})
        chain_type = chain_info.get('type', 'evm')

        try:
            # EVM Balance
            if chain_type == 'evm':
                wei = self.w3.eth.get_balance(self.address)
                return float(self.w3.from_wei(wei, 'ether'))
            
            # Solana Balance
            elif chain_type == 'svm':
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [self.address]
                }
                response = requests.post(chain_info['rpc'], json=payload).json()
                if 'result' in response:
                    lamports = response['result']['value']
                    return float(lamports) / 1_000_000_000
                return 0.0

            # TON Balance
            elif chain_type == 'tvm':
                # 1. Fetch Native Balance
                native_bal = 0.0
                jetton_usd_val = 0.0
                
                try:
                    # TON Center public API (Mainnet)
                    # Using JSON-RPC getAddressBalance
                    payload = {
                        "id": "1",
                        "jsonrpc": "2.0",
                        "method": "getAddressBalance",
                        "params": {"address": self.address}
                    }
                    
                    # Try public endpoint
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(chain_info['rpc'], json=payload, headers=headers, timeout=5)
                    data = response.json()
                    
                    if data.get('ok') and 'result' in data:
                        nanotons = int(data['result'])
                        native_bal = float(nanotons) / 1_000_000_000
                    else:
                        # Fallback to tonapi.io (another public indexer)
                        url = f"https://toncenter.com/api/v2/getAddressBalance?address={self.address}"
                        resp2 = requests.get(url, timeout=5).json()
                        if resp2.get('ok'):
                             native_bal = float(resp2['result']) / 1_000_000_000
                except Exception as e:
                    logging.error(f"TON native fetch error: {e}")

                # 2. Fetch Jettons (Stablecoins mainly)
                try:
                    # tonapi.io is best for Jettons
                    j_url = f"https://tonapi.io/v2/accounts/{self.address}/jettons"
                    j_resp = requests.get(j_url, timeout=5)
                    if j_resp.status_code == 200:
                        j_data = j_resp.json()
                        for j in j_data.get('balances', []):
                            symbol = j.get('jetton', {}).get('symbol', '').upper()
                            decimals = int(j.get('jetton', {}).get('decimals', 9))
                            raw = float(j.get('balance', 0))
                            amt = raw / (10**decimals)
                            
                            # Simple Valuation for Stables
                            if symbol in ['USDT', 'USDC', 'DAI']:
                                jetton_usd_val += amt
                            # Add other valuations if price feed available
                except Exception as e:
                    logging.error(f"TON Jetton fetch error: {e}")

                # Return total "Value" in TON terms roughly, OR just return Native + Stables/Price
                # Since this function returns a float "balance", usually native.
                # BUT for "Trading with it", we want total equity.
                # Let's return a special structure or just Native. 
                # To be "Safe" for the generic get_balance(), let's return Native.
                # The Dashboard handles the USD conversion.
                # Wait, if user has ONLY USDT, they show 0 balance.
                # Let's hack it: Return Native + (JettonVal / 5.4) roughly to show "TON Equivalent"
                # OR better: The dashboard calls this. 
                
                # Let's just return Native for now to be "Accurate" to the function name.
                # AND we will add a new function get_portfolio_value() later if needed.
                # Actually, user wants "Accurate wallet balance". 
                # If I return Native + Jettons mixed, it's confusing.
                
                return native_bal

            # Tron Balance
            elif chain_type == 'tron':
                try:
                    # TronGrid API
                    # Note: Requires API Key for stability, but let's try public endpoint
                    # https://api.trongrid.io/v1/accounts/{address}
                    url = f"https://api.trongrid.io/v1/accounts/{self.address}"
                    response = requests.get(url, timeout=5).json()
                    if response.get('success') and response.get('data'):
                        # Balance is in sun (1e-6)
                        return float(response['data'][0].get('balance', 0)) / 1_000_000
                except Exception as e:
                    logging.error(f"Tron balance error: {e}")
                return 0.0

            # UTXO Balance (BTC/LTC/DOGE)
            elif chain_type == 'utxo':
                try:
                    # Use public explorers (Rate limited usually)
                    # Bitcoin: blockchain.info
                    if chain_info['symbol'] == 'BTC':
                        url = f"https://blockchain.info/q/addressbalance/{self.address}"
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            # Returns satoshis as plain text
                            return float(response.text) / 100_000_000
                    
                    # Litecoin: blockcypher
                    elif chain_info['symbol'] == 'LTC':
                         # Free tier blockcypher
                         url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{self.address}/balance"
                         response = requests.get(url, timeout=5).json()
                         return float(response.get('balance', 0)) / 100_000_000
                         
                    # Dogecoin: dogechain.info
                    elif chain_info['symbol'] == 'DOGE':
                        url = f"https://dogechain.info/api/v1/address/balance/{self.address}"
                        response = requests.get(url, timeout=5).json()
                        if response.get('success'):
                            return float(response.get('balance', 0)) # Already in DOGE? API says "balance"
                        
                except Exception as e:
                    logging.error(f"UTXO balance error: {e}")
                return 0.0

            # Cosmos Balance
            elif chain_type == 'cosmos':
                try:
                    # Use LCD API for Cosmos
                    lcd_url = chain_info.get('api', 'https://cosmos-lcd.publicnode.com')
                    url = f"{lcd_url}/cosmos/bank/v1beta1/balances/{self.address}"
                    response = requests.get(url, timeout=5).json()
                    balances = response.get('balances', [])
                    for b in balances:
                        if b['denom'] == 'uatom':
                            return float(b['amount']) / 1_000_000
                except Exception as e:
                    logging.error(f"Cosmos balance error: {e}")
                return 0.0

        except Exception as e:
            logging.error(f"Error fetching balance: {e}")
            return 0.0

    def get_portfolio_value_usd(self, price_map=None):
        """
        Returns total estimated USD value of the wallet (Native + Tokens).
        Requires price_map {symbol: price_usd} for accurate valuation.
        """
        if not self.connected or not self.address:
            return 0.0

        chain_type = self.CHAINS.get(self.chain_id, {}).get('type', 'evm')
        
        # Base Native Value
        native_bal = self.get_balance()
        total_usd = 0.0
        
        # Use provided prices or 0 (No hardcoded fallbacks)
        symbol = self.CHAINS.get(self.chain_id, {}).get('symbol', 'ETH')
        if price_map and symbol in price_map:
            price = price_map[symbol]
            total_usd += native_bal * price
        
        # Add Jettons/Tokens for TON
        if chain_type == 'tvm':
             try:
                 # tonapi.io
                 j_url = f"https://tonapi.io/v2/accounts/{self.address}/jettons"
                 j_resp = requests.get(j_url, timeout=5)
                 if j_resp.status_code == 200:
                     j_data = j_resp.json()
                     for j in j_data.get('balances', []):
                         j_symbol = j.get('jetton', {}).get('symbol', '').upper()
                         decimals = int(j.get('jetton', {}).get('decimals', 9))
                         raw = float(j.get('balance', 0))
                         amt = raw / (10**decimals)
                         
                         if j_symbol in ['USDT', 'USDC', 'DAI']:
                             total_usd += amt # 1:1 for stables
                         elif price_map and j_symbol in price_map:
                             total_usd += amt * price_map[j_symbol]
             except:
                 pass
                 
        return total_usd


    def get_token_balance(self, token_address):
        """Get balance of a specific token"""
        if not self.connected or not self.address:
            return 0.0

        chain_info = self.CHAINS.get(self.chain_id, {})
        chain_type = chain_info.get('type', 'evm')

        try:
            if chain_type == 'evm':
                contract = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=self.ERC20_ABI)
                balance = contract.functions.balanceOf(self.address).call()
                decimals = contract.functions.decimals().call()
                return float(balance) / (10 ** decimals)
            
            elif chain_type == 'svm':
                # Solana Token Balance (SPL)
                payload = {
                    "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
                    "params": [
                        self.address,
                        {"mint": token_address},
                        {"encoding": "jsonParsed"}
                    ]
                }
                response = requests.post(chain_info['rpc'], json=payload).json()
                if 'result' in response and response['result']['value']:
                    # Get the first account found
                    info = response['result']['value'][0]['account']['data']['parsed']['info']
                    return float(info['tokenAmount']['uiAmount'])
                return 0.0
                
        except Exception as e:
            logging.error(f"Error fetching token balance: {e}")
            return 0.0
        return 0.0

    def estimate_gas(self, to_address, amount_eth=0, data=b''):
        """Estimate gas for a transaction (EVM only)"""
        if not self.connected or self.CHAINS.get(self.chain_id, {}).get('type') != 'evm':
            return None
            
        try:
            tx = {
                'to': Web3.to_checksum_address(to_address),
                'value': self.w3.to_wei(amount_eth, 'ether'),
                'from': self.address,
                'data': data
            }
            gas_limit = self.w3.eth.estimate_gas(tx)
            gas_price = self.w3.eth.gas_price
            
            # Return cost in ETH
            return float(self.w3.from_wei(gas_limit * gas_price, 'ether'))
        except Exception as e:
            logging.error(f"Gas estimation failed: {e}")
            return None

    def get_gas_price(self):
        """
        Fetch current gas price/fees for the connected chain.
        Returns a dictionary with formatted fee info.
        """
        if not self.connected:
            return None
            
        chain_info = self.CHAINS.get(self.chain_id, {})
        chain_type = chain_info.get('type', 'evm')
        
        try:
            # 1. EVM Chains
            if chain_type == 'evm':
                try:
                    # Try EIP-1559 (London Hardfork)
                    # Fetching latest block base fee
                    block = self.w3.eth.get_block('latest')
                    base_fee = block.get('baseFeePerGas')
                    
                    if base_fee:
                        # Convert to Gwei
                        base_gwei = float(self.w3.from_wei(base_fee, 'gwei'))
                        
                        # Get Priority Fee (Simple heuristic or RPC call if supported)
                        # maxPriorityFeePerGas is not always directly available via simple call on all RPCs without sending tx
                        # But we can estimate standard priority (e.g. 1.5 Gwei)
                        priority_gwei = 1.5 
                        
                        return {
                            'type': 'EIP-1559',
                            'base_fee_gwei': round(base_gwei, 2),
                            'priority_fee_gwei': priority_gwei,
                            'estimated_cost_gwei': round(base_gwei + priority_gwei, 2),
                            'unit': 'Gwei'
                        }
                    else:
                        raise ValueError("No baseFeePerGas")
                except:
                    # Legacy Fallback
                    gas_price = self.w3.eth.gas_price
                    gwei = float(self.w3.from_wei(gas_price, 'gwei'))
                    return {
                        'type': 'Legacy',
                        'gas_price_gwei': round(gwei, 2),
                        'unit': 'Gwei'
                    }

            # 2. Solana (SVM)
            elif chain_type == 'svm':
                # Solana fees are usually deterministic (5000 lamports) + Priority
                # We can try fetching recent prioritization fees if RPC supports it
                return {
                    'type': 'Solana',
                    'base_fee': 0.000005,
                    'unit': 'SOL',
                    'note': 'Standard Signature Fee'
                }

            # 3. TON (TVM)
            elif chain_type == 'tvm':
                 # TON fees depend on storage + computation
                 return {
                     'type': 'TON',
                     'base_fee': 0.005,
                     'unit': 'TON',
                     'note': 'Estimated Transfer Fee'
                 }
            
            # 4. Tron
            elif chain_type == 'tron':
                 return {
                     'type': 'Tron',
                     'bandwidth': 'Variable',
                     'energy': 'Variable',
                     'note': 'Burn TRX if no Freeze'
                 }
                 
        except Exception as e:
            logging.error(f"Error fetching gas price: {e}")
            return {'error': str(e)}
            
        return None

    def send_transaction(self, to_address, amount, side, symbol="TON"):
        """
        Execute a transaction on the connected chain.
        Supports EVM (Real w/ Key) and TON (Simulated/Optimistic).
        """
        if not self.connected:
            return {"status": "failed", "error": "Wallet not connected"}

        chain_type = self.CHAINS.get(self.chain_id, {}).get('type', 'evm')
        
        # 1. TON (TVM)
        if chain_type == 'tvm':
             # For TON, we require real wallet integration via TonConnect or similar.
             # Simulation/Fake balance updates are disabled.
             logging.info(f"Sending TON Transaction: {side} {amount} {symbol} to {to_address}")
             
             return {
                 "status": "failed", 
                 "error": "Real TON transactions require active wallet integration. Fake execution is disabled."
             }

        # 2. EVM
        elif chain_type == 'evm':
            if not self.private_key:
                 return {"status": "failed", "error": "Read-Only Wallet. Cannot Sign."}
            
            try:
                # Construct Transaction
                tx = {
                    'nonce': self.w3.eth.get_transaction_count(self.address),
                    'to': Web3.to_checksum_address(to_address),
                    'value': self.w3.to_wei(amount, 'ether'),
                    'gas': 21000,
                    'gasPrice': self.w3.eth.gas_price,
                    'chainId': int(self.chain_id)
                }
                
                # Sign
                signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
                
                # Send
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                
                return {
                    "status": "success",
                    "tx_hash": self.w3.to_hex(tx_hash),
                    "message": "Transaction Broadcasted"
                }
            except Exception as e:
                return {"status": "failed", "error": str(e)}
                
        return {"status": "failed", "error": "Chain type not supported for execution"}

    def get_network_name(self):
        return self.CHAINS.get(self.chain_id, {}).get('name', 'Unknown Network')
        
    def get_symbol(self):
        return self.CHAINS.get(self.chain_id, {}).get('symbol', 'ETH')

    def get_short_address(self):
        if self.connected and self.address:
            if self.chain_id == 'solana':
                return f"{self.address[:4]}...{self.address[-4:]}"
            return f"{self.address[:6]}...{self.address[-4:]}"
        return "Not Connected"

    def is_connected(self):
        return self.connected

    def to_wei(self, amount, unit='ether'):
        if self.CHAINS.get(self.chain_id, {}).get('type') == 'evm':
            return self.w3.to_wei(amount, unit)
        return int(amount * 1_000_000_000) # Solana/Lamports approximation

    # --- New Wallet & Utility Features ---
    def generate_wallet(self):
        """Generates a new EVM wallet"""
        account = Account.create()
        return {
            "address": account.address,
            "private_key": account.key.hex(),
            "mnemonic": "N/A (Private Key Only)" 
        }

    def generate_qr_code(self, address: str):
        """Generates a QR code image bytes for the address"""
        if not qrcode:
            return None
            
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(address)
            qr.make(fit=True)
            img = qr.make_image(fill="black", back_color="white")
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            logging.error(f"QR Gen Error: {e}")
            return None

    def scan_all_balances(self, address: str):
        """Scans native balances across all configured chains (EVM, TON, SOL)"""
        results = {}
        
        # Address Type Detection
        is_evm = False
        try:
            is_evm = Web3.is_address(address)
        except: pass
        
        # TON Address Check (Rough)
        # Standard base64url encoded addresses are 48 chars
        is_ton = len(address) == 48 and (address.startswith("EQ") or address.startswith("UQ") or address.startswith("kQ"))
        
        # Solana Address Check (Base58, 32-44 chars usually)
        is_sol = 32 <= len(address) <= 44 and not address.startswith("0x") and not is_ton

        # Tron Address Check (Starts with T, length 34)
        is_tron = len(address) == 34 and address.startswith("T")

        for chain_id, config in self.CHAINS.items():
            chain_type = config.get('type', 'evm')
            chain_name = config['name']
            symbol = config['symbol']
            
            # --- EVM Chains ---
            if chain_type == 'evm':
                if not is_evm:
                    results[chain_name] = "N/A (Invalid Type)"
                    continue
                    
                try:
                    w3_temp = Web3(Web3.HTTPProvider(config['rpc'], request_kwargs={'timeout': 3}))
                    if w3_temp.is_connected():
                        bal_wei = w3_temp.eth.get_balance(Web3.to_checksum_address(address))
                        bal_eth = float(w3_temp.from_wei(bal_wei, 'ether'))
                        results[chain_name] = f"{bal_eth:.4f} {symbol}"
                    else:
                        results[chain_name] = "Connection Failed"
                except Exception:
                    results[chain_name] = "Error"
            
            # --- TON Chain ---
            elif chain_type == 'tvm':
                if not is_ton:
                    results[chain_name] = "N/A (Invalid Type)"
                    continue
                    
                try:
                    # Public API fetch
                    url = f"https://toncenter.com/api/v2/getAddressBalance?address={address}"
                    resp = requests.get(url, timeout=5).json()
                    if resp.get('ok'):
                        val = float(resp['result']) / 1_000_000_000
                        results[chain_name] = f"{val:.4f} {symbol}"
                    else:
                        # Fallback to tonapi.io
                        url2 = f"https://tonapi.io/v2/accounts/{address}"
                        resp2 = requests.get(url2, timeout=5).json()
                        if 'balance' in resp2:
                             val = float(resp2['balance']) / 1_000_000_000
                             results[chain_name] = f"{val:.4f} {symbol}"
                        else:
                             results[chain_name] = "Error"
                except Exception as e:
                    results[chain_name] = f"Error"

            # --- Solana Chain ---
            elif chain_type == 'svm':
                if not is_sol:
                    results[chain_name] = "N/A (Invalid Type)"
                    continue
                    
                try:
                    payload = {
                        "jsonrpc": "2.0", "id": 1, "method": "getBalance",
                        "params": [address]
                    }
                    resp = requests.post(config['rpc'], json=payload, timeout=5).json()
                    if 'result' in resp:
                        val = float(resp['result']['value']) / 1_000_000_000
                        results[chain_name] = f"{val:.4f} {symbol}"
                    else:
                        results[chain_name] = "Error"
                except:
                    results[chain_name] = "Error"

            # --- Tron Chain ---
            elif chain_type == 'tron':
                if not is_tron:
                    results[chain_name] = "N/A (Invalid Type)"
                    continue
                
                try:
                    # Try TronGrid Public API
                    url = f"https://api.trongrid.io/v1/accounts/{address}"
                    resp = requests.get(url, timeout=5).json()
                    if resp.get('success') and resp.get('data'):
                         bal = float(resp['data'][0].get('balance', 0)) / 1_000_000
                         results[chain_name] = f"{bal:.2f} {symbol}"
                    elif resp.get('success') and not resp.get('data'):
                         # Account inactive or 0 balance often returns empty data
                         results[chain_name] = f"0.00 {symbol}"
                    else:
                         results[chain_name] = "Error"
                except:
                     results[chain_name] = "Error"

        return results

    def scan_tokens(self, address: str, token_map: dict = None):
        """
        Scans specific ERC20 tokens across chains.
        token_map: {'ChainName': {'Symbol': 'Address'}}
        """
        if not token_map:
             # Default from user request
             token_map = {
                 'Ethereum': {
                     'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                     'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
                 }
             }
        
        results = {}
        for chain_name, tokens in token_map.items():
            # Find chain config by name
            chain_cfg = next((c for c in self.CHAINS.values() if c['name'] == chain_name), None)
            if not chain_cfg: continue
            
            try:
                w3_temp = Web3(Web3.HTTPProvider(chain_cfg['rpc'], request_kwargs={'timeout': 5}))
                for sym, addr in tokens.items():
                    try:
                        contract = w3_temp.eth.contract(address=Web3.to_checksum_address(addr), abi=self.ERC20_ABI)
                        bal = contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
                        dec = contract.functions.decimals().call()
                        results[f"{sym} ({chain_name})"] = float(bal) / (10**dec)
                    except:
                        results[f"{sym} ({chain_name})"] = 0.0
            except:
                pass
                
        return results

    def get_trc20_balance(self, tron_address: str, contract_address: str):
        """Get TRC-20 Token Balance"""
        if not Tron: return "TronPy not installed"
        
        try:
            client = Tron()
            contract = client.get_contract(contract_address)
            precision = contract.functions.decimals()
            balance = contract.functions.balanceOf(tron_address)
            return float(balance) / (10 ** precision)
        except Exception as e:
            return f"Error: {str(e)}"
