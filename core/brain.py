
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

class CapacityBayBrain:
    def __init__(self):
        self.regimes = {
            'trend_accel': 'Trend Acceleration',
            'trend_exhaust': 'Trend Exhaustion',
            'range_accum': 'Range Accumulation',
            'range_dist': 'Range Distribution',
            'vol_shock': 'Volatility Shock',
            'vol_squeeze': 'Volatility Squeeze (Pre-Breakout)',
            'struct_break': 'Structural Breakdown',
            'quantum_flux': 'Quantum Flux (Uncertainty)'
        }
        
        # Lazy Load AI and Quantum Engines to prevent circular imports and improve startup speed
        from core.ai import AIEngine
        from core.quantum import QuantumEngine
        
        self.ai_engine = AIEngine()
        self.quantum = QuantumEngine()
        
        # Meta-Strategy State
        self.strategy_weights = {
            'trend_following': 0.5,
            'mean_reversion': 0.3,
            'breakout': 0.2
        }

    def update_strategy_weights(self, performance_metrics: dict):
        """
        Meta-Strategy Optimizer: Dynamically reallocates influence based on recent performance.
        """
        # Simple reinforcement learning logic
        total_score = 0
        for strat, score in performance_metrics.items():
            self.strategy_weights[strat] *= (1 + score) # Boost if positive, decay if negative
            total_score += self.strategy_weights[strat]
            
        # Normalize
        if total_score > 0:
            for strat in self.strategy_weights:
                self.strategy_weights[strat] /= total_score

    def get_ai_prediction(self, df_features: pd.DataFrame) -> float:
        """
        Get prediction from AI Engine using Feature Store data.
        Returns a score between -1 (Strong Sell) and 1 (Strong Buy).
        """
        if df_features.empty or not hasattr(self, 'ai_engine'):
            return 0.0
            
        # Feature columns matching AIEngine input (v2)
        feature_cols = ["rsi", "ema_50", "ema_200", "atr", "adx", "macd", "bollinger_width", "returns", "log_volume", "high_low_pct"]
        
        # Ensure all columns exist
        if not all(col in df_features.columns for col in feature_cols):
            return 0.0
            
        # Get last 10 rows (seq_len=10)
        if len(df_features) < 10:
            return 0.0
            
        seq_data = df_features[feature_cols].iloc[-10:].values.astype(np.float32)
        
        # Simple local normalization (MinMax over the window) to prevent exploding gradients/outputs
        # in the untrained model or if inputs vary wildly.
        min_val = np.min(seq_data, axis=0)
        max_val = np.max(seq_data, axis=0)
        # Avoid division by zero
        range_val = max_val - min_val
        range_val[range_val == 0] = 1.0
        
        normalized_seq = (seq_data - min_val) / range_val
        
        # Predict
        try:
            prediction = self.ai_engine.predict_next_price_lstm(normalized_seq)
            # Sigmoid output is usually 0-1? Or linear?
            # If linear, we clamp it.
            # Assuming the model outputs a "next return" or "score".
            # Let's clip to -1 to 1 for safety.
            return np.clip(prediction, -1.0, 1.0)
        except Exception as e:
            print(f"AI Prediction Error: {e}")
            return 0.0

    def detect_market_regime(self, df: pd.DataFrame) -> dict:
        """
        Module 1: Market Regime Intelligence (Enhanced with Quantum Detection)
        """
        if df.empty: return {'type': 'Unknown', 'tradable': False}
        
        # Ensure indicators are calculated
        if 'atr' not in df.columns:
            from core.analysis import TechnicalAnalysis
            df = TechnicalAnalysis.calculate_indicators(df)
        
        # Use Quantum Engine for Regime Detection
        q_regime = self.quantum.detect_regime_quantum(df)
        
        row = df.iloc[-1]
        volatility_ratio = row.get('atr', 0) / row['close'] if 'atr' in row and row['close'] != 0 else 0
        adx = row.get('ADX_14', row.get('adx', 0))
        
        regime = 'Range Accumulation'
        tradable = True
        reason = "Normal market conditions"
        
        # Hybrid Logic
        if q_regime == "High Volatility (Unstable)":
            regime = self.regimes['vol_shock']
            tradable = False
            reason = "Quantum Volatility Detection Triggered"
        
        elif 'atr' in df.columns and row['atr'] > df['atr'].rolling(14).mean().iloc[-1] * 2.5:
             regime = self.regimes['vol_shock']
             tradable = False
             reason = "Extreme Volatility detected"
             
        elif 'bb_width' in df.columns and row['bb_width'] < 0.05:
             regime = self.regimes['vol_squeeze']
             reason = "Volatility Squeeze - Preparing for Breakout"
             
        elif adx > 30 and 'ema_50' in row and row['close'] > row['ema_50']:
            regime = self.regimes['trend_accel']
            
        elif adx > 45 and 'rsi' in row and (row['rsi'] > 75 or row['rsi'] < 25):
            regime = self.regimes['trend_exhaust']
            reason = "Trend potentially overextended"
            
        return {
            'type': regime,
            'tradable': tradable,
            'volatility_score': volatility_ratio,
            'reason': reason,
            'quantum_state': q_regime
        }

    def analyze_liquidity(self, order_book: dict) -> dict:
        """
        Module 2: Liquidity-Aware Decision Making
        Analyze bid/ask spread and depth.
        """
        if not order_book or 'bids' not in order_book or 'asks' not in order_book:
            return {'status': 'Unknown', 'score': 0}
            
        bids = order_book['bids']
        asks = order_book['asks']
        
        if not bids or not asks:
            return {'status': 'Low Liquidity', 'score': 0}
            
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        
        spread_pct = (best_ask - best_bid) / best_bid * 100
        
        # Score: Lower spread is better
        score = 1.0
        if spread_pct > 0.1: score = 0.5
        if spread_pct > 0.5: score = 0.1
        
        return {
            'spread_pct': spread_pct,
            'score': score,
            'status': 'Favorable' if score > 0.7 else 'Poor'
        }

    def cross_market_check(self, btc_df: pd.DataFrame, current_bias: str) -> bool:
        """
        Module 3: Correlation Guard (BTC Filter)
        If trading ALTs, ensure BTC is not crashing.
        """
        if btc_df.empty: return True # Cannot check
        
        # Simple Logic: If bias is LONG, BTC should not be below EMA50 or RSI < 40
        row = btc_df.iloc[-1]
        
        if current_bias == 'buy':
            # Avoid buying if BTC is crashing
            if 'ema_50' in btc_df.columns and row['close'] < row['ema_50']:
                # Allow if RSI is oversold (reversal play)
                if row['rsi'] < 30: return True
                return False
        
        elif current_bias == 'sell':
            # Avoid selling if BTC is pumping strongly
            if 'ema_50' in btc_df.columns and row['close'] > row['ema_50']:
                if row['rsi'] > 70: return True
                return False
                
        return True

    def check_safety_events(self) -> dict:
        """
        Module 4: Global Risk Events
        (Placeholder for news API or volatility index check)
        """
        return {'safe': True}

    def apply_behavioral_filter(self, last_trade_time) -> bool:
        """
        Module 5: Anti-FOMO / Overtrading Guard
        """
        if last_trade_time is None: return True
        
        # Ensure 5 mins between trades (scalping protection)
        import datetime
        if (datetime.datetime.now() - last_trade_time).seconds < 300:
            return False
            
        return True

    def predict_next_move(self, df: pd.DataFrame) -> dict:
        """
        ML-Based Price Prediction (Ensemble: Linear Regression + LSTM)
        """
        if len(df) < 50:
            return {'predicted_price': 0, 'confidence': 0}
            
        # 1. Prepare Data for Linear Regression
        df = df.copy()
        df['time_idx'] = np.arange(len(df))
        
        X = df[['time_idx']].values
        y = df['close'].values
        
        # Train on last 50 candles
        model_lr = LinearRegression()
        model_lr.fit(X[-50:], y[-50:])
        
        # Predict next candle (t+1)
        next_time_idx = X[-1][0] + 1
        pred_lr = model_lr.predict([[next_time_idx]])[0]
        
        # 2. Get LSTM Prediction (via AI Engine & Feature Store)
        # Use our robust get_ai_prediction method which handles normalization
        # Note: get_ai_prediction returns a score -1 to 1. 
        # We need to convert this to a price impact or percentage change.
        
        # Ensure features are computed if not present
        if 'returns' not in df.columns:
             # Assuming we have access to feature store or can compute on fly
             # For now, simplistic calculation to support the call
             df['returns'] = df['close'].pct_change()
             df['log_volume'] = np.log1p(df['volume'])
             df['high_low_pct'] = (df['high'] - df['low']) / df['close']
             # Add other missing cols with 0 if needed or rely on robust get_ai_prediction checks
             for col in ["rsi", "ema_50", "ema_200", "atr", "adx", "macd", "bollinger_width"]:
                 if col not in df.columns: df[col] = 0

        ai_score = self.get_ai_prediction(df) # -1 to 1
        
        # Interpret AI Score as predicted % move (e.g., strong buy = +1% move)
        # Conservative estimate: max +/- 1% per candle
        pred_lstm_impact = ai_score * 0.01 * df['close'].iloc[-1]
        pred_lstm_price = df['close'].iloc[-1] + pred_lstm_impact
        
        # Ensemble: 70% LR (Trend), 30% LSTM (AI)
        pred_final = (pred_lr * 0.7) + (pred_lstm_price * 0.3)
        
        current_price = df['close'].iloc[-1]
        predicted_change = (pred_final - current_price) / current_price
        
        # Simple confidence metric based on R-squared of Linear Regression
        r2 = model_lr.score(X[-50:], y[-50:])
        confidence = max(0, min(1, r2))
        
        # Boost confidence if AI agrees with Trend
        trend_direction = 1 if pred_lr > current_price else -1
        ai_direction = 1 if ai_score > 0 else -1
        
        if trend_direction == ai_direction and abs(ai_score) > 0.3:
            confidence = min(0.99, confidence + 0.2)
        
        return {
            'predicted_price': pred_final,
            'predicted_change_pct': predicted_change * 100,
            'confidence': confidence,
            'ensemble_score': confidence
        }

    def get_ensemble_signal(self, df: pd.DataFrame, technical_signal: dict, sentiment_score: float) -> dict:
        """
        The 'Master Mind' function combining all signals.
        Weights:
        - Technical Analysis: 40%
        - AI/ML Prediction: 30%
        - Sentiment Analysis: 20%
        - RL Agent: 10%
        """
        # 1. Technical Score (-10 to 10) -> Normalize to -1 to 1
        tech_norm = technical_signal.get('score', 0) / 10.0
        
        # 2. AI Prediction
        ml_data = self.predict_next_move(df)
        ml_change = ml_data['predicted_change_pct']
        # Cap at +/- 2% for normalization
        ml_norm = np.clip(ml_change, -2, 2) / 2.0
        
        # 3. Sentiment (-1 to 1)
        sent_norm = sentiment_score
        
        # 4. RL Agent
        # Construct real state for RL
        feature_cols = ["rsi", "ema_50", "ema_200", "atr", "adx", "macd", "bollinger_width", "returns", "log_volume", "high_low_pct"]
        rl_action = 0
        
        # Check if we have the features
        if all(col in df.columns for col in feature_cols) and len(df) > 20:
            current_state = df[feature_cols].iloc[-1].values.astype(np.float32)
            
            # Normalize state using recent history (similar to LSTM preprocessing)
            history = df[feature_cols].iloc[-20:].values.astype(np.float32)
            min_val = np.min(history, axis=0)
            max_val = np.max(history, axis=0)
            range_val = max_val - min_val
            range_val[range_val == 0] = 1.0
            
            normalized_state = (current_state - min_val) / range_val
            
            # Get Action from RL Agent
            rl_action = self.ai_engine.get_rl_action(normalized_state) # 0=Hold, 1=Buy, 2=Sell
            
        rl_norm = 0
        if rl_action == 1: rl_norm = 1   # Buy
        elif rl_action == 2: rl_norm = -1 # Sell
        
        # Ensemble Weighting
        final_score = (tech_norm * 0.4) + (ml_norm * 0.3) + (sent_norm * 0.2) + (rl_norm * 0.1)
        
        # Determine Final Decision
        decision = "HOLD"
        if final_score > 0.25: decision = "BUY"
        elif final_score < -0.25: decision = "SELL"
        
        return {
            'decision': decision,
            'final_score': final_score,
            'components': {
                'technical': tech_norm,
                'ml': ml_norm,
                'sentiment': sent_norm,
                'rl': rl_norm
            },
            'confidence': abs(final_score) # Simple confidence proxy
        }

    def generate_decision(self, signal, regime_data, liquidity_data, cross_market_valid, risk_data, safety_data, behavior_allowed, ensemble_score=None):
        """
        Final Gating Logic.
        Combines all checks to issue a final GO/NO-GO.
        """
        # 1. Global Safety Check
        if not safety_data.get('safe', True):
            return {'decision': 'WAIT', 'rejection_reason': 'Global Safety Event', 'confidence': 0}
            
        # 2. Behavioral Check
        if not behavior_allowed:
            return {'decision': 'WAIT', 'rejection_reason': 'Behavioral Filter (Cool-down)', 'confidence': 0}
            
        # 3. Liquidity Check
        if liquidity_data['status'] == 'Low Liquidity':
            return {'decision': 'WAIT', 'rejection_reason': 'Low Liquidity', 'confidence': 0}
            
        # 4. Cross Market Check
        if not cross_market_valid:
            return {'decision': 'WAIT', 'rejection_reason': 'Cross Market Divergence', 'confidence': 0}
            
        # 5. Market Regime Filter
        # Don't buy in 'Trend Exhaustion' or 'Structural Breakdown'
        if regime_data['type'] in ['Trend Exhaustion', 'Structural Breakdown'] and signal.type == 'buy':
             return {'decision': 'WAIT', 'rejection_reason': f"Bad Regime: {regime_data['type']}", 'confidence': 0}
             
        # 6. Ensemble Confirmation (if provided)
        final_confidence = 0.5
        if ensemble_score is not None:
             # If ensemble disagrees strongly, block
             if signal.type == 'buy' and ensemble_score < -0.1:
                 return {'decision': 'WAIT', 'rejection_reason': 'Ensemble Disagreement', 'confidence': abs(ensemble_score)}
             if signal.type == 'sell' and ensemble_score > 0.1:
                 return {'decision': 'WAIT', 'rejection_reason': 'Ensemble Disagreement', 'confidence': abs(ensemble_score)}
             final_confidence = abs(ensemble_score)
        
        return {
            'decision': 'EXECUTE',
            'confidence': final_confidence,
            'rejection_reason': '',
            'market_regime': regime_data['type']
        }
