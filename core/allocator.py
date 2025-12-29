
import numpy as np
import pandas as pd
from collections import deque

class ProfitOptimizer:
    """
    Profit Optimization Layer (POL).
    Uses Contextual Multi-Armed Bandits to dynamically allocate capital 
    based on strategy performance and market regime.
    """
    def __init__(self, strategies, lookback_window=50):
        self.strategies = strategies
        self.lookback_window = lookback_window
        
        # Performance History: {strategy: deque of trade_results}
        self.history = {s: deque(maxlen=lookback_window) for s in strategies}
        
        # Contextual Scores: {regime: {strategy: {'alpha': 1.0, 'beta': 1.0}}}
        # Regimes: 'Trend', 'Range', 'Volatile', 'Unknown'
        self.regimes = ['Trend', 'Range', 'Volatile', 'Unknown']
        self.context_scores = {
            r: {s: {'alpha': 1.0, 'beta': 1.0} for s in strategies} 
            for r in self.regimes
        }
        
        # Global Metrics
        self.metrics = {
            s: {
                'sharpe': 0.0, 
                'sortino': 0.0, 
                'max_drawdown': 0.0, 
                'win_rate': 0.0,
                'total_pnl': 0.0
            } for s in strategies
        }

    def update(self, strategy_name, pnl, regime='Unknown'):
        """
        Update the optimizer with trade results.
        pnl: Percentage return of the trade (e.g., 0.05 for 5%)
        """
        if strategy_name not in self.strategies:
            return
            
        # 1. Update History
        self.history[strategy_name].append(pnl)
        
        # 2. Update Contextual Bandit Scores
        # Map complex regime names to simple categories
        simple_regime = 'Unknown'
        if 'Trend' in regime or 'Accel' in regime: simple_regime = 'Trend'
        elif 'Range' in regime or 'Accum' in regime: simple_regime = 'Range'
        elif 'Volat' in regime or 'Shock' in regime: simple_regime = 'Volatile'
        
        # Reward shaping: Sigmoid-like scaling of PnL to 0-1 range for Beta update
        # We want small wins to be good, big wins better, losses bad.
        # Simple heuristic: Win = Alpha+, Loss = Beta+
        # Weighted by magnitude?
        
        magnitude = min(abs(pnl) * 10, 2.0) # Cap magnitude boost
        
        if pnl > 0:
            self.context_scores[simple_regime][strategy_name]['alpha'] += (1.0 + magnitude)
        else:
            self.context_scores[simple_regime][strategy_name]['beta'] += (1.0 + magnitude)
            
        # 3. Recalculate Metrics
        self._recalculate_metrics(strategy_name)

    def _recalculate_metrics(self, strategy_name):
        returns = list(self.history[strategy_name])
        if not returns:
            return
            
        returns_np = np.array(returns)
        
        # Win Rate
        wins = np.sum(returns_np > 0)
        total = len(returns_np)
        self.metrics[strategy_name]['win_rate'] = (wins / total) * 100
        self.metrics[strategy_name]['total_pnl'] = np.sum(returns_np)
        
        # Sharpe (Simplified)
        std_dev = np.std(returns_np)
        avg_ret = np.mean(returns_np)
        if std_dev > 0:
            self.metrics[strategy_name]['sharpe'] = avg_ret / std_dev * np.sqrt(len(returns_np)) # Annualized approx
        else:
            self.metrics[strategy_name]['sharpe'] = 0.0
            
        # Sortino (Downside Deviation)
        downside = returns_np[returns_np < 0]
        if len(downside) > 0:
            down_std = np.std(downside)
            if down_std > 0:
                self.metrics[strategy_name]['sortino'] = avg_ret / down_std * np.sqrt(len(returns_np))
        
        # Max Drawdown
        cum_ret = np.cumsum(returns_np)
        peak = np.maximum.accumulate(cum_ret)
        dd = peak - cum_ret
        self.metrics[strategy_name]['max_drawdown'] = np.max(dd) if len(dd) > 0 else 0.0

    def get_allocation_weights(self, current_regime='Unknown'):
        """
        Get capital allocation weights based on current market regime.
        Returns dict: {strategy: weight_pct}
        """
        # Map regime
        simple_regime = 'Unknown'
        if 'Trend' in current_regime or 'Accel' in current_regime: simple_regime = 'Trend'
        elif 'Range' in current_regime or 'Accum' in current_regime: simple_regime = 'Range'
        elif 'Volat' in current_regime or 'Shock' in current_regime: simple_regime = 'Volatile'
        
        samples = {}
        for s in self.strategies:
            params = self.context_scores[simple_regime][s]
            
            # Thompson Sampling with Penalty
            # Sample from Beta
            raw_sample = np.random.beta(params['alpha'], params['beta'])
            
            # Apply Penalties based on Metrics
            # Penalty for High Drawdown (> 5%)
            dd_penalty = 1.0
            if self.metrics[s]['max_drawdown'] > 0.05:
                dd_penalty = 0.5
            elif self.metrics[s]['max_drawdown'] > 0.10:
                dd_penalty = 0.1
                
            # Penalty for Low Sharpe (< 0.5)
            sharpe_penalty = 1.0
            if self.metrics[s]['sharpe'] < 0.5:
                sharpe_penalty = 0.8
                
            samples[s] = raw_sample * dd_penalty * sharpe_penalty
            
        total_score = sum(samples.values())
        
        # Softmax-like normalization or simple ratio
        if total_score == 0:
            return {s: 1.0/len(self.strategies) for s in self.strategies}
            
        weights = {s: val/total_score for s, val in samples.items()}
        
        # Filter out very small weights to reduce noise (Capital < 5% -> 0)
        final_weights = {}
        cleaned_total = 0
        for s, w in weights.items():
            if w > 0.05:
                final_weights[s] = w
                cleaned_total += w
            else:
                final_weights[s] = 0.0
                
        # Re-normalize
        if cleaned_total > 0:
            for s in final_weights:
                final_weights[s] /= cleaned_total
                
        return final_weights

    def get_best_strategy(self, current_regime='Unknown'):
        weights = self.get_allocation_weights(current_regime)
        return max(weights, key=weights.get)
