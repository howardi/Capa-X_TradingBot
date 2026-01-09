
import unittest
import os
import shutil
from core.auth import AuthManager

class TestAuthKeys(unittest.TestCase):
    def setUp(self):
        self.test_dir = "data/test_users"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.auth = AuthManager(data_dir=self.test_dir)
        self.auth.register_user("testuser", "password123", "test@example.com")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_get_keys(self):
        # Test saving keys with encryption key
        username = "testuser"
        exchange = "flutterwave"
        api_key = "pk_test_123"
        secret_key = "sk_test_456"
        enc_key = "enc_key_789"

        success = self.auth.save_api_keys(username, exchange, api_key, secret_key, encryption_key=enc_key)
        self.assertTrue(success)

        # Retrieve keys
        keys = self.auth.get_api_keys(username, exchange)
        self.assertIsNotNone(keys)
        self.assertIsInstance(keys, dict)
        self.assertEqual(keys['api_key'], api_key)
        self.assertEqual(keys['api_secret'], secret_key)
        self.assertEqual(keys['encryption_key'], enc_key)

    def test_save_without_enc_key(self):
        # Test backward compatibility (sort of)
        username = "testuser"
        exchange = "binance"
        api_key = "pk_bin_123"
        secret_key = "sk_bin_456"

        success = self.auth.save_api_keys(username, exchange, api_key, secret_key)
        self.assertTrue(success)

        keys = self.auth.get_api_keys(username, exchange)
        self.assertIsNotNone(keys)
        self.assertEqual(keys['api_key'], api_key)
        self.assertEqual(keys['api_secret'], secret_key)
        self.assertNotIn('encryption_key', keys)

if __name__ == '__main__':
    unittest.main()
