
import json
import os
import hashlib
from datetime import datetime, timedelta
import pandas as pd

class ComplianceManager:
    """
    Risk & Compliance Module.
    Handles layered limits, kill-switches, audit logging, and policy enforcement.
    """
    def __init__(self, bot):
        self.bot = bot
        self.audit_log_file = "compliance_audit.log"
        self.config = {
            "max_daily_loss_pct": 5.0,  # 5% max daily drawdown
            "max_drawdown_pct": 10.0,   # 10% total max drawdown
            "max_leverage": 5.0,
            "restricted_assets": ["XMR", "DASH", "ZEC"], # Privacy coins often restricted
            "required_confirmations": 1
        }
        self.daily_pnl = 0.0
        self.starting_equity = 10000.0 # Should be synced with wallet
        self.is_kill_switch_active = False
        
        # Initialize Audit Log
        if not os.path.exists(self.audit_log_file):
            self.log_audit_event("SYSTEM_INIT", "Compliance Module Initialized", "SYSTEM")

    def log_audit_event(self, event_type: str, description: str, actor: str, meta: dict = None):
        """
        Immutable-ish Audit Logging (Append Only with Hash Chaining concept)
        """
        entry = {
            "timestamp": str(datetime.now()),
            "event_type": event_type,
            "description": description,
            "actor": actor,
            "meta": meta or {}
        }
        
        # Simple checksum for integrity (in production, use Merkle tree or blockchain)
        entry_str = json.dumps(entry, sort_keys=True)
        checksum = hashlib.sha256(entry_str.encode()).hexdigest()
        entry['checksum'] = checksum
        
        with open(self.audit_log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def check_trade_compliance(self, symbol: str, side: str, amount: float, price: float) -> dict:
        """
        Pre-trade compliance check.
        Returns: {'allowed': bool, 'reason': str}
        """
        if self.is_kill_switch_active:
            return {'allowed': False, 'reason': "KILL SWITCH ACTIVE"}
            
        # 1. Restricted Assets Policy
        base_asset = symbol.split('/')[0]
        if base_asset in self.config["restricted_assets"]:
            self.log_audit_event("COMPLIANCE_BLOCK", f"Attempted trade on restricted asset {base_asset}", "BOT")
            return {'allowed': False, 'reason': f"Restricted Asset: {base_asset}"}
            
        # 2. Daily Loss Limit
        current_drawdown = -self.daily_pnl if self.daily_pnl < 0 else 0
        loss_pct = (current_drawdown / self.starting_equity) * 100
        if loss_pct >= self.config["max_daily_loss_pct"]:
            self.trigger_kill_switch(f"Daily Loss Limit Exceeded ({loss_pct:.2f}%)")
            return {'allowed': False, 'reason': "Daily Loss Limit Exceeded"}
            
        # 3. Notional Value Limits (e.g. Max trade size $50k)
        notional_value = amount * price
        if notional_value > 50000:
             return {'allowed': False, 'reason': f"Trade Size Limit Exceeded (${notional_value:.2f})"}

        return {'allowed': True, 'reason': "Compliance Passed"}

    def update_pnl(self, realized_pnl: float):
        """
        Update internal PnL tracker.
        """
        self.daily_pnl += realized_pnl
        # Reset logic would go here (e.g. check date change)

    def trigger_kill_switch(self, reason: str):
        """
        Emergency Halt.
        """
        self.is_kill_switch_active = True
        self.log_audit_event("KILL_SWITCH_TRIGGERED", reason, "SYSTEM")
        print(f"🚨 KILL SWITCH TRIGGERED: {reason}")
        # In a real system, this would cancel all open orders immediately via bot.data_manager

    def reset_kill_switch(self, actor: str):
        self.is_kill_switch_active = False
        self.daily_pnl = 0.0 # Optional reset
        self.log_audit_event("KILL_SWITCH_RESET", "Manual Reset", actor)

    def get_status(self):
        return {
            "kill_switch": self.is_kill_switch_active,
            "daily_loss_pct": (-self.daily_pnl / self.starting_equity * 100) if self.daily_pnl < 0 else 0.0,
            "allowed_assets": "ALL except " + ",".join(self.config["restricted_assets"])
        }
