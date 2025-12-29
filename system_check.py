import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

# Ensure core modules are importable
sys.path.append(os.getcwd())

from core.bot import TradingBot
from core.data import DataManager
from core.risk import AdaptiveRiskManager
from core.execution import ExecutionEngine
from core.strategies import SniperStrategy
from core.defi import DeFiManager

class SystemIntegrityTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print("\n🚀 Starting System Integrity Check...")
        cls.bot = TradingBot(exchange_id='binance')
        # Force offline for safety during tests
        cls.bot.data_manager.offline_mode = True
        cls.bot.data_manager.use_yfinance_fallback = False 

    def test_01_bot_initialization(self):
        """Test Bot Initialization and default state"""
        self.assertIsNotNone(self.bot.data_manager)
        self.assertIsNotNone(self.bot.risk_manager)
        self.assertEqual(self.bot.trading_mode, 'Demo')
        print("✅ Bot Initialization")

    def test_02_mode_switching(self):
        """Test switching between all 4 trading modes"""
        modes = ['Demo', 'CEX_Proxy', 'CEX_Direct', 'DEX']
        for mode in modes:
            success = self.bot.set_trading_mode(mode)
            self.assertTrue(success)
            self.assertEqual(self.bot.trading_mode, mode)
            # Verify Risk Manager mode sync
            if mode == 'Demo':
                self.assertEqual(self.bot.risk_manager.mode, 'Demo')
            elif mode == 'CEX_Proxy':
                self.assertEqual(self.bot.risk_manager.mode, 'CEX_Proxy')
                # Verify Proxy was requested (mock check would be ideal, but we trust the setter for now)
            elif mode == 'CEX_Direct':
                self.assertEqual(self.bot.risk_manager.mode, 'CEX_Direct')
            elif mode == 'DEX':
                self.assertEqual(self.bot.risk_manager.mode, 'DEX')
        print("✅ Mode Switching")

    def test_03_risk_isolation(self):
        """Test that risk metrics are isolated per mode"""
        # Set to Demo
        self.bot.set_trading_mode('Demo')
        initial_demo_peak = self.bot.risk_manager.metrics['Demo']['peak']
        
        # Simulate a loss in Demo
        self.bot.risk_manager.update_metrics(pnl_amount=-100)
        self.assertLess(self.bot.risk_manager.demo_balance, initial_demo_peak)
        
        # Switch to CEX_Direct
        self.bot.set_trading_mode('CEX_Direct')
        # Ensure CEX_Direct metrics are untouched by Demo loss
        self.assertEqual(self.bot.risk_manager.metrics['CEX_Direct']['max_drawdown'], 0.0)
        
        print("✅ Risk Isolation")

    def test_04_execution_routing(self):
        """Test that execution engine routes to correct modules"""
        
        # Mock DataManager.create_order
        self.bot.data_manager.create_order = MagicMock(return_value={'id': '123', 'status': 'open'})
        
        # 1. Test Demo Routing
        self.bot.set_trading_mode('Demo')
        result = self.bot.execution.execute_smart_order('BTC/USDT', 'buy', 0.1, 'market')
        self.assertEqual(result['status'], 'Filled') # Demo always fills immediately in simulation
        
        # 2. Test CEX Routing
        self.bot.set_trading_mode('CEX_Direct')
        result = self.bot.execution.execute_smart_order('BTC/USDT', 'buy', 0.1, 'market')
        self.bot.data_manager.create_order.assert_called()
        
        # 3. Test DEX Routing
        self.bot.set_trading_mode('DEX')
        # Mock DeFi execute_swap
        self.bot.defi.execute_swap = MagicMock(return_value={'status': 'success', 'tx_hash': '0x123'})
        result = self.bot.execution.execute_smart_order('ETH/USDT', 'buy', 1.0, 'market')
        self.bot.defi.execute_swap.assert_called()
        
        print("✅ Execution Routing")

    def test_05_strategy_logic(self):
        """Test SniperStrategy signal generation"""
        strategy = SniperStrategy(self.bot)
        
        # Mock Data
        df = pd.DataFrame({
            'open': [100.0] * 200,
            'high': [105.0] * 200,
            'low': [95.0] * 200,
            'close': [102.0] * 200,
            'volume': [1000.0] * 200
        })
        
        # Inject data
        self.bot.data_manager.fetch_ohlcv = MagicMock(return_value=df)
        
        # Mock Feature Store
        self.bot.feature_store.compute_features = MagicMock(return_value=df)
        
        # Mock Brain
        self.bot.brain.get_ai_prediction = MagicMock(return_value=0.5)
        
        # Run execute (should not crash)
        try:
            signal = strategy.execute('BTC/USDT')
            # Signal might be None or a Signal object, just checking for no crash
            pass
        except Exception as e:
            self.fail(f"Strategy Execution crashed: {e}")
            
        print("✅ Strategy Logic")

    def test_06_defi_wrappers(self):
        """Test DeFi Manager wrappers"""
        defi = DeFiManager()
        
        # Test Swap Wrapper logic
        with patch.object(defi, 'swap_tokens') as mock_swap:
            defi.execute_swap('ETH/USDT', 'buy', 1.0)
            mock_swap.assert_called_with('USDT', 'ETH', 1.0) # Buy ETH with USDT
            
            defi.execute_swap('ETH/USDT', 'sell', 1.0)
            mock_swap.assert_called_with('ETH', 'USDT', 1.0) # Sell ETH for USDT
            
        print("✅ DeFi Wrappers")

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
