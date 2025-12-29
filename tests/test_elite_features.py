
import unittest
import pandas as pd
import numpy as np
from datetime import datetime
from core.brain import CapaXBrain
from core.risk import AdaptiveRiskManager
from core.bot import TradingBot
from core.models import Signal

class TestCapaXEliteFeatures(unittest.TestCase):
    def setUp(self):
        self.brain = CapaXBrain()
        self.risk = AdaptiveRiskManager(initial_capital=10000)
        # Mock Data Creation
        self.dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
        self.df = pd.DataFrame({
            'timestamp': self.dates,
            'open': np.random.randn(100) + 50000,
            'high': np.random.randn(100) + 51000,
            'low': np.random.randn(100) + 49000,
            'close': np.linspace(50000, 55000, 100), # Uptrend
            'volume': np.random.randint(100, 1000, 100)
        })
        # Add indicators needed for Brain
        self.df['atr'] = 500.0 # Mock ATR
        self.df['ema_50'] = self.df['close'] * 0.95 # Price above EMA
        self.df['ADX_14'] = 35.0 # Strong Trend
        self.df['rsi'] = 60.0

    def test_market_regime_intelligence(self):
        print("\nTesting Market Regime Intelligence...")
        regime = self.brain.detect_market_regime(self.df)
        print(f"Detected Regime: {regime}")
        # With price > EMA and ADX > 30, should be Trend Acceleration or similar
        self.assertIn(regime['type'], ['Trend Acceleration', 'Range Accumulation'])
        self.assertTrue(regime['tradable'])

    def test_liquidity_analysis(self):
        print("\nTesting Liquidity Analysis...")
        # Mock Order Book
        order_book = {
            'bids': [[49990, 1.0]],
            'asks': [[50010, 1.0]]
        } # Spread = 20 / 49990 ~= 0.04% (Very tight)
        
        analysis = self.brain.analyze_liquidity(order_book)
        print(f"Liquidity Analysis: {analysis}")
        self.assertGreater(analysis['score'], 0.8)
        self.assertEqual(analysis['status'], 'Favorable')

    def test_adaptive_risk_manager(self):
        print("\nTesting Adaptive Risk Manager...")
        # Test 1: Normal conditions
        risk_res = self.risk.calculate_risk_size(volatility_atr=500, entry_price=50000, stop_loss_price=49000)
        initial_risk_amount = risk_res['risk_amount']
        print(f"Initial Risk Amount: ${initial_risk_amount}")
        
        # Test 2: After Drawdown > 5%
        self.risk.current_capital = 9000 # 10% Drawdown
        self.risk.update_metrics(9000) # Update max_dd
        
        risk_res_dd = self.risk.calculate_risk_size(volatility_atr=500, entry_price=50000, stop_loss_price=49000)
        print(f"Risk Amount after Drawdown: ${risk_res_dd['risk_amount']}")
        
        # Should be half of base risk (approx, accounting for capital drop too)
        # Base: 10000 * 1% = 100. Drawdown: 9000 * 0.5% = 45.
        self.assertTrue(risk_res_dd['risk_amount'] < initial_risk_amount)

    def test_decision_gating(self):
        print("\nTesting Final Decision Gating...")
        # Mock inputs
        signal_mock = type('obj', (object,), {'type': 'buy'})
        regime_data = {'type': 'Trend Acceleration', 'tradable': True}
        liquidity_data = {'score': 0.9, 'status': 'Favorable'}
        cross_market = True
        risk_data = {'risk_pct': 0.01, 'risk_amount': 100, 'position_size': 0.1}
        
        decision = self.brain.generate_decision(
            signal=signal_mock,
            regime_data=regime_data,
            liquidity_data=liquidity_data,
            cross_market_valid=cross_market,
            risk_data=risk_data
        )
        
        print(f"Decision Output: {decision}")
        self.assertEqual(decision['decision'], 'EXECUTE')
        self.assertGreater(decision['confidence'], 0.75)

if __name__ == '__main__':
    unittest.main()
