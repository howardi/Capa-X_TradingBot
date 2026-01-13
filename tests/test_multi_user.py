import unittest
import os
import json
import sys
import sqlite3
from unittest.mock import MagicMock

# Mock firebase_admin before importing api
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
mock_firestore = MagicMock()
# Return None to ensure db=None in api/index.py, bypassing Cloud logic
mock_firestore.client.return_value = None
sys.modules['firebase_admin.firestore'] = mock_firestore

# Add api to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

# Set Test DB
os.environ['DB_PATH'] = 'test_users.db'

try:
    import index
    from index import app, init_sqlite
except ImportError:
    # If running from root, path might be different
    sys.path.append(os.path.join(os.getcwd(), 'api'))
    import index
    from index import app, init_sqlite

class MultiUserTestCase(unittest.TestCase):
    def setUp(self):
        # Force db to None to use SQLite
        index.db = None
        
        self.app = app.test_client()
        self.app.testing = True
        
        # Clear tables instead of deleting file to avoid locking issues
        try:
            conn = sqlite3.connect(os.environ['DB_PATH'])
            c = conn.cursor()
            # Create tables if not exist (in case init_sqlite hasn't run or file deleted)
            init_sqlite()
            
            # Clear data
            c.execute("DELETE FROM users")
            try:
                c.execute("DELETE FROM wallets")
            except:
                pass
            try:
                c.execute("DELETE FROM exchanges")
            except:
                pass
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB Cleanup Error: {e}")
            # If file doesn't exist or other error, ensure init
            init_sqlite()

    def tearDown(self):
        # Optional: Clear data again or leave it for inspection
        pass

    def test_register_login(self):
        print("\nTesting Register & Login...")
        # Register
        res = self.app.post('/api/register', json={'username': 'testuser', 'password': 'password123'})
        if res.status_code != 200:
            print(f"Register Failed: {res.status_code} - {res.data}")
        self.assertEqual(res.status_code, 200)
        
        # Login
        res = self.app.post('/api/login', json={'username': 'testuser', 'password': 'password123'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['username'], 'testuser')
        print("✅ Register & Login Passed")

    def test_wallet_flow(self):
        print("\nTesting Wallet Flow...")
        username = 'walletuser'
        # Register
        self.app.post('/api/register', json={'username': username, 'password': 'pw'})
        
        # Import Wallet (Use a valid format PK)
        valid_pk = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
        
        res = self.app.post('/api/wallet/import', json={
            'username': username,
            'private_key': valid_pk
        })
        self.assertEqual(res.status_code, 200)
        
        # Get Info
        res = self.app.get(f'/api/wallet/info?username={username}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsNotNone(data['address'])
        print(f"✅ Wallet Imported: {data['address']}")
        
        # Transfer (Should fail due to no balance/connection but return appropriate error)
        res = self.app.post('/api/wallet/transfer', json={
            'username': username,
            'to_address': '0x123...',
            'amount': 0.1
        })
        # Could be 500 (Not connected) or 400.
        print(f"Transfer Response: {res.status_code}")

    def test_uniswap_swap(self):
        print("\nTesting Uniswap Swap Endpoint...")
        username = 'uniuser'
        self.app.post('/api/register', json={'username': username, 'password': 'pw'})
        valid_pk = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
        self.app.post('/api/wallet/import', json={'username': username, 'private_key': valid_pk})

        # Use valid address format
        valid_token = "0xdAC17F958D2ee523a2206206994597C13D831ec7" # USDT
        res = self.app.post('/api/uniswap/swap', json={
            'username': username,
            'amount_in': '0.01',
            'token_out': valid_token
        })
        # Should fail due to connection/balance but logic should hold
        print(f"Swap Response: {res.status_code}")
        # We expect 500 or 400, but NOT 404 (Wallet not found)
        self.assertNotEqual(res.status_code, 404)
        print("✅ Uniswap Swap logic reachable")

if __name__ == '__main__':
    unittest.main()
