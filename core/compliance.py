from typing import Dict, Optional, List
import time

class ComplianceManager:
    """
    Handles KYC/AML, Transaction Limits, and Risk Monitoring for Nigerian Users.
    """
    
    TIERS = {
        0: {"daily_limit": 50000.0, "single_limit": 20000.0, "req": "Email Verified"},
        1: {"daily_limit": 500000.0, "single_limit": 100000.0, "req": "BVN Verified"},
        2: {"daily_limit": 5000000.0, "single_limit": 1000000.0, "req": "ID Verified"},
        3: {"daily_limit": float('inf'), "single_limit": float('inf'), "req": "Enhanced Due Diligence"}
    }

    def __init__(self, storage_manager=None):
        self.storage = storage_manager

    def get_user_tier(self, user_id: str) -> int:
        """
        Get user KYC Tier. 
        For MVP, default to Tier 1 if not found.
        In prod, fetch from User Table.
        """
        # Simulated Tier for MVP
        if self.storage:
            # Check if user has stored KYC data
            # tier = self.storage.get_user_kyc_tier(user_id)
            pass
        return 1

    def check_transaction_limit(self, user_id: str, amount: float, tx_type: str = "withdrawal") -> Dict:
        """
        Check if transaction exceeds daily or single limits.
        """
        tier_level = self.get_user_tier(user_id)
        tier_limits = self.TIERS.get(tier_level, self.TIERS[0])
        
        # 1. Single Transaction Limit
        if amount > tier_limits["single_limit"]:
            return {
                "allowed": False, 
                "message": f"Amount exceeds single limit of ₦{tier_limits['single_limit']:,.2f} for Tier {tier_level}"
            }
            
        # 2. Daily Limit Check
        # Fetch today's total volume for this user and type
        daily_total = self._get_daily_volume(user_id, tx_type)
        if (daily_total + amount) > tier_limits["daily_limit"]:
             return {
                "allowed": False, 
                "message": f"Daily limit of ₦{tier_limits['daily_limit']:,.2f} exceeded. Used: ₦{daily_total:,.2f}"
            }
            
        return {"allowed": True, "tier": tier_level}

    def _get_daily_volume(self, user_id: str, tx_type: str) -> float:
        """
        Calculate total volume for today.
        In prod, query StorageManager for transactions since midnight.
        """
        if self.storage:
            # txs = self.storage.get_transactions_since(user_id, tx_type, midnight_timestamp)
            # return sum(t['amount'] for t in txs)
            
            # Use 'get_recent_fiat_transactions' as a proxy for now if we don't have user_id specific query
            # Ideally we need a method `get_daily_volume(user_id)`
            pass
        return 0.0 # Mock for MVP

    def verify_identity(self, user_id: str, bvn: str = None, nin: str = None) -> Dict:
        """
        Mock Identity Verification (BVN/NIN).
        Integrate with Smile Identity / Dojah / YouVerify here.
        """
        if bvn and len(bvn) == 11:
            return {"status": "success", "tier": 1, "message": "BVN Verified"}
        return {"status": "failed", "message": "Invalid ID"}

    def log_suspicious_activity(self, user_id: str, action: str, details: Dict):
        """
        Log suspicious events for AML monitoring.
        """
        print(f"AML ALERT: User {user_id} performed {action}: {details}")
        # Save to 'compliance_logs' table
