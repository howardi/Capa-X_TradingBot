import json
from datetime import datetime
from api.db import get_db_connection
from api.core.logger import logger

class RiskManager:
    """
    Enforces institutional-grade risk controls:
    1. Daily Loss Limit
    2. Max Drawdown
    3. Position Sizing Caps
    4. Kill Switch
    """
    
    def __init__(self):
        self.defaults = {
            "max_daily_loss_pct": 0.05, # 5% daily loss limit
            "max_drawdown_pct": 0.10,   # 10% global drawdown
            "max_position_pct": 0.20,   # Max 20% of equity per trade
            "max_open_positions": 5     # Max 5 concurrent trades
        }

    def check_trade_allowed(self, username, symbol, amount_usd, current_equity):
        """
        Validates if a new trade can be opened.
        Returns: (bool, reason)
        """
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            
            # 1. Check Kill Switch / Daily Lock
            c.execute("SELECT * FROM risk_daily_stats WHERE username=? AND date=?", (username, date_str))
            stats = c.fetchone()
            
            if not stats:
                 # Initialize Daily Stats
                 c.execute("""INSERT INTO risk_daily_stats 
                              (username, date, starting_balance, current_balance, daily_pnl)
                              VALUES (?, ?, ?, ?, 0.0)""",
                           (username, date_str, current_equity, current_equity))
                 conn.commit()
                 # Re-fetch
                 c.execute("SELECT * FROM risk_daily_stats WHERE username=? AND date=?", (username, date_str))
                 stats = c.fetchone()
            
            if stats:
                if stats['is_locked']:
                    return False, "Daily Risk Limit Hit (Locked)"
                
                # Check Daily Loss
                starting_bal = stats['starting_balance']
                if starting_bal > 0:
                    current_loss_pct = (stats['daily_pnl'] / starting_bal)
                    if current_loss_pct <= -self.defaults['max_daily_loss_pct']:
                        # Lock account
                        c.execute("UPDATE risk_daily_stats SET is_locked=1 WHERE id=?", (stats['id'],))
                        conn.commit()
                        logger.warning(f"User {username} hit daily loss limit. Account Locked.")
                        return False, f"Daily Loss Limit Exceeded ({current_loss_pct*100:.2f}%)"

            # 2. Check Position Size
            if amount_usd > (current_equity * self.defaults['max_position_pct']):
                return False, f"Position size {amount_usd} exceeds max {self.defaults['max_position_pct']*100}% of equity"

            # 3. Check Max Open Positions
            c.execute("SELECT count(*) as count FROM bot_activity WHERE username=? AND status='open'", (username,))
            open_count = c.fetchone()['count']
            
            if open_count >= self.defaults['max_open_positions']:
                return False, f"Max open positions ({self.defaults['max_open_positions']}) reached"

            return True, "Allowed"
            
        except Exception as e:
            logger.error(f"Risk Check Error: {e}")
            return False, f"Risk Check Failed: {e}"
        finally:
            conn.close()

    def update_after_trade_close(self, username, pnl, current_balance):
        """
        Updates daily stats after a trade closes.
        """
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            
            # Get or Init Stats
            c.execute("SELECT * FROM risk_daily_stats WHERE username=? AND date=?", (username, date_str))
            stats = c.fetchone()
            
            if not stats:
                # First trade of day, initialize
                # Ideally this runs at 00:00, but lazy init works too
                c.execute("""INSERT INTO risk_daily_stats 
                             (username, date, starting_balance, current_balance, daily_pnl, trade_count, loss_count)
                             VALUES (?, ?, ?, ?, ?, 1, ?)""",
                          (username, date_str, current_balance - pnl, current_balance, pnl, 1 if pnl < 0 else 0))
            else:
                new_pnl = stats['daily_pnl'] + pnl
                loss_inc = 1 if pnl < 0 else 0
                
                # Check Drawdown logic (simplified for daily)
                start = stats['starting_balance']
                dd = 0
                if start > 0:
                    dd = (start - current_balance) / start if current_balance < start else 0
                
                c.execute("""UPDATE risk_daily_stats 
                             SET current_balance=?, daily_pnl=?, trade_count=trade_count+1, 
                                 loss_count=loss_count+?, max_drawdown=MAX(max_drawdown, ?)
                             WHERE id=?""",
                          (current_balance, new_pnl, loss_inc, dd, stats['id']))
                          
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to update risk stats: {e}")
        finally:
            conn.close()
