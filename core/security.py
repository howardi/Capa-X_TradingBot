
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
        self.key = self._load_or_generate_key()
        try:
            from cryptography.fernet import Fernet
            self.cipher_suite = Fernet(self.key)
            self.encryption_available = True
        except ImportError:
            print("Cryptography module not found. Falling back to basic obfuscation.")
            self.encryption_available = False

    def _load_or_generate_key(self):
        try:
            from cryptography.fernet import Fernet
            key_path = "secret.key"
            if os.path.exists(key_path):
                with open(key_path, "rb") as key_file:
                    return key_file.read()
            else:
                key = Fernet.generate_key()
                with open(key_path, "wb") as key_file:
                    key_file.write(key)
                return key
        except ImportError:
            return None

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
        Encrypts data using Fernet (AES).
        """
        if self.encryption_available and self.key:
            try:
                encrypted_bytes = self.cipher_suite.encrypt(data.encode())
                return f"enc_aes_{encrypted_bytes.decode()}"
            except Exception as e:
                print(f"Encryption Error: {e}")
                return data
        
        # Fallback to Base64
        try:
            import base64
            encoded = base64.b64encode(data.encode()).decode()
            return f"enc_b64_{encoded}"
        except:
            return data

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        Decrypts data using Fernet (AES) or Base64 fallback.
        """
        try:
            if encrypted_data.startswith("enc_aes_"):
                if self.encryption_available and self.key:
                    encrypted_bytes = encrypted_data.replace("enc_aes_", "").encode()
                    decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
                    return decrypted_bytes.decode()
                else:
                    return "[Encrypted Data - Key Missing]"
            
            elif encrypted_data.startswith("enc_b64_"):
                import base64
                encoded = encrypted_data.replace("enc_b64_", "")
                return base64.b64decode(encoded).decode()
                
            elif encrypted_data.startswith("encrypted_"):
                return encrypted_data.replace("encrypted_", "")
                
            return encrypted_data
        except Exception as e:
            print(f"Decryption Error: {e}")
            return encrypted_data
