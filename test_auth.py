import requests
import time
import os
import sys

# Ensure we are testing the local running instance
BASE_URL = "http://localhost:5000/api"

def test_auth():
    print("--- Testing Auth Routes ---")
    
    # 1. Register
    username = f"testuser_{int(time.time())}"
    email = f"{username}@example.com"
    password = "password123"
    
    print(f"Registering user: {username}...")
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    
    if resp.status_code != 200:
        print(f"Registration Failed: {resp.text}")
        return False
    print("Registration Success")
    
    # 2. Login
    print("Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    
    if resp.status_code != 200:
        print(f"Login Failed: {resp.text}")
        return False
    print(f"Login Success: {resp.json()}")
    
    # 3. Forgot Password
    print("Testing Forgot Password...")
    resp = requests.post(f"{BASE_URL}/auth/forgot-password", json={
        "email": email
    })
    
    if resp.status_code != 200:
        print(f"Forgot Password Failed: {resp.text}")
        return False
    print(f"Forgot Password Success (Check server logs for mock email): {resp.json()}")
    
    # 4. Admin Access (Fail)
    print("Testing Admin Access (Should Fail without secret)...")
    resp = requests.get(f"{BASE_URL}/admin/users", params={"username": username})
    if resp.status_code == 403:
        print("Admin Access Correctly Denied")
    else:
        print(f"Admin Access Incorrectly Allowed or Error: {resp.status_code} {resp.text}")
        
    # 5. Admin Access (Success with Header)
    print("Testing Admin Access (With Secret)...")
    headers = {"X-Admin-Secret": "admin123"} # Default secret
    resp = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    if resp.status_code == 200:
        users = resp.json()
        print(f"Admin Access Success. Found {len(users)} users.")
        # Verify our user is there
        found = False
        for u in users:
            if u['username'] == username:
                found = True
                break
        if found:
            print("New user found in admin list.")
        else:
            print("New user NOT found in admin list!")
            return False
    else:
        print(f"Admin Access Failed with Secret: {resp.status_code} {resp.text}")
        return False
        
    return True

if __name__ == "__main__":
    try:
        if test_auth():
            print("\n>>> AUTH TESTS PASSED <<<")
            sys.exit(0)
        else:
            print("\n>>> AUTH TESTS FAILED <<<")
            sys.exit(1)
    except Exception as e:
        print(f"Test Exception: {e}")
        sys.exit(1)
