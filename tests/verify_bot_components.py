
import unittest
from unittest.mock import MagicMock
import pandas as pd
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.risk import AdaptiveRiskManager
from core.auto_trader import AutoTrader
from core.strategies import SmartTrendStrategy
from core.models import Signal

class TestBotComponents(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.symbol = "BTC/USDT"
        self.bot.timeframe = "1h"
        self.bot.trading_mode = "paper"
        self.bot.positions = {"paper": []}
        self.bot.save_positions = MagicMock()
        
        # Mock DataManager
        self.bot.data_manager = MagicMock()
        self.bot.data_manager.fetch_ohlcv.return_value = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [95, 96, 97],
            'close': [102, 103, 104],
            'volume': [1000, 1100, 1200]
        })
        
        # Real RiskManager
        self.bot.risk_manager = AdaptiveRiskManager(initial_capital=10000)
        self.bot.risk_manager.set_mode('Demo')
        
        # Mock Execution
        self.bot.execution = MagicMock()
        self.bot.execution.place.return_value = {
            'id': '123', 'status': 'filled', 'price': 104, 'qty': 0.1
        }
        
        # Mock Analyzer and Brain for Strategy
        self.bot.analyzer = MagicMock()
        self.bot.analyzer.calculate_indicators.return_value = pd.DataFrame({
            'close': [104], 'atr': [2.0], 'rsi': [30], 'ema_50': [110], 'macd': [1], 'macd_signal': [0]
        })
        self.bot.analyzer.get_signal.return_value = {
            'type': 'buy', 'score': 8, 'reason': 'Test Signal', 'indicators': {}
        }
        self.bot.brain = MagicMock()
        self.bot.brain.detect_market_regime.return_value = {'type': 'Trending'}
        self.bot.log_trade = MagicMock()

    def test_risk_circuit_breaker(self):
        print("\nTesting Risk Management Circuit Breakers...")
        risk = self.bot.risk_manager
        
        # Initial State
        start_equity = 10000
        current_equity = 10000
        self.assertTrue(risk.check_circuit_breakers(start_equity, current_equity))
        
        # 5% Drawdown (Below Limit)
        current_equity = 9500
        self.assertTrue(risk.check_circuit_breakers(start_equity, current_equity))
        
        # 15% Drawdown (Above Limit - Default Kill Switch is usually 10-15%)
        # Let's check config default in risk.py, usually it's around 0.10 or 0.15
        # We can force set it for test
        risk.max_dd = 0.10 # 10%
        
        current_equity = 8000 # 20% DD
        self.assertFalse(risk.check_circuit_breakers(start_equity, current_equity))
        self.assertTrue(risk.is_kill_switch_active)
        print("Circuit Breaker Triggered Successfully.")

    def test_auto_trader_integration(self):
        print("\nTesting AutoTrader Integration...")
        auto_trader = AutoTrader(self.bot)
        
        # Verify Strategy is SmartTrend
        self.assertIsInstance(auto_trader.signal, SmartTrendStrategy)
        
        # Mock Strategy Execute to return a Signal
        signal_obj = Signal(
            symbol="BTC/USDT", type="buy", price=104, timestamp=pd.Timestamp.now(),
            reason="Test", indicators={}, score=8, regime="Trending",
            liquidity_status="Normal", confidence=0.8, decision_details={'test': True}
        )
        auto_trader.signal.execute = MagicMock(return_value=signal_obj)
        
        # Run Once
        auto_trader.run_once("BTC/USDT")
        
        # Verify Execution
        self.bot.execution.place.assert_called()
        print("AutoTrader successfully processed signal and executed trade.")

if __name__ == '__main__':
    unittest.main()
