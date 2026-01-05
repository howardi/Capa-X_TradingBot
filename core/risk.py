
import numpy as np
from config.trading_config import TRADING_CONFIG

class AdaptiveRiskManager:
    def __init__(self, initial_capital=1000.0):
        self.demo_balance = initial_capital
        self.live_balance = 0.0
        self.mode = 'Demo' # 'Demo', 'CEX_Proxy', 'CEX_Direct', 'DEX'

        self.metrics = {
            'Demo': {'max_drawdown': 0.0, 'win_streak': 0, 'loss_streak': 0, 'peak': initial_capital},
            'CEX_Proxy': {'max_drawdown': 0.0, 'win_streak': 0, 'loss_streak': 0, 'peak': 0.0},
            'CEX_Direct': {'max_drawdown': 0.0, 'win_streak': 0, 'loss_streak': 0, 'peak': 0.0},
            'DEX': {'max_drawdown': 0.0, 'win_streak': 0, 'loss_streak': 0, 'peak': 0.0}
        }
        
        self.base_risk_per_trade = TRADING_CONFIG['risk']['per_trade_risk_min']
        self.stop_loss_config = {'mode': 'atr', 'value': 1.5} # 'atr' (multiplier) or 'fixed' (percentage)
        self.take_profit_config = {'mode': 'atr', 'value': 3.0}
        self.monte_carlo_simulator = MonteCarloSimulator() # New Integration
        
        # New Constraints
        self.open_positions = []
        self.is_kill_switch_active = False
        self.max_dd = TRADING_CONFIG['risk']['kill_switch_drawdown'] # From config
        self.dd_triggered = False

    @property
    def current_capital(self):
        if self.mode == 'Demo':
            return self.demo_balance
        else:
            return self.live_balance

    @property
    def max_drawdown(self):
        return self.metrics[self.mode]['max_drawdown']

    @property
    def win_streak(self):
        return self.metrics[self.mode]['win_streak']

    @property
    def loss_streak(self):
        return self.metrics[self.mode]['loss_streak']

    def set_mode(self, mode):
        if mode in ['Demo', 'CEX_Proxy', 'CEX_Direct', 'DEX']:
            self.mode = mode
            # Initialize peak if 0
            if self.metrics[self.mode]['peak'] == 0.0:
                 if mode == 'Demo':
                     self.metrics[self.mode]['peak'] = self.demo_balance
                 else:
                     self.metrics[self.mode]['peak'] = self.live_balance

    def update_live_balance(self, balance):
        """Update Live Balance from Exchange"""
        self.live_balance = balance
        if self.mode in self.metrics:
            if balance > self.metrics[self.mode]['peak']:
                 self.metrics[self.mode]['peak'] = balance

    def check_kill_switch(self):
        """
        Check if global kill switch should be activated.
        """
        if self.max_drawdown >= TRADING_CONFIG['risk']['kill_switch_drawdown']:
            self.is_kill_switch_active = True
            return True
        return False

    def check_portfolio_limits(self, symbol, new_position_size):
        """
        Check against portfolio-wide constraints (Max Open Positions, Exposure).
        """
        if self.is_kill_switch_active:
            return False, "Kill Switch Active"

        if len(self.open_positions) >= TRADING_CONFIG['risk']['max_open_positions']:
            return False, "Max Open Positions Reached"

        # Future: Add Correlation Check here
        return True, "Allowed"

    def configure(self, risk_per_trade=None, stop_loss_pct=None, take_profit_pct=None, stop_atr_mult=None, tp_atr_mult=None):
        """
        Update risk parameters from UI/Settings.
        """
        if risk_per_trade is not None:
            self.base_risk_per_trade = risk_per_trade / 100.0 # Convert % to decimal
            
        if stop_loss_pct is not None:
            # If user sets a specific %, we switch to fixed mode
            self.stop_loss_config = {'mode': 'fixed', 'value': stop_loss_pct / 100.0}
        
        if stop_atr_mult is not None:
            # Switch to ATR mode with custom multiplier
            self.stop_loss_config = {'mode': 'atr', 'value': float(stop_atr_mult)}

        if take_profit_pct is not None:
            self.take_profit_config = {'mode': 'fixed', 'value': take_profit_pct / 100.0}
            
        if tp_atr_mult is not None:
            self.take_profit_config = {'mode': 'atr', 'value': float(tp_atr_mult)}

    def update_metrics(self, current_balance=None, last_trade_result=None, pnl_amount=0.0, capital_released=0.0):
        """Update metrics for the active mode with PnL amount"""
        if pnl_amount != 0.0 or capital_released != 0.0:
            if self.mode != 'Demo':
                self.live_balance += pnl_amount # Live balance is usually synced, but this helps simulations
                current_balance = self.live_balance
            else:
                self.demo_balance += (pnl_amount + capital_released)
                current_balance = self.demo_balance
        
        if current_balance is not None:
             # For backward compatibility if strictly passed, but we use internal state now
             pass
        
        # Drawdown Calc
        peak = max(self.metrics[self.mode]['peak'], self.current_capital)
        self.metrics[self.mode]['peak'] = peak # Update peak
        
        dd = (peak - self.current_capital) / peak if peak > 0 else 0
        self.metrics[self.mode]['max_drawdown'] = max(self.metrics[self.mode]['max_drawdown'], dd)
        
        # Check Kill Switch
        if dd >= TRADING_CONFIG['risk']['kill_switch_drawdown']:
            self.is_kill_switch_active = True

        # Streak Calc
        if last_trade_result == 'win':
            self.metrics[self.mode]['win_streak'] = self.metrics[self.mode].get('win_streak', 0) + 1
            self.metrics[self.mode]['loss_streak'] = 0
        elif last_trade_result == 'loss':
            self.metrics[self.mode]['loss_streak'] = self.metrics[self.mode].get('loss_streak', 0) + 1
            self.metrics[self.mode]['win_streak'] = 0

    def check_circuit_breakers(self, equity_start, equity_now):
        """
        Check if circuit breaker should trigger based on drawdown.
        Matches CapacityBay requirements.
        """
        if equity_start == 0: return True
        dd = 1 - (equity_now / equity_start)
        
        # Update internal metrics
        self.metrics[self.mode]['max_drawdown'] = max(self.metrics[self.mode]['max_drawdown'], dd)
        
        if dd >= self.max_dd:
            self.dd_triggered = True
            self.is_kill_switch_active = True
            
        return not self.dd_triggered

    def position_size(self, price, atr):
        """
        Calculate position size and stop distance.
        Matches CapacityBay requirements.
        """
        # Reuse existing logic but return tuple (qty, stop_distance)
        sl_data = self.calculate_dynamic_stops(price, atr, 'buy') # Side doesn't matter for distance
        stop_distance = abs(price - sl_data['stop_loss'])
        
        # If stop distance is 0 or tiny, prevent division by zero
        if stop_distance < 1e-8:
            return 0.0, stop_distance
            
        risk_calc = self.calculate_risk_size(atr, price, sl_data['stop_loss'])
        qty = risk_calc.get('position_size', 0.0)
        
        return qty, stop_distance

    def stop_take_levels(self, side, price, atr):
        """
        Get SL/TP levels.
        Matches CapacityBay requirements.
        """
        levels = self.calculate_dynamic_stops(price, atr, side)
        return levels['stop_loss'], levels['take_profit']

    def calculate_risk_size(self, volatility_atr, entry_price, stop_loss_price, regime="Normal"):
        """
        Dynamic Risk Sizing based on "Self-Adaptive Risk Control" module.
        Never increase risk during drawdown.
        """
        if self.is_kill_switch_active:
             return {'risk_pct': 0, 'risk_amount': 0, 'position_size': 0, 'reason': 'Kill Switch Active'}

        # 1. Base Risk
        risk_pct = self.base_risk_per_trade
        
        # 2. Drawdown Penalty
        # If in > 5% drawdown, reduce risk by half
        if self.max_drawdown > 0.05:
            risk_pct *= 0.5
            
        # 3. Streak Adjustment
        # If losing streak > 3, reduce risk
        if self.loss_streak > 3:
            risk_pct *= 0.5
            
        # 4. Volatility Regime Adjustment
        # Reduce risk in shock/extreme volatility to preserve capital
        if regime in ['Volatility Shock', 'Volatile', 'Extreme Volatility']:
            risk_pct *= 0.5
        elif regime == 'Trending':
            # Slightly increase risk in strong trends (Pyramiding logic potential)
            # But keep safe for now
            pass
            
        risk_amount = self.current_capital * risk_pct
        
        # Fee & Slippage Adjustment (Pre-Trade Cost Model)
        est_fees = risk_amount * (TRADING_CONFIG['fees']['taker'] + TRADING_CONFIG['fees']['slippage_est'])
        risk_amount -= est_fees # Reduce risk amount to account for costs

        # Calculate Position Size
        # Risk Amount = Size * (Entry - SL)
        # Size = Risk Amount / |Entry - SL|
        sl_distance = abs(entry_price - stop_loss_price)
        if sl_distance == 0: return {'risk_pct': 0, 'risk_amount': 0, 'position_size': 0}
        
        position_size = risk_amount / sl_distance
        
        return {
            'risk_pct': risk_pct,
            'risk_amount': risk_amount,
            'position_size': position_size
        }

    def calculate_dynamic_stops(self, entry_price: float, atr: float, side: str) -> dict:
        """
        Calculate safe Stop Loss and Take Profit levels based on volatility (ATR).
        Optimized for 1:2 or 1:3 Risk/Reward ratio.
        """
        # Default multipliers
        multiplier_sl = 1.5 
        multiplier_tp = 3.0
        
        # Use configured values if in ATR mode
        if self.stop_loss_config.get('mode') == 'atr':
            multiplier_sl = self.stop_loss_config.get('value', 1.5)
            
        if self.take_profit_config.get('mode') == 'atr':
            multiplier_tp = self.take_profit_config.get('value', 3.0)
        
        if side.lower() == 'buy':
            sl = entry_price - (atr * multiplier_sl)
            tp = entry_price + (atr * multiplier_tp)
        else:
            sl = entry_price + (atr * multiplier_sl)
            tp = entry_price - (atr * multiplier_tp)
            
        return {'stop_loss': sl, 'take_profit': tp}

