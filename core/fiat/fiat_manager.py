import os
import time
from typing import Dict, List, Optional
from core.fiat.flutterwave import FlutterwaveAdapter
from core.compliance import ComplianceManager
from core.execution.swap_manager import SwapManager
from config.settings import FLUTTERWAVE_PUBLIC_KEY, FLUTTERWAVE_SECRET_KEY, FLUTTERWAVE_ENCRYPTION_KEY

class FiatManager:
    """
    Manages Fiat On/Off Ramp Operations.
    Integrates Flutterwave (Exclusive), Compliance, and Swap Logic.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.adapter = None
        # Enforce Flutterwave
        self.provider = "flutterwave"
        
        # Initialize Sub-Managers
        self.compliance = ComplianceManager(getattr(self.bot, 'storage', None))
        self.swap_manager = SwapManager(self.bot)
        
        # Load NGN Ledger Balance from Storage (Backed by Real Deposits)
        if hasattr(self.bot, 'storage'):
            self.fiat_balance = float(self.bot.storage.get_setting("fiat_balance_ngn", 0.0))
        else:
            self.fiat_balance = 0.0
        
        # FX Rates (Fetched live where possible)
        self.fx_rates = {}
        
        self.initialize_adapter()

    def initialize_adapter(self, username=None, provider_override=None):
        # Load keys from secure storage or config
        self.provider = "flutterwave" # Strict Enforcement
        
        # Priority: Env Vars -> Config Settings -> Defaults
        api_key = os.environ.get("FLUTTERWAVE_PUBLIC_KEY", FLUTTERWAVE_PUBLIC_KEY)
        secret_key = os.environ.get("FLUTTERWAVE_SECRET_KEY", FLUTTERWAVE_SECRET_KEY)
        encryption_key = os.environ.get("FLUTTERWAVE_ENCRYPTION_KEY", FLUTTERWAVE_ENCRYPTION_KEY)
        
        # Check bot secure storage if available
        if hasattr(self.bot, 'auth_manager') and username:
            keys = self.bot.auth_manager.get_api_keys(username, self.provider)
            print(f"DEBUG: FiatManager loaded keys: {keys}")
            if keys:
                if isinstance(keys, tuple):
                    api_key = keys[0]
                    secret_key = keys[1]
                elif isinstance(keys, dict):
                    api_key = keys.get('api_key', api_key)
                    secret_key = keys.get('api_secret', secret_key)
                    encryption_key = keys.get('encryption_key', encryption_key)
        
        print(f"DEBUG: Final Keys -> API: {api_key[:5]}... Secret: {secret_key[:5]}...")
        if not api_key or not secret_key:
            print(f"⚠️  No keys found for Flutterwave. Real Fund operations will fail.")
            self.adapter = None
            return

        # Auto-detect Live Mode based on Key Prefix
        is_live = False
        if "FLWPUBK_TEST" not in api_key and "FLWSECK_TEST" not in secret_key:
            is_live = True
            
        print(f"✅ Initializing Flutterwave Adapter (Live Mode: {is_live})")
        self.adapter = FlutterwaveAdapter(api_key, secret_key, live_mode=is_live, encryption_key=encryption_key)

    def get_ngn_balance(self):
        """Return virtual NGN balance"""
        return self.fiat_balance

    def initiate_deposit(self, amount: float, email: str) -> Dict:
        """
        Initiate NGN Deposit.
        """
        if not self.adapter:
            return {"status": "error", "message": "Fiat Adapter not initialized"}
        
        # Check Compliance Limit
        limit_check = self.compliance.check_transaction_limit(email, amount, "deposit")
        if not limit_check['allowed']:
             return {"status": "error", "message": limit_check['message']}
            
        return self.adapter.initialize_deposit(amount, email)

    # Alias for backward compatibility
    deposit_ngn = initiate_deposit
    
    def verify_deposit(self, reference: str) -> Dict:
        """
        Verify deposit and credit virtual balance.
        """
        if not self.adapter:
            return {"status": "error", "message": "Fiat Adapter not initialized"}
            
        # 1. Idempotency Check
        if hasattr(self.bot, 'storage'):
            existing_tx = self.bot.storage.get_fiat_transaction(reference)
            if existing_tx and existing_tx.get('status') == 'success':
                 return {"status": "error", "message": "Transaction already processed", "reference": reference}

        # 2. Verify with Adapter
        result = self.adapter.verify_transaction(reference)
        
        if result.get('status') == 'success':
            amount = result.get('amount', 0)
            
            # 3. Credit Balance
            self.fiat_balance += amount
            
            # 4. Persist State
            if hasattr(self.bot, 'storage'):
                self.bot.storage.save_setting("fiat_balance_ngn", self.fiat_balance)
                self.bot.storage.save_fiat_transaction(
                    reference, 'deposit', amount, 'NGN', 'success', details=result
                )
            
            return {"status": "success", "new_balance": self.fiat_balance, "amount_credited": amount}
            
        return result

    def initiate_withdrawal(self, amount: float, bank_code: str, account_number: str, account_name: str = None) -> Dict:
        """
        Withdraw NGN to Bank. Auto-resolves account name if missing.
        """
        if not self.adapter:
            return {"status": "error", "message": "Fiat Adapter not initialized"}
            
        if self.fiat_balance < amount:
            return {"status": "error", "message": "Insufficient NGN Balance (Bot Ledger)"}

        # --- SIMULATION MODE CHECK ---
        trading_mode = os.environ.get("TRADING_MODE", "Demo")
        if trading_mode == "Demo":
            print(f"ℹ️ [Demo Mode] Simulating Withdrawal of ₦{amount}...")
            # Simulate Success
            self.fiat_balance -= amount
            
            # Persist
            if hasattr(self.bot, 'storage'):
                self.bot.storage.save_setting("fiat_balance_ngn", self.fiat_balance)
                self.bot.storage.save_fiat_transaction(
                    f"sim_with_{int(time.time())}", 'withdrawal', amount, 'NGN', 'success', 
                    details={"mode": "demo", "bank": bank_code, "account": account_number}
                )
            
            return {
                "status": "success", 
                "message": "Withdrawal Successful (Demo Mode)", 
                "reference": f"sim_with_{int(time.time())}",
                "amount": amount
            }

        # Check Real Flutterwave Balance (Proactive Check)
        try:
            balances = self.get_balances()
            ngn_bal = next((b for b in balances if b['currency'] == 'NGN'), None)
            if ngn_bal:
                avail = float(ngn_bal.get('available_balance', 0))
                ledger = float(ngn_bal.get('ledger_balance', 0))
                
                # STRICT CHECK: To prevent confusing "Contact Administrator" API errors,
                # we block withdrawals if Available Balance is insufficient.
                
                # Calculate likely fee to ensure coverage
                fee = 10.75 # Minimum buffer
                if amount > 5000: fee = 26.88
                if amount > 50000: fee = 53.75
                
                required = amount + fee
                
                if avail < required:
                    return {
                        "status": "error", 
                        "message": (
                            f"Withdrawal Rejected: Insufficient Settled Funds (incl. fees). "
                            f"Available: ₦{avail:,.2f} (Ledger: ₦{ledger:,.2f}). "
                            f"Required: ₦{required:,.2f}. "
                            "Funds from new deposits typically take 24 hours to settle. "
                            "Please try again when funds are Available."
                        )
                    }
        except Exception as e:
            print(f"⚠️ Failed to check real balance: {e}")

        # Check Compliance Limit (Withdrawal)
        # Using account_number as user_id proxy if logged in user is generic, or pass actual user_id
        user_id = account_number # Simplification for MVP
        limit_check = self.compliance.check_transaction_limit(user_id, amount, "withdrawal")
        if not limit_check['allowed']:
             return {"status": "error", "message": limit_check['message']}

        # Auto-resolve name if missing
        if not account_name:
             res = self.resolve_account(account_number, bank_code)
             if res.get('status') == 'success':
                 account_name = res.get('account_name')
             else:
                 return {"status": "error", "message": f"Could not resolve account: {res.get('message')}"}

        # 1. Create Recipient
        recipient = self.adapter.create_transfer_recipient(account_name, account_number, bank_code)
        if recipient.get('status') != 'success':
            return recipient
            
        recipient_code = recipient.get('recipient_code')
        
        # 2. Initiate Transfer
        transfer = self.adapter.initiate_transfer(amount, recipient_code, reason="Withdrawal from Bot")
        
        # Intercept vague Flutterwave errors
        if transfer.get('status') != 'success' and transfer.get('status') != 'pending':
            msg = transfer.get('message', '')
            if "contact your account administrator" in msg.lower():
                transfer['message'] = (
                    f"Transaction Declined by Payment Provider. "
                    f"This usually means Insufficient Settled Funds or an Account Limit. "
                    f"Original Error: {msg}"
                )
        
        if transfer.get('status') == 'success' or transfer.get('status') == 'pending':
            self.fiat_balance -= amount
            
            # Persist
            if hasattr(self.bot, 'storage'):
                self.bot.storage.save_setting("fiat_balance_ngn", self.fiat_balance)
                self.bot.storage.save_fiat_transaction(
                    transfer.get('reference', 'unknown'), 'withdrawal', amount, 'NGN', 'pending', details=transfer
                )
                
        return transfer

    # Alias
    withdraw_ngn = initiate_withdrawal

    def get_banks(self):
        if self.adapter:
            return self.adapter.get_banks()
        return []

    def get_balances(self):
        if self.adapter:
            return self.adapter.get_balances()
        return []

    def resolve_account(self, account_number, bank_code):
        if self.adapter:
            return self.adapter.resolve_account_number(account_number, bank_code)
        return {"status": "error", "message": "Adapter not ready"}

    def execute_swap(self, from_asset: str, to_asset: str, amount: float) -> Dict:
        """
        Execute Swap using SwapManager.
        """
        # 1. Get Quote
        quote = self.swap_manager.get_quote(from_asset, to_asset, amount)
        if quote['status'] != 'success':
            return quote
            
        # 2. Check Balance & Deduct
        if from_asset == 'NGN':
            if self.fiat_balance < amount:
                return {"status": "error", "message": "Insufficient NGN Balance"}
            self.fiat_balance -= amount
            
        elif from_asset in ['USDT', 'USD']:
            # Assume external balance check is done or passed in. 
            # For MVP, we'll verify if we have a way to check user's USDT balance here.
            # But typically, the dashboard/caller handles the crypto debit logic or we integrate with UserWallet.
            pass
            
        # 3. Execute
        res = self.swap_manager.execute_swap("user_id", quote)
        
        if res['status'] == 'success':
            # Credit Target
            if to_asset == 'NGN':
                self.fiat_balance += res['amount_out']
            elif to_asset in ['USDT', 'USD']:
                if hasattr(self.bot, 'storage'):
                    current_credit = float(self.bot.storage.get_setting("virtual_usdt_credit_usd", 0.0) or 0.0)
                    self.bot.storage.save_setting("virtual_usdt_credit_usd", current_credit + float(res.get('amount_out', 0.0)))
            
            # Debit when selling USDT to NGN
            if from_asset in ['USDT', 'USD']:
                if hasattr(self.bot, 'storage'):
                    current_credit = float(self.bot.storage.get_setting("virtual_usdt_credit_usd", 0.0) or 0.0)
                    new_credit = current_credit - float(amount)
                    if new_credit < 0:
                        new_credit = 0.0
                    self.bot.storage.save_setting("virtual_usdt_credit_usd", new_credit)
                
            # Save State
            if hasattr(self.bot, 'storage'):
                 self.bot.storage.save_setting("fiat_balance_ngn", self.fiat_balance)
                 self.bot.storage.save_fiat_transaction(
                    f"swap_{int(time.time())}", 
                    'swap_buy' if from_asset == 'NGN' else 'swap_sell',
                    amount, from_asset, 'success', 
                    details={"quote": quote, "tx": res}
                )
                
            return {**res, "quote": quote}
            
        return res
        # and now we are just moving the accounting value to NGN.
        # In reality, we need to ensure the USD is liquid.
        
        current_usd = self.bot.risk_manager.live_balance
        if current_usd >= amount_usd:
             self.bot.risk_manager.update_live_balance(current_usd - amount_usd)
             self.fiat_balance += ngn_value
             return {"status": "success", "ngn_amount": ngn_value, "rate": rate}
        else:
             return {"status": "error", "message": "Insufficient USD Trading Balance"}

    def refund_usdt_credit_to_ngn(self, amount_usd: float = None) -> Dict:
        """
        Convert stored USDT credit back to NGN and clear the credit.
        If amount_usd is None, refund the full available credit.
        """
        try:
            credit = 0.0
            if hasattr(self.bot, 'storage'):
                credit = float(self.bot.storage.get_setting("virtual_usdt_credit_usd", 0.0) or 0.0)
            if amount_usd is None:
                amount_usd = credit
            amount_usd = float(amount_usd or 0.0)
            if amount_usd <= 0:
                return {"status": "error", "message": "No USDT credit available to refund"}
            if credit <= 0:
                return {"status": "error", "message": "No stored USDT credit"}
            amount_usd = min(amount_usd, credit)

            # Get quote and execute swap (USDT -> NGN)
            quote = self.swap_manager.get_quote('USDT', 'NGN', amount_usd)
            if quote.get('status') != 'success':
                return quote
            tx = self.swap_manager.execute_swap("user_id", quote)
            if tx.get('status') != 'success':
                return tx

            ngn_amount = float(tx.get('amount_out', 0.0) or 0.0)
            self.fiat_balance += ngn_amount

            # Persist updates
            if hasattr(self.bot, 'storage'):
                new_credit = round(credit - amount_usd, 8)
                if new_credit < 0: new_credit = 0.0
                self.bot.storage.save_setting("virtual_usdt_credit_usd", new_credit)
                self.bot.storage.save_setting("fiat_balance_ngn", self.fiat_balance)
                self.bot.storage.save_fiat_transaction(
                    f"refund_{int(time.time())}",
                    'refund', ngn_amount, 'NGN', 'success',
                    details={"amount_usd": amount_usd, "quote": quote, "tx": tx}
                )

            return {"status": "success", "ngn_amount": ngn_amount, "amount_usd": amount_usd}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def manual_refund_ngn(self, amount_ngn: float, note: str = "Manual refund") -> Dict:
        """Directly credit NGN fiat balance and log a manual refund."""
        try:
            amount_ngn = float(amount_ngn)
            if amount_ngn <= 0:
                return {"status": "error", "message": "Invalid amount"}
            self.fiat_balance += amount_ngn
            if hasattr(self.bot, 'storage'):
                self.bot.storage.save_setting("fiat_balance_ngn", self.fiat_balance)
                self.bot.storage.save_fiat_transaction(
                    f"manual_refund_{int(time.time())}",
                    'refund', amount_ngn, 'NGN', 'success', details={"note": note}
                )
            return {"status": "success", "new_balance": self.fiat_balance}
        except Exception as e:
            return {"status": "error", "message": str(e)}
