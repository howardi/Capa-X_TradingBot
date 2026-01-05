import time
import random
import json
import logging
from datetime import datetime

class TonConnectManager:
    """
    Manages Telegram Wallet (TON) connectivity via TON Connect 2.0 protocol simulation.
    In a production environment with 'pytonconnect' installed, this would interface with the actual bridge.
    """
    
    def __init__(self):
        self.manifest_url = "https://caparox.app/tonconnect-manifest.json"
        self.bridge_url = "https://bridge.tonapi.io/bridge"
        self.wallets_list = [
            {"name": "Telegram Wallet", "image": "https://wallet.tg/images/logo-288.png", "app_name": "telegram-wallet"},
            {"name": "Tonkeeper", "image": "https://tonkeeper.com/assets/tonkeeper.png", "app_name": "tonkeeper"},
            {"name": "MyTonWallet", "image": "https://mytonwallet.io/icon-256.png", "app_name": "mytonwallet"}
        ]
        # Store balances for simulation (Address -> {TON: float, USDT: float})
        self.balances = {}

        
    def get_wallets(self):
        """Return supported wallets"""
        return self.wallets_list

    def generate_connect_request(self):
        """
        Generates a connection request payload and QR code data.
        Returns: (connect_url, session_id)
        """
        session_id = f"sess_{int(time.time())}_{random.randint(1000,9999)}"
        
        # Simulate a TON Connect 2.0 Deep Link
        # Real format: tc://?v=2&id={session_id}&r={request_payload}&ret=back
        connect_url = f"https://app.tonkeeper.com/ton-connect?v=2&id={session_id}&r=%7B%22manifestUrl%22%3A%22https%3A%2F%2Fcaparox.app%2Ftonconnect-manifest.json%22%2C%22items%22%3A%5B%7B%22name%22%3A%22ton_addr%22%7D%5D%7D"
        
        # Telegram Desktop / Web Link
        tg_link = f"https://t.me/wallet?startattach=tonconnect-{session_id}"

        return {
            "session_id": session_id,
            "connect_url": connect_url,
            "tg_link": tg_link,
            "expiry": time.time() + 300, # 5 minutes
            "status": "pending"
        }

    def check_connection_status(self, session_id):
        """
        Simulates checking the bridge for a user approval.
        In a real app, this would poll the bridge or wait for a callback.
        """
        # We simulate a "success" if the user clicks "I've Approved" in the UI
        # or randomly after some time if we were fully async.
        # For this implementation, we'll rely on a manual trigger in the UI for the simulation.
        pass

    def mock_approve_connection(self):
        """
        Simulates a successful wallet connection response.
        """
        # Generate a random realistic TON address
        # EQ... (48 chars)
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        addr_hash = "".join(random.choice(chars) for _ in range(43))
        address = f"EQB{addr_hash}"
        
        return {
            "address": address,
            "chain": "-239", # Mainnet
            "wallet_type": "tonkeeper",
            "public_key": "simulated_pub_key",
            "connected_at": time.time()
        }

    def get_balance(self, address):
        """
        Fetch balance for the connected address.
        Tries to fetch REAL balance from tonapi.io, falls back to simulation.
        """
        # Return existing simulated/cached balance if available and modified
        # Note: If we want to refresh real balance, we might need a force_refresh flag.
        # For now, let's prioritize cached if it exists to preserve "trading" updates in simulation.
        if address in self.balances:
            return self.balances[address]

        # Try to fetch REAL balance
        try:
            # tonapi.io v2 API (public)
            url = f"https://tonapi.io/v2/accounts/{address}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # Balance is in nanoton
                real_balance = int(data.get('balance', 0)) / 1e9
                
                # Fetch USDT Balance (Jetton) - simplified, maybe just fetch TON for now
                # Or mock USDT if real TON found
                usdt_balance = 0.0
                
                # Store
                self.balances[address] = {
                    "TON": round(real_balance, 4),
                    "USDT": round(usdt_balance, 2)
                }
                return self.balances[address]
        except Exception as e:
            logging.warning(f"Failed to fetch real TON balance: {e}")

        # Fallback: Simulate fetching from TON API
        # Random balance between 10 and 5000 TON
        # Seed with address to be consistent
        random.seed(address)
        balance = random.uniform(10.5, 5000.0)
        usdt_balance = random.uniform(0, 20000.0)
        random.seed() # Reset
        
        # Store for session
        self.balances[address] = {
            "TON": round(balance, 4),
            "USDT": round(usdt_balance, 2)
        }
        
        return self.balances[address]

    def estimate_gas(self, transaction_type):
        """
        Estimate gas fees for a transaction.
        """
        if transaction_type == "swap":
            return 0.08 + random.uniform(0, 0.05)
        elif transaction_type == "transfer":
            return 0.005 + random.uniform(0, 0.002)
        return 0.01

    def sign_transaction(self, tx_details):
        """
        Simulate the transaction signing process.
        """
        # In reality, this sends a request to the wallet app via the bridge
        return {
            "status": "signed",
            "tx_hash": f"boc_{int(time.time())}_{random.randint(10000,99999)}",
            "fee": self.estimate_gas("swap")
        }

