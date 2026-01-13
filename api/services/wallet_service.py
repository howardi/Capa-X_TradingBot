import json
import os
import time
from eth_account import Account
from web3 import Web3
try:
    from tronpy import Tron
    from tronpy.keys import PrivateKey
except ImportError:
    Tron = None

try:
    from tonsdk.contract.wallet import Wallets, WalletVersionEnum
    from tonsdk.utils import bytes_to_b64str, to_nano
    from tonsdk.crypto import mnemonic_new, mnemonic_to_wallet_key
    from tonsdk.boc import Cell
    ton_support = True
except ImportError:
    ton_support = False

try:
    from bit import Key
    from bit.network import NetworkAPI
    bit_support = True
except ImportError:
    bit_support = False

from api.db import get_db_connection

class WalletService:
    def __init__(self):
        # In production, use a proper KMS or secret manager
        self.encryption_key = os.getenv('WALLET_ENCRYPTION_KEY', 'default-insecure-key-change-me')
        # Load RPCs from Env or Default
        self.rpcs = {
            'EVM': os.getenv('RPC_EVM', 'https://mainnet.infura.io/v3/YOUR-PROJECT-ID'),
            'Ethereum': os.getenv('RPC_ETH', 'https://mainnet.infura.io/v3/YOUR-PROJECT-ID'),
            'BSC': os.getenv('RPC_BSC', 'https://bsc-dataseed.binance.org/'),
            'SmartChain': os.getenv('RPC_BSC', 'https://bsc-dataseed.binance.org/'),
            'POLYGON': os.getenv('RPC_POLYGON', 'https://polygon-rpc.com'),
            'TRON': os.getenv('RPC_TRON', 'https://api.trongrid.io'),
            'TON': os.getenv('RPC_TON', 'https://toncenter.com/api/v2/jsonRPC')
        }
        self.contracts = {
            'USDT': {
                'Ethereum': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                'BSC': '0x55d398326f99059fF775485246999027B3197955',
                'TRON': 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
            }
        }
        # ERC20 ABI for transfer
        self.erc20_abi = [
            {
                "constant": False,
                "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]

    def _send_evm_transaction(self, private_key, to_address, amount, currency, chain):
        rpc_url = self.rpcs.get(chain) or self.rpcs.get('EVM')
        if not rpc_url:
            return None, "Chain RPC not found"
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not w3.is_connected():
                 return None, "RPC Connection failed"

            acct = w3.eth.account.from_key(private_key)
            
            # Check Balance (Gas)
            eth_balance = w3.eth.get_balance(acct.address)
            gas_price = w3.eth.gas_price
            
            if currency == 'USDT' or currency in self.contracts:
                # Token Transfer
                contract_address = self.contracts.get(currency, {}).get(chain)
                if not contract_address:
                    return None, f"Contract for {currency} on {chain} not found"
                
                contract = w3.eth.contract(address=contract_address, abi=self.erc20_abi)
                # Decimals? USDT is 6 on ETH, 18 on BSC usually? 
                # Simplification: Assume 18 or check. USDT ETH is 6.
                decimals = 6 if currency == 'USDT' and chain == 'Ethereum' else 18
                amount_wei = int(amount * (10 ** decimals))
                
                # Build Tx
                tx = contract.functions.transfer(to_address, amount_wei).build_transaction({
                    'from': acct.address,
                    'nonce': w3.eth.get_transaction_count(acct.address),
                    'gas': 100000, # Estimate?
                    'gasPrice': gas_price
                })
            else:
                # Native Transfer
                amount_wei = w3.to_wei(amount, 'ether')
                if eth_balance < amount_wei + (21000 * gas_price):
                     return None, "Insufficient native balance for gas + amount"

                tx = {
                    'nonce': w3.eth.get_transaction_count(acct.address),
                    'to': to_address,
                    'value': amount_wei,
                    'gas': 21000,
                    'gasPrice': gas_price,
                    'chainId': w3.eth.chain_id
                }
            
            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return w3.to_hex(tx_hash), None
        except Exception as e:
            return None, str(e)

    def _send_btc_transaction(self, private_key, to_address, amount, currency):
        if not bit_support:
            return None, "Bitcoin support not installed (bit library)"
        if currency != 'BTC':
            return None, "Only BTC supported on Bitcoin chain"
            
        try:
            key = Key(private_key)
            # amount in BTC, convert to satoshi? bit handles it usually if using send?
            # key.send expects list of (address, amount, currency) tuples or just direct
            # amount defaults to satoshi if int, or use string/decimal for BTC?
            # bit documentation says: key.send([('address', 0.001, 'btc')])
            
            tx_hash = key.send([(to_address, amount, 'btc')])
            return tx_hash, None
        except Exception as e:
            return None, f"Bitcoin Transaction Failed: {str(e)}"

    def generate_wallet(self, username, chain='EVM'):
        """Generates a new wallet for the user."""
        address = None
        private_key = None
        chain_type = chain
        
        if chain in ['EVM', 'SmartChain', 'Ethereum', 'BSC', 'POLYGON']:
            # Generate EVM Account
            acct = Account.create()
            address = acct.address
            private_key = acct._private_key.hex()
            chain_type = 'EVM' # Normalize
        elif chain.upper() == 'TRON':
            if not Tron:
                return {"error": "Tron support not installed"}
            # Generate Tron Account
            try:
                # Local generation without node connection
                priv = PrivateKey.random()
                address = priv.public_key.to_base58check_address()
                private_key = priv.hex()
                chain_type = 'TRON'
            except Exception as e:
                return {"error": f"Tron generation failed: {str(e)}"}
        elif chain.upper() == 'TON':
            if not ton_support:
                return {"error": "TON support not installed (tonsdk)"}
            try:
                mnemonics = mnemonic_new()
                _pub, _priv, _wallet = Wallets.from_mnemonics(mnemonics=mnemonics, version=WalletVersionEnum.v4r2, workchain=0)
                
                address = _wallet.address.to_string(True, True, True) # user_friendly, url_safe, bounceable
                private_key = " ".join(mnemonics) # Store mnemonic for TON as it's standard for reconstruction
                chain_type = 'TON'
            except Exception as e:
                return {"error": f"TON generation failed: {str(e)}"}
        elif chain.upper() == 'BTC' or chain.upper() == 'BITCOIN':
            if not bit_support:
                return {"error": "Bitcoin support not installed"}
            try:
                key = Key() # Generates new random key
                address = key.address
                private_key = key.to_wif() # WIF is standard for storage
                chain_type = 'BTC'
            except Exception as e:
                return {"error": f"Bitcoin generation failed: {str(e)}"}
        else:
            return {"error": f"Chain {chain} not supported"}

        # Store in DB
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            # Check if exists
            c.execute("SELECT address FROM wallets WHERE username=? AND type=?", (username, chain_type))
            existing = c.fetchone()
            if existing:
                return {"address": existing['address'], "type": chain_type, "message": "Wallet already exists"}
                
            # Insert
            # TODO: Encrypt private_key before storing!
            c.execute("INSERT INTO wallets (username, type, name, address, private_key, balance) VALUES (?, ?, ?, ?, ?, ?)",
                      (username, chain_type, f'{chain} Wallet', address, private_key, 0.0))
            conn.commit()
            
            return {
                "address": address,
                "private_key": private_key,
                "type": chain_type,
                "message": "Wallet generated successfully"
            }
        except Exception as e:
            conn.rollback()
            return {"error": str(e)}
        finally:
            conn.close()

    def get_user_wallets(self, username):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, type, name, address, balance FROM wallets WHERE username=?", (username,))
        wallets = [dict(row) for row in c.fetchall()]
        conn.close()
        return wallets
    
    def get_private_key(self, username, chain_type):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT private_key FROM wallets WHERE username=? AND type=?", (username, chain_type))
        row = c.fetchone()
        conn.close()
        if row:
            return row['private_key']
        return None

    def _send_tron_transaction(self, private_key, to_address, amount, currency):
        if not Tron:
             return None, "Tron support not installed"
        try:
            client = Tron() # Defaults to mainnet
            priv = PrivateKey(bytes.fromhex(private_key))
            
            if currency == 'USDT':
                cntr = client.get_contract("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
                txn = (
                    cntr.functions.transfer(to_address, int(amount * 1_000_000))
                    .with_owner(priv.public_key.to_base58check_address())
                    .fee_limit(10_000_000)
                    .build()
                    .sign(priv)
                )
                res = txn.broadcast()
                return res.get('txid'), None
            elif currency == 'TRX':
                txn = (
                    client.trx.transfer(priv.public_key.to_base58check_address(), to_address, int(amount * 1_000_000))
                    .build()
                    .sign(priv)
                )
                res = txn.broadcast()
                return res.get('txid'), None
            else:
                return None, "Unsupported currency on Tron"
        except Exception as e:
            return None, str(e)

    def _send_ton_transaction(self, mnemonics_str, to_address, amount, currency):
        if not ton_support:
            return None, "TON support not installed"
        
        try:
            mnemonics = mnemonics_str.split()
            _pub, _priv, wallet = Wallets.from_mnemonics(mnemonics=mnemonics, version=WalletVersionEnum.v4r2, workchain=0)
            
            # 1. Get Seqno from API
            rpc_url = self.rpcs.get('TON') or "https://toncenter.com/api/v2/jsonRPC"
            
            # Check for API Key
            ton_api_key = os.getenv('TON_API_KEY')
            headers = {"Content-Type": "application/json"}
            if ton_api_key:
                headers["X-API-Key"] = ton_api_key
                
            # Get Seqno
            payload = {
                "id": "1",
                "jsonrpc": "2.0",
                "method": "runGetMethod",
                "params": {
                    "address": wallet.address.to_string(True, True, True),
                    "method": "seqno",
                    "stack": []
                }
            }
            
            resp = requests.post(rpc_url, json=payload, headers=headers, timeout=10)
            data = resp.json()
            
            seqno = 0
            if 'result' in data and 'stack' in data['result']:
                # Parse stack for seqno (usually first item, type 'num')
                # Format: [['num', '0x...']]
                stack = data['result']['stack']
                if stack and stack[0][0] == 'num':
                    seqno = int(stack[0][1], 16)
                    
            # 2. Build Transfer
            if currency == 'TON':
                query = wallet.create_transfer_message(
                    to_addr=to_address,
                    amount=to_nano(amount, 'ton'),
                    seqno=seqno,
                    payload="CapaRox Withdrawal"
                )
            elif currency == 'USDT':
                # USDT on TON (Jetton)
                # This requires Jetton Wallet interaction, which is complex.
                # For now, we only support Native TON transfer fully, log error for Jetton.
                return None, "USDT on TON automated transfer not yet implemented (requires Jetton Wallet)"
            else:
                return None, f"Currency {currency} not supported on TON"
            
            # 3. Send BOC
            boc = bytes_to_b64str(query["message"].to_boc(False))
            
            send_payload = {
                "id": "1",
                "jsonrpc": "2.0",
                "method": "sendBoc",
                "params": {"boc": boc}
            }
            
            send_resp = requests.post(rpc_url, json=send_payload, headers=headers, timeout=10)
            send_data = send_resp.json()
            
            if 'result' in send_data:
                # result is usually the status code or type, not a hash directly in v2
                # But typically returns 200 OK. Hash isn't always returned in body.
                # We can assume success if no error.
                return "pending_ton_tx", None 
            elif 'error' in send_data:
                return None, f"TON Send Error: {send_data['error']}"
                
            return "pending_ton_tx", None
            
        except Exception as e:
            return None, str(e)

    def withdraw_crypto(self, username, amount, currency, to_address, chain='EVM'):
        """
        Withdraws crypto from internal balance to external address.
        """
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            # Check Balance
            c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (username, currency))
            row = c.fetchone()
            if not row or row['balance'] < amount:
                return {"error": "Insufficient balance"}
            
            # Deduct Internal Ledger (Optimistic)
            c.execute("UPDATE live_balances SET balance = balance - ? WHERE username=? AND currency=?", (amount, username, currency))
            
            tx_hash = None
            status = 'processing'
            
            # Attempt Real Transfer
            # Find Wallet
            # Map chain names to types stored in DB
            db_chain_type = 'EVM'
            if chain.upper() == 'TRON':
                db_chain_type = 'TRON'
            elif chain.upper() == 'TON':
                db_chain_type = 'TON'
            elif chain.upper() in ['BTC', 'BITCOIN']:
                db_chain_type = 'BTC'
            
            c.execute("SELECT private_key, address FROM wallets WHERE username=? AND type=?", (username, db_chain_type))
            wallet_row = c.fetchone()
            
            error_msg = None
            
            if wallet_row:
                private_key = wallet_row['private_key']
                if db_chain_type == 'EVM':
                    tx_hash, error_msg = self._send_evm_transaction(private_key, to_address, amount, currency, chain)
                elif db_chain_type == 'TRON':
                    tx_hash, error_msg = self._send_tron_transaction(private_key, to_address, amount, currency)
                elif db_chain_type == 'TON':
                    tx_hash, error_msg = self._send_ton_transaction(private_key, to_address, amount, currency)
                elif db_chain_type == 'BTC':
                    tx_hash, error_msg = self._send_btc_transaction(private_key, to_address, amount, currency)
                else:
                    error_msg = "Chain automated withdrawal not supported"
            else:
                error_msg = "No wallet found for automated withdrawal"

            if tx_hash:
                status = 'completed'
                message = f"Sent {amount} {currency} to {to_address}"
            else:
                status = 'manual_check'
                message = f"Withdrawal recorded. Manual processing required. Reason: {error_msg}"
                # Note: We do NOT refund here automatically to avoid double spend if error was ambiguous (timeout).
                # Admin must verify.

            # Log Transaction
            tx_ref = tx_hash if tx_hash else f"tx_{int(time.time())}"
            c.execute("INSERT INTO transactions (username, type, currency, amount, status, tx_ref) VALUES (?, ?, ?, ?, ?, ?)",
                      (username, 'withdrawal', currency, amount, status, tx_ref))
            
            conn.commit()
            return {"status": status, "tx_hash": tx_hash, "message": message}
            
        except Exception as e:
            conn.rollback()
            return {"error": str(e)}
        finally:
            conn.close()

    def swap_currency(self, username, from_currency, to_currency, amount):
        """
        Swaps one currency for another using internal rates.
        """
        conn = get_db_connection()
        c = conn.cursor()
        
        # Mock Rates
        rates = {
            "USDT": 1.0,
            "NGN": 1650.0, # 1 USDT = 1650 NGN
        }
        
        try:
            # Check Balance
            c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (username, from_currency))
            row = c.fetchone()
            if not row or row['balance'] < amount:
                return {"error": f"Insufficient {from_currency} balance"}

            # Get Rates
            rate = 1.0
            if from_currency == 'USDT' and to_currency == 'NGN':
                rate = 1650.0
            elif from_currency == 'NGN' and to_currency == 'USDT':
                rate = 1.0 / 1650.0
            else:
                 return {"error": "Pair not supported"}
            
            receive_amount = amount * rate
            
            # Update Balances
            c.execute("UPDATE live_balances SET balance = balance - ? WHERE username=? AND currency=?", (amount, username, from_currency))
            
            # Check if destination account exists
            c.execute("SELECT balance FROM live_balances WHERE username=? AND currency=?", (username, to_currency))
            dest = c.fetchone()
            if dest:
                c.execute("UPDATE live_balances SET balance = balance + ? WHERE username=? AND currency=?", (receive_amount, username, to_currency))
            else:
                 c.execute("INSERT INTO live_balances (username, currency, balance) VALUES (?, ?, ?)", (username, to_currency, receive_amount))
                 
            # Log
            c.execute("INSERT INTO transactions (username, type, currency, amount, status, tx_ref) VALUES (?, ?, ?, ?, ?, ?)",
                      (username, 'swap', f"{from_currency}_{to_currency}", amount, 'completed', f"swap_{int(time.time())}"))
            
            conn.commit()
            return {"status": "success", "from": from_currency, "to": to_currency, "sent": amount, "received": receive_amount}
            
        except Exception as e:
            conn.rollback()
            return {"error": str(e)}
        finally:
            conn.close()

    def get_onchain_balance(self, address, currency, chain='EVM'):
        """
        Fetches the real on-chain balance of an address.
        """
        rpc_url = self.rpcs.get(chain)
        if not rpc_url and chain != 'BTC': return 0.0
        
        try:
            if chain in ['EVM', 'Ethereum', 'BSC', 'SmartChain', 'POLYGON']:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                if not w3.is_connected(): return 0.0
                
                if currency == 'USDT' or currency in self.contracts:
                    contract_address = self.contracts.get(currency, {}).get(chain)
                    if not contract_address: return 0.0
                    contract = w3.eth.contract(address=contract_address, abi=self.erc20_abi)
                    # Decimals again
                    decimals = 6 if currency == 'USDT' and chain == 'Ethereum' else 18
                    raw_balance = contract.functions.balanceOf(address).call()
                    return raw_balance / (10 ** decimals)
                else:
                    # Native
                    wei = w3.eth.get_balance(address)
                    return w3.from_wei(wei, 'ether')
            
            elif chain == 'TRON' and Tron:
                client = Tron() # Uses default grid
                if currency == 'USDT':
                     cntr = client.get_contract("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
                     # Tronpy logic for balance?
                     # Standard TRC20 balanceOf
                     return float(cntr.functions.balanceOf(address)) / 1_000_000
                elif currency == 'TRX':
                    return float(client.get_account_balance(address))
            
            elif chain == 'TON':
                # Basic TON Balance Check using Toncenter API
                try:
                    payload = {
                        "id": "1",
                        "jsonrpc": "2.0",
                        "method": "getAddressBalance",
                        "params": {"address": address}
                    }
                    headers = {"Content-Type": "application/json"}
                    # Check for API Key if provided in env
                    ton_api_key = os.getenv('TON_API_KEY')
                    if ton_api_key:
                        headers["X-API-Key"] = ton_api_key
                        
                    resp = requests.post(rpc_url, json=payload, headers=headers, timeout=10)
                    data = resp.json()
                    
                    if 'result' in data:
                        # Balance is in nanotons (10^9)
                        nanotons = int(data['result'])
                        return nanotons / 1_000_000_000
                    else:
                        print(f"TON API Error: {data}")
                        return 0.0
                except Exception as e:
                    print(f"TON Balance Check Failed: {e}")
                    return 0.0
            elif chain in ['BTC', 'BITCOIN'] and bit_support:
                try:
                    # Bit library has network_api
                    # or Key(address).balance ? Key needs private key usually.
                    # bit.network.NetworkAPI.get_balance(address)
                    balance_satoshi = NetworkAPI.get_balance(address)
                    return float(balance_satoshi) / 100_000_000
                except Exception as e:
                     print(f"BTC Balance Check Failed: {e}")
                     return 0.0

            return 0.0
        except Exception as e:
            print(f"Error fetching onchain balance: {e}")
            return 0.0

    def _get_chain_type(self, chain):
        if chain in ['EVM', 'SmartChain', 'Ethereum', 'BSC', 'POLYGON']:
             return 'EVM'
        if chain in ['BTC', 'BITCOIN']:
             return 'BTC'
        return chain.upper()

    def interact_with_contract(self, username, chain, contract_address, abi, function_name, params):
        """
        Interacts with a smart contract (Read/Write).
        Requires a wallet to be present for the user.
        """
        conn = get_db_connection()
        c = conn.cursor()
        
        chain_type = self._get_chain_type(chain)
        c.execute("SELECT private_key FROM wallets WHERE username=? AND type=?", (username, chain_type)) 
        row = c.fetchone()
        conn.close()
        
        if not row:
            return {"error": f"No {chain_type} wallet found for user"}
            
        private_key = row['private_key']
        rpc_url = self.rpcs.get(chain) or self.rpcs.get('EVM')
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not w3.is_connected():
                return {"error": "Could not connect to RPC"}
                
            contract = w3.eth.contract(address=contract_address, abi=abi)
            func = getattr(contract.functions, function_name)
            
            # Check if view or transaction
            # Simplified: assume transaction if private key needed, but we can't know without ABI inspection easily.
            # Let's try to build a transaction.
            
            acct = w3.eth.account.from_key(private_key)
            
            # Build Tx
            tx = func(*params).build_transaction({
                'from': acct.address,
                'nonce': w3.eth.get_transaction_count(acct.address),
                'gas': 2000000,
                'gasPrice': w3.eth.gas_price
            })
            
            # Sign
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
            
            # Send
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return {"status": "success", "tx_hash": w3.to_hex(tx_hash)}
            
        except Exception as e:
            return {"error": f"Smart Contract Interaction Failed: {str(e)}"}
