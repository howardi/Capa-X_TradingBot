from web3 import Web3
import json
import os
import time

# Standard Uniswap V2 Router ABI (Minimal for getAmountsOut)
UNISWAP_V2_ROUTER_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]')

# ERC20 ABI (Minimal for decimals and transfer)
ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}, {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')

# Common Addresses (Mainnet)
UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

class Web3ArbitrageScanner:
    def __init__(self, rpc_url=None):
        if not rpc_url:
            rpc_url = os.getenv('ETH_RPC_URL', 'https://rpc.ankr.com/eth')
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.router = self.w3.eth.contract(address=UNISWAP_V2_ROUTER, abi=UNISWAP_V2_ROUTER_ABI)
        
    def is_connected(self):
        return self.w3.is_connected()

    def get_token_decimals(self, token_address):
        try:
            token = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            return token.functions.decimals().call()
        except:
            return 18

    def get_uniswap_price(self, token_in, token_out, amount_in=1.0):
        """
        Get price of token_in in terms of token_out via Uniswap V2 Router.
        """
        try:
            if not self.w3.is_connected():
                return None
            
            # Convert addresses to checksum
            token_in = Web3.to_checksum_address(token_in)
            token_out = Web3.to_checksum_address(token_out)
            
            # Get Decimals
            decimals_in = 18 # Simplified, ideal to cache this
            decimals_out = 6 if token_out in [USDT_ADDRESS, USDC_ADDRESS] else 18
            
            amount_in_wei = int(amount_in * (10**decimals_in))
            
            path = [token_in, token_out]
            
            # If direct pair doesn't exist/liquidity low, router might fail or revert
            # Usually we route through WETH if not WETH pair
            if token_in != WETH_ADDRESS and token_out != WETH_ADDRESS:
                path = [token_in, WETH_ADDRESS, token_out]
                
            amounts = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            amount_out_wei = amounts[-1]
            
            price = amount_out_wei / (10**decimals_out)
            return price
        except Exception as e:
            print(f"Web3 Price Error: {e}")
            return None

    def scan_arbitrage(self, symbol, cex_price):
        """
        Compare CEX price with Uniswap price.
        """
        # Map symbol to address (Simplified map)
        token_map = {
            "ETH": WETH_ADDRESS,
            "WETH": WETH_ADDRESS,
            # Add more as needed, or fetch from a token list API
        }
        
        token_address = token_map.get(symbol)
        if not token_address:
            return None # Not in our map
            
        dex_price = self.get_uniswap_price(token_address, USDT_ADDRESS)
        
        if not dex_price:
            return None
            
        diff = dex_price - cex_price
        pct = (diff / cex_price) * 100
        
        return {
            "symbol": symbol,
            "cex_price": cex_price,
            "dex_price": dex_price,
            "difference_pct": pct,
            "opportunity": abs(pct) > 1.5, # 1.5% threshold for gas
            "direction": "Buy CEX, Sell DEX" if pct > 0 else "Buy DEX, Sell CEX"
        }

    def send_crypto(self, symbol, to_address, amount, private_key):
        """
        Send Crypto (ETH or Tokens) to an external address.
        """
        if not self.w3.is_connected():
            return {"error": "Web3 not connected"}

        try:
            account = self.w3.eth.account.from_key(private_key)
            from_address = account.address
            to_address = Web3.to_checksum_address(to_address)
            
            # Check Balance
            if symbol == 'ETH':
                balance_wei = self.w3.eth.get_balance(from_address)
                amount_wei = self.w3.to_wei(amount, 'ether')
                if balance_wei < amount_wei:
                    return {"error": "Insufficient ETH balance in bot wallet"}
                
                # Build Transaction
                tx = {
                    'nonce': self.w3.eth.get_transaction_count(from_address),
                    'to': to_address,
                    'value': amount_wei,
                    'gas': 21000,
                    'gasPrice': self.w3.eth.gas_price,
                    'chainId': 1 # Mainnet (Change for Testnet/L2)
                }
                
                # Sign and Send
                signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                return {"status": "success", "tx_hash": self.w3.to_hex(tx_hash)}

            elif symbol == 'USDT':
                # ERC20 Transfer
                contract = self.w3.eth.contract(address=USDT_ADDRESS, abi=ERC20_ABI)
                
                # Get Decimals (USDT is usually 6)
                decimals = 6 
                try:
                    decimals = contract.functions.decimals().call()
                except:
                    pass
                    
                amount_units = int(amount * (10**decimals))
                
                # Build Transaction
                # Note: USDT on Mainnet doesn't always return bool, but standard ERC20 does. 
                # Using build_transaction is safer.
                tx = contract.functions.transfer(to_address, amount_units).build_transaction({
                    'chainId': 1,
                    'gas': 100000, # Estimate or hardcode buffer
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(from_address),
                })
                
                # Sign and Send
                signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                return {"status": "success", "tx_hash": self.w3.to_hex(tx_hash)}
                
            else:
                return {"error": f"Sending {symbol} not supported yet"}

        except Exception as e:
            return {"error": str(e)}

# Singleton instance
arbitrage_scanner = Web3ArbitrageScanner()
