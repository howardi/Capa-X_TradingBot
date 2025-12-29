
import os
import hashlib
import hmac
import time
import json
from typing import Dict, Optional, List

class SecurityManager:
    """
    Handles security, authentication, and infrastructure safety.
    """
    def __init__(self):
        self.whitelist_ips = []
        self.api_key_hashes = {}
        self.session_tokens = {}

    def hash_api_key(self, api_key: str) -> str:
        """Securely hash API keys for storage/comparison"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def validate_request(self, api_key: str, signature: str, params: Dict) -> bool:
        """
        Validate incoming requests (e.g., from a webhook) using HMAC signature.
        """
        if not api_key or not signature:
            return False
            
        # Reconstruct payload string
        payload = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        
        # Calculate expected signature
        # In a real scenario, use the secret associated with the API key
        secret = "YOUR_WEBHOOK_SECRET" 
        expected_sig = hmac.new(
            secret.encode(), 
            payload.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)

    def check_ip_whitelist(self, ip_address: str) -> bool:
        """Check if IP is allowed"""
        if not self.whitelist_ips:
            return True # Open if no whitelist defined
        return ip_address in self.whitelist_ips

    def cold_wallet_transfer_check(self, amount: float, threshold: float = 10000.0) -> bool:
        """
        Simulates a check for large transfers requiring manual approval 
        or multi-sig (Infrastructure safety).
        """
        if amount > threshold:
            print(f"SECURITY ALERT: Large transfer ({amount}) detected. Requiring Multi-Sig/Cold Wallet confirmation.")
            return False # Block auto-transfer
        return True

    def encrypt_sensitive_data(self, data: str) -> str:
        """
        Placeholder for encryption logic (e.g., using Fernet/AES).
        """
        # In production, use a proper encryption library like cryptography
        return f"encrypted_{data}"

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        Placeholder for decryption logic.
        """
        if encrypted_data.startswith("encrypted_"):
            return encrypted_data.replace("encrypted_", "")
        return encrypted_data
