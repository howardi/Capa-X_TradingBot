import json
import hashlib
import time
import os
from typing import Dict, List, Optional

class TransparencyLog:
    """
    Manages immutable trade logs and on-chain transparency.
    Simulates interaction with IPFS/Arweave and Chainlink Oracles.
    """
    
    def __init__(self, storage_path: str = "audit_log.json"):
        self.storage_path = storage_path
        self.logs = self._load_logs()
        
    def _load_logs(self) -> List[Dict]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_logs(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.logs, f, indent=4)

    def log_trade(self, trade_data: Dict) -> Dict:
        """
        Logs a trade with a cryptographic hash, simulating on-chain storage.
        """
        timestamp = time.time()
        
        # Create a canonical string representation for hashing
        data_string = json.dumps(trade_data, sort_keys=True)
        
        # Calculate SHA-256 Hash (Simulating Content ID / IPFS Hash)
        tx_hash = hashlib.sha256(f"{timestamp}{data_string}".encode()).hexdigest()
        
        # Simulate IPFS CID (Content Identifier)
        ipfs_cid = f"Qm{tx_hash[:44]}" 
        
        log_entry = {
            "timestamp": timestamp,
            "hash": tx_hash,
            "ipfs_cid": ipfs_cid,
            "data": trade_data,
            "status": "verified",
            "storage_network": "IPFS (Simulated)"
        }
        
        self.logs.append(log_entry)
        self._save_logs()
        
        return log_entry

    def verify_log(self, ipfs_cid: str) -> bool:
        """
        Verify the integrity of a log entry.
        """
        for log in self.logs:
            if log['ipfs_cid'] == ipfs_cid:
                # Reconstruct hash to verify
                data_string = json.dumps(log['data'], sort_keys=True)
                recalc_hash = hashlib.sha256(f"{log['timestamp']}{data_string}".encode()).hexdigest()
                return recalc_hash == log['hash']
        return False

    def get_latest_logs(self, limit: int = 10) -> List[Dict]:
        return sorted(self.logs, key=lambda x: x['timestamp'], reverse=True)[:limit]

class OracleManager:
    """
    Simulates Chainlink Oracle interactions for verifiable price feeds.
    """
    
    @staticmethod
    def get_price_feed(asset: str, chain: str) -> float:
        """
        Get price from 'Chainlink Oracle' (Simulated).
        """
        # In a real app, this would call a smart contract:
        # price_feed = web3.eth.contract(address=addr, abi=abi)
        # return price_feed.functions.latestRoundData().call()
        
        # Simulated Prices
        prices = {
            "ETH": 2250.00,
            "BTC": 42000.00,
            "SOL": 95.00,
            "BNB": 310.00,
            "AVAX": 35.00
        }
        return prices.get(asset, 0.0)