class MonteCarloSimulator:
    """
    Advanced Risk Assessment using Monte Carlo Simulation.
    Projects potential future equity curves based on historical performance stats.
    """
    def __init__(self, num_simulations=1000, trade_count=100):
        self.num_simulations = num_simulations
        self.trade_count = trade_count

    def run_simulation(self, win_rate: float, avg_win: float, avg_loss: float, starting_equity: float) -> dict:
        """
        Run simulations to estimate Risk of Ruin and Expected Drawdown.
        """
        simulations = []
        
        for _ in range(self.num_simulations):
            equity_curve = [starting_equity]
            equity = starting_equity
            
            for _ in range(self.trade_count):
                # Random trade outcome
                if np.random.random() < win_rate:
                    equity += avg_win
                else:
                    equity -= abs(avg_loss)
                
                # Prevent negative equity
                if equity < 0: equity = 0
                equity_curve.append(equity)
                
            simulations.append(equity_curve)
            
        simulations = np.array(simulations)
        
        # Calculate Statistics
        final_equities = simulations[:, -1]
        ruin_count = np.sum(final_equities <= 0)
        risk_of_ruin = (ruin_count / self.num_simulations) * 100
        
        median_equity = np.median(final_equities)
        worst_case = np.min(final_equities)
        
        return {
            'risk_of_ruin_pct': risk_of_ruin,
            'median_expected_equity': median_equity,
            'worst_case_equity': worst_case,
            'simulations': simulations # For plotting
        }
