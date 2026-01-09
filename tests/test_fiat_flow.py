import unittest
from unittest.mock import MagicMock, patch
from core.fiat.fiat_manager import FiatManager
from core.fiat.flutterwave import FlutterwaveAdapter
from core.execution.swap_manager import SwapManager

class TestFiatSystem(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_bot.storage.get_setting.return_value = 0.0
        self.mock_bot.config = {}
        
        self.fiat_manager = FiatManager(self.mock_bot)
        
        # Mock Adapters
        self.fiat_manager.adapter = MagicMock()
        self.fiat_manager.adapter.initialize_deposit.return_value = {
            "status": "success", 
            "reference": "test_ref", 
            "authorization_url": "http://pay.com"
        }
        self.fiat_manager.adapter.verify_transaction.return_value = {
            "status": "success",
            "amount": 5000.0
        }
        
    def test_deposit_flow(self):
        # 1. Initiate
        res = self.fiat_manager.initiate_deposit(5000.0, "test@example.com")
        self.assertEqual(res['status'], "success")
        self.assertEqual(res['reference'], "test_ref")
        
        # 2. Verify
        # Mock storage to return None (not processed yet)
        self.mock_bot.storage.get_fiat_transaction.return_value = None
        
        verify_res = self.fiat_manager.verify_deposit("test_ref")
        self.assertEqual(verify_res['status'], "success")
        self.assertEqual(self.fiat_manager.fiat_balance, 5000.0)
        
        # 3. Idempotency Check
        self.mock_bot.storage.get_fiat_transaction.return_value = {"status": "success"}
        dup_res = self.fiat_manager.verify_deposit("test_ref")
        self.assertEqual(dup_res['status'], "error")
        self.assertEqual(dup_res['message'], "Transaction already processed")

    def test_compliance_limits(self):
        # Tier 1 Limit is 100,000 single
        res = self.fiat_manager.initiate_deposit(150000.0, "test@example.com")
        self.assertEqual(res['status'], "error")
        self.assertIn("exceeds single limit", res['message'])

    def test_swap_quote(self):
        quote = self.fiat_manager.swap_manager.get_quote("NGN", "USDT", 165000.0)
        self.assertEqual(quote['status'], "success")
        # Rate is roughly 1/1655
        self.assertAlmostEqual(quote['amount_out_net'], 165000 / 1655 * 0.995, delta=5.0)

    def test_swap_execution_ngn_to_usdt(self):
        # Credit user first
        self.fiat_manager.fiat_balance = 200000.0
        
        quote = self.fiat_manager.swap_manager.get_quote("NGN", "USDT", 165000.0)
        res = self.fiat_manager.execute_swap("NGN", "USDT", 165000.0)
        
        self.assertEqual(res['status'], "success")
        self.assertEqual(self.fiat_manager.fiat_balance, 35000.0) # 200k - 165k

    def test_withdraw_flow(self):
        self.fiat_manager.fiat_balance = 50000.0
        
        # Mock Resolve
        self.fiat_manager.adapter.resolve_account_number.return_value = {
            "status": "success", "account_name": "Test User"
        }
        # Mock Transfer
        self.fiat_manager.adapter.create_transfer_recipient.return_value = {
            "status": "success", "recipient_code": "RCP_123"
        }
        self.fiat_manager.adapter.initiate_transfer.return_value = {
            "status": "success", "reference": "wd_ref"
        }
        
        res = self.fiat_manager.initiate_withdrawal(10000.0, "057", "1234567890")
        self.assertEqual(res['status'], "success")
        self.assertEqual(self.fiat_manager.fiat_balance, 40000.0)

if __name__ == '__main__':
    unittest.main()
