import unittest
import sys
import os

# Add the project root to the python path so we can import api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.services.strategy_service import StrategyService

class TestStrategyService(unittest.TestCase):
    def setUp(self):
        self.service = StrategyService()

    def test_stoch_rsi_calculation(self):
        # Create a dummy RSI series
        # Pattern that goes up then down
        rsi_data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 80, 70, 60, 50, 40, 30, 20]
        # We need enough data for period=14
        # Just ensure it doesn't crash
        k, d = self.service._stoch_rsi(rsi_data, period=5, k_period=3, d_period=3)
        self.assertEqual(len(k), len(rsi_data))
        self.assertEqual(len(d), len(rsi_data))
        
        # Check values are normalized 0-1 (roughly, depending on SMA smoothing)
        # The _sma function might smooth them, but intermediate stoch_rsi is 0-1.
        # k and d should be valid numbers
        for val in k:
            self.assertTrue(0 <= val <= 1, f"K value {val} out of range")

    def test_combined_ai_buy_signal(self):
        # Construct a scenario for a BUY signal
        # RSI < 30 (Oversold)
        # MACD Bullish
        # Price below Lower BB
        
        # Generate data: Downtrend then sharp drop
        closes = [100 - i for i in range(50)] # 100, 99, 98...
        # Sudden drop to trigger oversold
        closes.extend([50, 48, 45, 40, 38, 35]) 
        
        # High volume on the drop/reversal? 
        # Actually to get positive volume score, current > avg * 1.5
        volumes = [1000] * 55
        volumes.append(5000) # Spike
        
        result = self.service.combined_ai(closes, volumes)
        
        print(f"\nBuy Signal Test Result: {result}")
        
        # We expect a score that might trigger buy or at least be positive
        # RSI will be low (Buy +2)
        # Price likely below BB lower (Buy +1)
        # Volume high (Buy +1 if score > 0)
        
        # Note: MACD might be bearish because of the drop, but let's see.
        
        self.assertIn('signal', result)
        self.assertIn('confidence', result)
        self.assertIn('reason', result)

    def test_combined_ai_sell_signal(self):
        # Construct a scenario for a SELL signal
        # RSI > 70
        # Price above Upper BB
        
        closes = [10 + i for i in range(50)] # 10, 11, 12...
        # Sharp spike
        closes.extend([70, 75, 80, 85, 90, 95])
        
        volumes = [1000] * 55
        volumes.append(5000)
        
        result = self.service.combined_ai(closes, volumes)
        
        print(f"\nSell Signal Test Result: {result}")
        
        self.assertIn('signal', result)
        
    def test_analyze_integration(self):
        candles = [{'close': 100 + i, 'volume': 1000} for i in range(30)]
        result = self.service.analyze('combined_ai', candles)
        print(f"\nIntegration Test Result: {result}")
        self.assertTrue(isinstance(result, dict))
        self.assertIn('signal', result)

if __name__ == '__main__':
    unittest.main()
