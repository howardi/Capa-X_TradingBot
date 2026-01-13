import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.coinbase_service import CoinbaseService

class TestCoinbaseService(unittest.TestCase):
    def setUp(self):
        self.service = CoinbaseService()

    def test_key_loading(self):
        # Keys should be loaded from .env (which we updated)
        self.assertIsNotNone(self.service.api_key)
        self.assertIsNotNone(self.service.secret_key)

    def test_private_key_formatting(self):
        pem = self.service._get_formatted_private_key()
        self.assertIn("-----BEGIN EC PRIVATE KEY-----", pem)
        self.assertIn("-----END EC PRIVATE KEY-----", pem)

    def test_jwt_signing(self):
        # Mocking time to have consistent result if needed, but we just check structure
        msg = {"type": "subscribe"}
        signed = self.service.sign_with_jwt(msg, "level2", ["BTC-USD"])
        self.assertIn('jwt', signed)
        print(f"Generated Token: {signed['jwt'][:20]}...")

if __name__ == '__main__':
    unittest.main()
