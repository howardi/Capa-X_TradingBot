import sys
import os
import json
import secrets
import hashlib
from datetime import datetime

# Add root to path
sys.path.append(os.getcwd())

from core.auth import AuthManager

def generate_seed(username, password, email):
    # Initialize AuthManager (will create empty DB if not exists)
    # We use a temporary directory to avoid messing with real local DB if needed, 
    # but here we want to generate a JSON object to save to a file.
    
    # Actually, we can just use the internal hashing method of AuthManager
    # But AuthManager is tied to a file.
    # Let's just instantiate it, use the _hash_password method.
    
    auth = AuthManager()
    salt, hashed_pw = auth._hash_password(password)
    
    user_data = {
        "email": email,
        "salt": salt,
        "password_hash": hashed_pw,
        "role": "admin",
        "2fa_enabled": False,
        "2fa_secret": None,
        "created_at": str(datetime.now()),
        "last_login": None,
        "settings": {
            "theme": "dark",
            "notifications_enabled": True
        }
    }
    
    seed_data = {
        username: user_data
    }
    
    output_path = os.path.join("data", "users", "cloud_users_seed.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(seed_data, f, indent=4)
        
    print(f"✅ Generated seed file at {output_path}")
    print(f"User: {username}")
    print(f"Pass: {password}")

if __name__ == "__main__":
    username = "admin"
    # Generate a random secure password
    password = secrets.token_urlsafe(12) 
    email = "admin@caparox.com"
    
    generate_seed(username, password, email)
