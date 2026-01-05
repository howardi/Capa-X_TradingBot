from web3 import Web3
from eth_account import Account
import logging
import requests

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
            'tron': {'name': 'Tron', 'rpc': 'https://api.trongrid.io', 'symbol': 'TRX', 'type': 'tron'},
            'bitcoin': {'name': 'Bitcoin', 'rpc': 'https://blockchain.info', 'symbol': 'BTC', 'type': 'utxo'},
            'litecoin': {'name': 'Litecoin', 'rpc': 'https://api.blockcypher.com/v1/ltc/main', 'symbol': 'LTC', 'type': 'utxo'},
            'dogecoin': {'name': 'Dogecoin', 'rpc': 'https://dogechain.info/api/v1', 'symbol': 'DOGE', 'type': 'utxo'},
            'cosmos': {'name': 'Cosmos Hub', 'rpc': 'https://cosmos-rpc.publicnode.com', 'api': 'https://cosmos-lcd.publicnode.com', 'symbol': 'ATOM', 'type': 'cosmos'}
        }
        
    def add_custom_chain(self, chain_id, rpc_url, name, symbol, chain_type='evm'):
        """Dynamically add a new network configuration"""
        self.CHAINS[str(chain_id)] = {
            'name': name,
            'rpc': rpc_url,
            'symbol': symbol,
            'type': chain_type
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
                
                # Update RPC for EVM
                if self.chain_id in self.CHAINS:
                     self.rpc_url = self.CHAINS[self.chain_id]['rpc']
                     self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
                     
                self.connected = True
                return True
            except Exception:
                # Not a valid EVM key, proceed to address checks
                pass

        if is_private_key:
            return True

        # 2. Treat as Address (Read-Only)
        
        # Handle Solana/SVM Addresses
        if chain_id == 'solana':
            self.chain_id = 'solana'
            self.address = input_str # No checksum for SOL
            self.connected = True
            return True

        # Handle Tron Addresses (Start with T, length 34)
        if chain_id == 'tron':
            if input_str.startswith('T') and len(input_str) == 34:
                self.chain_id = 'tron'
                self.address = input_str
                self.connected = True
                return True
            else:
                logging.warning(f"Invalid Tron address: {input_str}")
                # Fallback allowed for manual
                pass 

        # Handle Bitcoin/UTXO Addresses
        if chain_id in ['bitcoin', 'litecoin', 'dogecoin']:
            self.chain_id = chain_id
            self.address = input_str
            self.connected = True
            return True

        # Handle Cosmos Addresses
        if chain_id == 'cosmos':
            self.chain_id = 'cosmos'
            self.address = input_str
            self.connected = True
            return True

        # Handle TON Addresses
        if chain_id == 'ton':
            self.chain_id = 'ton'
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

            # TON Balance (Basic Mock/Impl)
            elif chain_type == 'tvm':
                # TON requires specific API handling, placeholder for now
                return 0.0

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
        
        return 0.0

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
