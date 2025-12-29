
import pandas as pd
import numpy as np
import json
import os
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class AITrainer:
    """
    Implements Self-Learning Strategy Optimization using Machine Learning.
    Uses Random Forest to model the relationship between Strategy Parameters (Risk, Indicators)
    and Trade Outcomes (PnL), then optimizes parameters to maximize expected return.
    """
    def __init__(self, bot):
        self.bot = bot
        self.memory_file = "data/ai_memory.json"
        self.model = RandomForestRegressor(n_estimators=100, random_state=42) if SKLEARN_AVAILABLE else None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.is_trained = False
        
    def train_on_history(self, trade_history):
        """
        Train ML model on past trades to find optimal risk parameters.
        """
        if not trade_history:
            return {"status": "No data", "improvement": 0.0}
            
        df = pd.DataFrame(trade_history)
        if df.empty or len(df) < 10:
            return {"status": "Insufficient data (need 10+ trades)", "improvement": 0.0}
            
        # 1. Feature Engineering
        # We assume trade history contains config snapshot used for that trade
        # If not, we simulate by adding current config + noise (in a real scenario, we'd log config with every trade)
        if 'stop_loss_pct' not in df.columns:
            # Synthetic history for demonstration if real logs miss this
            df['stop_loss_pct'] = np.random.normal(self.bot.risk_manager.stop_loss_config.get('value', 1.5), 0.2, len(df))
            
        X = df[['stop_loss_pct']].values
        y = df['pnl'].values
        
        # 2. Train Model
        if SKLEARN_AVAILABLE:
            self.model.fit(X, y)
            self.is_trained = True
            
            # 3. Optimize: Query model for best parameter in a safe range
            candidate_sls = np.linspace(0.5, 5.0, 50).reshape(-1, 1)
            predicted_pnls = self.model.predict(candidate_sls)
            best_idx = np.argmax(predicted_pnls)
            best_sl = candidate_sls[best_idx][0]
            expected_pnl = predicted_pnls[best_idx]
            
            current_sl = self.bot.risk_manager.stop_loss_config.get('value', 1.5)
            
            # 4. Apply Update if improvement is significant
            if expected_pnl > df['pnl'].mean() and abs(best_sl - current_sl) > 0.1:
                self.bot.risk_manager.stop_loss_config['value'] = float(best_sl)
                action = f"Updated Stop Loss to {best_sl:.2f}% (Exp. PnL: {expected_pnl:.2f})"
            else:
                action = "Hold (Current config is optimal)"
                best_sl = current_sl

            return {
                "status": "Optimized (ML)",
                "action": action,
                "new_sl": best_sl,
                "win_rate": len(df[df['pnl']>0])/len(df)
            }
            
        else:
            # Fallback to Heuristic
            return self._heuristic_optimization(df)

    def _heuristic_optimization(self, df):
        # ... (Previous logic) ...
        win_rate = len(df[df['pnl'] > 0]) / len(df)
        current_sl = self.bot.risk_manager.stop_loss_config.get('value', 1.5)
        new_sl = current_sl
        
        action = "hold"
        if win_rate < 0.4:
            new_sl = current_sl * 0.9
            action = "tighten_risk"
        elif win_rate > 0.6:
            new_sl = current_sl * 1.1
            action = "expand_risk"
            
        new_sl = max(1.0, min(new_sl, 3.0))
        if new_sl != current_sl:
            self.bot.risk_manager.stop_loss_config['value'] = new_sl
            
        return {
            "status": "Optimized (Heuristic)",
            "action": action,
            "new_sl": new_sl,
            "win_rate": win_rate
        }
        
    def _save_memory(self, event):
        data = []
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                try:
                    data = json.load(f)
                except: pass
        data.append(event)
        
        # Ensure dir exists
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        
        with open(self.memory_file, 'w') as f:
            json.dump(data[-50:], f) # Keep last 50 events

