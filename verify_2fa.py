import time
from core.auth import TOTP, AuthManager
import os
import shutil

def test_totp_flow():
    print("Testing TOTP Logic...")
    
    # 1. Generate Secret
    secret = TOTP.generate_secret()
    print(f"Generated Secret: {secret}")
    assert len(secret) > 10
    
    # 2. Generate Token
    token = TOTP.get_totp_token(secret)
    print(f"Generated Token: {token}")
    assert len(token) == 6
    assert token.isdigit()
    
    # 3. Verify Token
    is_valid = TOTP.verify_totp(secret, token)
    print(f"Verification Result: {is_valid}")
    assert is_valid == True
    
    # 4. Verify Invalid Token
    is_valid_bad = TOTP.verify_totp(secret, "000000")
    print(f"Invalid Token Result: {is_valid_bad}")
    assert is_valid_bad == False
    
    print("TOTP Logic Passed!")

def test_auth_manager_2fa():
    print("\nTesting AuthManager 2FA Flow...")
    
    # Setup
    if os.path.exists("data/test_users_2fa"):
        shutil.rmtree("data/test_users_2fa")
        
    auth = AuthManager(data_dir="data/test_users_2fa")
    username = "2fa_tester"
    password = "password123"
    auth.register_user(username, password, "test@example.com")
    
    # 1. Login (No 2FA)
    success, user = auth.login_user(username, password)
    assert success
    assert user['2fa_enabled'] == False
    
    # 2. Enable 2FA
    secret = TOTP.generate_secret()
    token = TOTP.get_totp_token(secret)
    
    # Try enabling with wrong code
    success, msg = auth.enable_2fa(username, secret, "000000")
    assert not success
    
    # Enable with correct code
    success, msg = auth.enable_2fa(username, secret, token)
    assert success
    print("2FA Enabled Successfully")
    
    # Verify User State
    auth._load_users() # Reload to be sure
    assert auth.users[username]['2fa_enabled'] == True
    assert auth.users[username]['2fa_secret'] == secret
    
    # 3. Login with 2FA
    # First step: Credential check
    success, user = auth.login_user(username, password)
    assert success
    assert user['2fa_enabled'] == True
    
    # Second step: 2FA verify
    token_new = TOTP.get_totp_token(secret)
    success = auth.verify_2fa_login(username, token_new)
    assert success
    print("2FA Login Verified")
    
    # 4. Disable 2FA
    success, msg = auth.disable_2fa(username, "wrong_password")
    assert not success
    
    success, msg = auth.disable_2fa(username, password)
    assert success
    print("2FA Disabled Successfully")
    
    auth._load_users()
    assert auth.users[username]['2fa_enabled'] == False
    assert auth.users[username]['2fa_secret'] == None
    
    print("AuthManager 2FA Flow Passed!")
    
    # Cleanup
    if os.path.exists("data/test_users_2fa"):
        shutil.rmtree("data/test_users_2fa")

if __name__ == "__main__":
    test_totp_flow()
    test_auth_manager_2fa()
