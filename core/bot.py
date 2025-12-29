
import time
from datetime import datetime
import pandas as pd
from core.data import DataManager
from core.analysis import TechnicalAnalysis
from core.fundamentals import FundamentalAnalysis
from core.models import Signal
from core.brain import CapaXBrain
from core.risk import AdaptiveRiskManager
from core.quantum import QuantumEngine
from core.strategies import (
    SmartTrendStrategy, GridTradingStrategy, MeanReversionStrategy, 
    FundingArbitrageStrategy, BasisTradeStrategy, LiquiditySweepStrategy, OrderFlowStrategy,
    SwingRangeStrategy, SniperStrategy
)
from core.arbitrage import ArbitrageScanner
from core.sentiment import SentimentEngine
from core.execution import ExecutionEngine
from core.security import SecurityManager
from core.defi import DeFiManager
from core.alerts import NotificationManager
from core.ai import PortfolioOptimizer, DriftDetector
from core.ai_optimizer import AITrainer
from core.allocator import ProfitOptimizer
from core.ml_predictor import EnsemblePredictor
from core.feature_store import FeatureStore
from core.compliance import ComplianceManager
from config.settings import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME

import json
import os

class TradingBot:
    def __init__(self, exchange_id='binance'):
        self.data_manager = DataManager(exchange_id)
        self.analyzer = TechnicalAnalysis()
        self.fundamentals = FundamentalAnalysis()
        self.brain = CapaXBrain()
        self.risk_manager = AdaptiveRiskManager()
        self.quantum = QuantumEngine()
        self.security = SecurityManager()
        
        # New Modules
        self.arbitrage = ArbitrageScanner()
        self.sentiment = SentimentEngine()
        self.execution = ExecutionEngine(self)
        self.defi = DeFiManager()
        self.notifications = NotificationManager()
        self.portfolio_opt = PortfolioOptimizer()
        self.feature_store = FeatureStore()
        self.compliance = ComplianceManager(self)
        self.drift_detector = DriftDetector()
        self.ai_trainer = AITrainer(self)
        
        self.is_running = False
        self.symbol = DEFAULT_SYMBOL
        self.timeframe = DEFAULT_TIMEFRAME
        self.trading_mode = 'Demo' # Default to Demo
        self.last_trade_time = None
        self.trade_log_file = "trade_log.json"
        
        self.positions_file = "active_positions.json"
        # Initialize positions for all 4 modes
        self.positions = {
            'Demo': [], 
            'CEX_Proxy': [], 
            'CEX_Direct': [], 
            'DEX': []
        }
        self.load_positions()
        
        # Initialize Strategies
        self.strategies = {
            "Smart Trend": SmartTrendStrategy(self),
            "Sniper Mode": SniperStrategy(self),
            "Grid Trading": GridTradingStrategy(self),
            "Mean Reversion": MeanReversionStrategy(self),
            "Funding Arbitrage": FundingArbitrageStrategy(self),
            "Basis Trade": BasisTradeStrategy(self),
            "Liquidity Sweep": LiquiditySweepStrategy(self),
            "Order Flow": OrderFlowStrategy(self),
            "Swing Range": SwingRangeStrategy(self)
        }
        self.active_strategy_name = "Smart Trend"
        self.active_strategy = self.strategies[self.active_strategy_name]
        
        # Initialize Profit Optimizer (Contextual Multi-Armed Bandit)
        self.profit_optimizer = ProfitOptimizer(list(self.strategies.keys()))
        
    @property
    def open_positions(self):
        """Return the list of positions for the active trading mode"""
        return self.positions.get(self.trading_mode, [])
    
    @open_positions.setter
    def open_positions(self, value):
        """Set positions (mostly for initialization or clearing)"""
        self.positions[self.trading_mode] = value

    def load_positions(self):
        """Load active positions from file to persist state across restarts"""
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    data = json.load(f)
                    
                    # Migration Logic: Old formats to New
                    if 'Simulation' in data:
                        if 'Demo' not in data: data['Demo'] = data.pop('Simulation')
                    if 'Live' in data:
                         # Default legacy 'Live' to 'CEX_Direct' if undefined, or keep as is?
                         # Let's map Live -> CEX_Direct for safety
                        if 'CEX_Direct' not in data: data['CEX_Direct'] = data.pop('Live')
                        
                    # Ensure all keys exist
                    for mode in ['Demo', 'CEX_Proxy', 'CEX_Direct', 'DEX']:
                        if mode not in data:
                            data[mode] = []
                            
                    self.positions = data
            
            # Sync with Risk Manager
            self.risk_manager.open_positions = self.positions.get(self.trading_mode, [])
            
        except Exception as e:
            print(f"Failed to load positions: {e}")

    def save_positions(self):
        """Save active positions to file"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=4)
        except Exception as e:
            print(f"Failed to save positions: {e}")

    def set_trading_mode(self, mode):
        """Switch between 4 Trading Environments"""
        valid_modes = ['Demo', 'CEX_Proxy', 'CEX_Direct', 'DEX']
        
        if mode in valid_modes:
            print(f"🔄 Switching Trading Mode: {self.trading_mode} -> {mode}")
            self.trading_mode = mode
            
            # 1. Configure Risk Manager Mode
            # Pass the specific mode to Risk Manager (Demo, CEX_Proxy, CEX_Direct, DEX)
            self.risk_manager.set_mode(mode)
            
            # 2. Configure Connection / Proxy
            if mode == 'CEX_Proxy':
                self.data_manager.set_proxy_mode(use_proxy=True)
            elif mode == 'CEX_Direct':
                self.data_manager.set_proxy_mode(use_proxy=False)
            elif mode == 'DEX':
                # DEX Logic (might not need DataManager proxy change, but let's default to no proxy for RPC)
                # Unless RPC requires it? Usually not.
                self.data_manager.set_proxy_mode(use_proxy=False)
            
            # 3. Sync positions to Risk Manager
            self.risk_manager.open_positions = self.positions.get(mode, [])
            
            # 4. Sync Balance
            if mode != 'Demo':
                self.sync_live_balance()
            else:
                print(f"Demo Balance: ${self.risk_manager.current_capital:.2f}")
                
            return True
        else:
            print(f"❌ Invalid Mode: {mode}")
            return False

    def sync_live_balance(self):
        """Fetch real balance from exchange/chain and update risk manager"""
        try:
            if self.trading_mode == 'DEX':
                # Fetch Wallet Balance via DeFi Manager
                if self.defi.account or (self.defi.current_chain == 'solana'):
                    # 1. Get Native Balance (e.g., 1.5 ETH)
                    native_bal = self.defi.get_balance()
                    
                    # 2. Get Price in USD (e.g., ETH/USDT)
                    chain_config = self.defi.CHAINS.get(self.defi.current_chain, {})
                    native_symbol = chain_config.get('symbol', 'ETH')
                    pair_symbol = f"{native_symbol}/USDT"
                    
                    price = self.data_manager.get_current_price(pair_symbol)
                    
                    # 3. Calculate USD Value
                    if price > 0:
                        usd_bal = native_bal * price
                        print(f"Synced DEX Balance: {native_bal:.4f} {native_symbol} (~${usd_bal:.2f})")
                        self.risk_manager.update_live_balance(usd_bal)
                    else:
                        print(f"⚠️ Could not fetch price for {pair_symbol}. Balance: {native_bal:.4f} {native_symbol}")
                        # Fallback: Don't update USD balance or update with 0? 
                        # Better to keep previous or 0 if completely unknown.
                        # For now, let's update with 0 if price is missing to be safe
                        self.risk_manager.update_live_balance(0.0) 
                else:
                    print("⚠️ No Wallet Loaded for DEX Mode")
            
            elif self.trading_mode in ['CEX_Proxy', 'CEX_Direct']:
                balance = self.data_manager.get_balance()
                # Try USDT first, then USD
                usdt_bal = balance.get('USDT', {}).get('total', 0.0)
                if usdt_bal == 0.0:
                     usdt_bal = balance.get('USD', {}).get('total', 0.0)
                
                self.risk_manager.update_live_balance(usdt_bal)
                print(f"Synced Live Balance ({self.trading_mode}): ${usdt_bal:.2f}")
                
        except Exception as e:
            print(f"Failed to sync live balance: {e}")

    def set_strategy(self, strategy_name):
        if strategy_name == "Meta-Allocator" or strategy_name in self.strategies:
            self.active_strategy_name = strategy_name
            if strategy_name in self.strategies:
                self.active_strategy = self.strategies[strategy_name]
            return True
        return False

    def log_trade(self, decision_packet):
        """
        Self-Audit: Record trade details for post-trade review.
        """
        import numpy as np
        
        # Helper to convert numpy types to native types
        def convert_numpy(obj):
            if isinstance(obj, (np.integer, int)):
                return int(obj)
            elif isinstance(obj, (np.floating, float)):
                return float(obj)
            elif isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            return obj

        # Sanitize packet
        clean_packet = {k: convert_numpy(v) for k, v in decision_packet.items()}
        if 'components' in clean_packet:
            clean_packet['components'] = {k: convert_numpy(v) for k, v in clean_packet['components'].items()}

        trade_record = {
            "timestamp": str(datetime.now()),
            "symbol": self.symbol,
            "type": clean_packet.get('bias', 'UNKNOWN'),
            "strategy": clean_packet.get('strategy', 'Unknown'),
            "entry": clean_packet.get('entry', 0),
            "stop_loss": clean_packet.get('stop_loss', 0),
            "take_profit": clean_packet.get('take_profit', 0),
            "risk_percent": clean_packet.get('risk_percent', 0),
            "confidence": clean_packet.get('confidence', 0),
            "regime": clean_packet.get('market_regime', 'Unknown'),
            "execution_score": clean_packet.get('execution_score', 0),
            "components": clean_packet.get('components', {}),
            "audit_status": "OPEN"
        }
        
        try:
            if os.path.exists(self.trade_log_file):
                try:
                    with open(self.trade_log_file, 'r') as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    print("Warning: trade_log.json corrupted. specific trade log will be reset.")
                    logs = []
            else:
                logs = []
                
            logs.append(trade_record)
            
            with open(self.trade_log_file, 'w') as f:
                json.dump(logs, f, indent=4)
                
            # Track Open Position in Memory
            if decision_packet.get('decision') == 'EXECUTE':
                self.open_positions.append({
                    "symbol": self.symbol,
                    "type": decision_packet.get('bias', 'UNKNOWN'),
                    "entry": decision_packet.get('entry', 0),
                    "stop_loss": decision_packet.get('stop_loss', 0),
                    "take_profit": decision_packet.get('take_profit', 0),
                    "strategy": decision_packet.get('strategy', 'Unknown'),
                    "position_size": decision_packet.get('position_size', 0)
                })
                self.save_positions()
                
        except Exception as e:
            print(f"Failed to log trade: {e}")

    def update_positions(self, current_price):
        """
        Check open positions for Stop Loss or Take Profit hits.
        """
        for position in self.open_positions[:]: # Iterate copy to allow removal
            symbol = position['symbol']
            bias = position['type']
            entry = position['entry']
            sl = position['stop_loss']
            tp = position['take_profit']
            
            # Simple simulation logic
            closed = False
            reason = ""
            pnl = 0.0
            
            if bias == 'BUY':
                if current_price <= sl and sl > 0:
                    closed = True
                    reason = "Stop Loss"
                    pnl = (sl - entry) / entry
                elif current_price >= tp and tp > 0:
                    closed = True
                    reason = "Take Profit"
                    pnl = (tp - entry) / entry
            elif bias == 'SELL':
                if current_price >= sl and sl > 0:
                    closed = True
                    reason = "Stop Loss"
                    pnl = (entry - sl) / entry
                elif current_price <= tp and tp > 0:
                    closed = True
                    reason = "Take Profit"
                    pnl = (entry - tp) / entry
                    
            if closed:
                print(f"Position Closed: {symbol} {bias} | {reason} @ {current_price} | PnL: {pnl:.2%}")
                self.open_positions.remove(position)
                self.save_positions()
                
                # Calculate Real PnL Amount
                pos_size = position.get('position_size', 0)
                pnl_amount = 0.0
                if bias == 'BUY':
                    pnl_amount = (current_price - entry) * pos_size
                elif bias == 'SELL':
                    pnl_amount = (entry - current_price) * pos_size
                
                trade_result = 'win' if pnl_amount > 0 else 'loss'
                
                # Update Balance in Risk Manager
                capital_released = entry * pos_size
                self.risk_manager.update_metrics(pnl_amount=pnl_amount, last_trade_result=trade_result, capital_released=capital_released)
                
                # Update Profit Optimizer
                if position.get('strategy'):
                    # Retrieve regime from position if stored, else Unknown
                    regime = position.get('regime', 'Unknown')
                    self.profit_optimizer.update(position['strategy'], pnl, regime)
                    
                # Log Close (Simplified)
                # self.log_trade({...}) # Ideally log the close event too

    def run_analysis(self, df=None):
        """
        Execute the selected strategy's logic
        """
        # Fetch raw data centrally if not provided
        if df is None:
            df = self.data_manager.fetch_ohlcv(self.symbol, self.timeframe, limit=200)
        
        if df.empty:
            return None

        # Feature Store: Compute/Retrieve Features
        # This ensures training and serving use the exact same logic
        df_features = self.feature_store.compute_features(df)
        
        # Update Positions (Check SL/TP)
        current_price = df['close'].iloc[-1]
        self.update_positions(current_price)
        
        # MLOps: Check for Data Drift
        drift_result = self.drift_detector.check_drift(df_features)
        if drift_result['status'] in ['moderate_drift', 'severe_drift']:
            print(f"Warning: {drift_result['status']} detected. Score: {drift_result['score']:.2f}")
            # In a real system, this would trigger a retraining pipeline via Airflow/Celery
        
        # Determine Strategy to Run
        strategy_to_run = self.active_strategy
        
        # Detect Regime for Allocation
        regime_data = self.brain.detect_market_regime(df)
        current_regime = regime_data.get('type', 'Unknown')
        
        allocation_weight = 1.0
        
        if self.active_strategy_name == "Profit Optimization Layer":
            # Profit Optimization Mode: Use Bandit to select best strategy
            weights = self.profit_optimizer.get_allocation_weights(current_regime)
            
            # Select strategy with highest weight
            best_strategy_name = max(weights, key=weights.get)
            strategy_to_run = self.strategies.get(best_strategy_name)
            allocation_weight = weights.get(best_strategy_name, 1.0)
            
            # Optional: Log allocation
            # print(f"Profit Optimizer chose: {best_strategy_name} (Weight: {allocation_weight:.2f})")

        # Delegate to the strategy
        if strategy_to_run:
            signal = strategy_to_run.execute(self.symbol, data=df_features)
            
            # Risk & Compliance: Post-Signal Checks
            if signal and signal.type in ['buy', 'sell']:
                # Apply Allocation Weight to Position Size
                if self.active_strategy_name == "Profit Optimization Layer":
                     # Scale position size by allocation weight
                     # We treat weight as a confidence scalar for the max allowed risk
                     original_size = signal.decision_details.get('position_size', 0)
                     adjusted_size = original_size * allocation_weight
                     signal.decision_details['position_size'] = adjusted_size
                     signal.decision_details['allocation_weight'] = allocation_weight
                     signal.decision_details['optimization_mode'] = True

                # Check Compliance (Kill-Switches, Restricted Assets, Limits)
                compliance_check = self.compliance.check_trade_compliance(
                    self.symbol, 
                    signal.type, 
                    signal.decision_details.get('risk_amount', 0), # Amount/Risk
                    signal.price
                )
                
                if not compliance_check['allowed']:
                    print(f"Compliance Block: {compliance_check['reason']}")
                    # Override signal to HOLD
                    signal.type = 'hold'
                    signal.reason = f"Compliance Blocked: {compliance_check['reason']}"
            
            return signal
        else:
            return None

    def start(self):
        self.is_running = True
        print("Capa-X System Activated...")

    def stop(self):
        self.is_running = False
        print("Capa-X System Deactivated...")

    def emergency_stop(self):
        print("🚨 EMERGENCY STOP TRIGGERED 🚨")
        self.is_running = False
        
        # Iterate over all modes to ensure everything is closed
        for mode in ['Live', 'Simulation']:
            # Get positions directly from dictionary to ensure we have the list
            positions = self.positions.get(mode, [])
            
            # Iterate over a copy to safely modify the list
            for position in positions[:]:
                symbol = position['symbol']
                bias = position['type']
                entry = position['entry']
                
                # Close Position Logic
                if mode == 'Live':
                    # Determine side to close
                    side = 'sell' if str(bias).upper() == 'BUY' else 'buy'
                    amount = float(position.get('position_size', 0))
                    
                    if amount > 0:
                        print(f"Executing LIVE Emergency Close: {symbol} {side} {amount}")
                        # Execute Market Order to close immediately
                        self.execution.execute_smart_order(symbol, side, amount, strategy='market')
                
                # Fetch current price for PnL log (Informational)
                try:
                    ticker = self.data_manager.fetch_ticker(symbol)
                    current_price = ticker['last']
                except:
                    current_price = entry 
                
                pnl = 0.0
                pnl_amount = 0.0
                pos_size = float(position.get('position_size', 0))
                
                if bias == 'BUY':
                    pnl = (current_price - entry) / entry
                    pnl_amount = (current_price - entry) * pos_size
                elif bias == 'SELL':
                    pnl = (entry - current_price) / entry
                    pnl_amount = (entry - current_price) * pos_size
                    
                print(f"🚨 Emergency Close ({mode}): {symbol} {bias} | PnL: {pnl:.2%} (${pnl_amount:.2f})")
                
                # Update Risk Manager Balance
                self.risk_manager.update_metrics(pnl_amount=pnl_amount, last_trade_result='win' if pnl_amount > 0 else 'loss', capital_released=entry*pos_size)
                
                # Log closure
                self.log_trade({
                    'decision': 'EMERGENCY_CLOSE',
                    'bias': 'FLAT',
                    'strategy': 'Kill Switch',
                    'symbol': symbol,
                    'entry': entry,
                    'exit_price': current_price,
                    'pnl': pnl,
                    'mode': mode
                })
            
            # Clear positions for this mode
            self.positions[mode] = []
            
        self.save_positions()
        
        # Sync Risk Manager
        self.risk_manager.open_positions = []
        
        return True
