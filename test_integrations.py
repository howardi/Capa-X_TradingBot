import unittest
from unittest.mock import patch, MagicMock
import json
import pandas as pd
from api.integrations import get_coin, get_coin_history
from api.analysis import MarketAnalyzer

class TestIntegrations(unittest.TestCase):
    
    @patch('api.integrations.requests.get')
    def test_get_coin_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"symbol": "BTC", "last_price_usd": 50000}
        mock_get.return_value = mock_response
        
        result = get_coin("BTC")
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["last_price_usd"], 50000)

    @patch('api.integrations.requests.get')
    def test_get_coin_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = get_coin("BTC")
        self.assertTrue("error" in result)

class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.analyzer = MarketAnalyzer()
        
    def test_analyze_empty(self):
        result = self.analyzer.analyze([])
        self.assertIsNone(result)
        
    def test_analyze_data(self):
        # Create dummy candle data
        candles = []
        base_time = 1600000000
        for i in range(300):
            candles.append({
                'time': base_time + i * 3600,
                'open': 100 + i,
                'high': 105 + i,
                'low': 95 + i,
                'close': 102 + i
            })
            
        df = self.analyzer.analyze(candles)
        self.assertIsNotNone(df)
        self.assertTrue('RSI' in df.columns)
        # EMA_50 should be present with 300 points
        self.assertTrue('EMA_50' in df.columns)
        
        # Test signal generation
        signal, confidence, reason = self.analyzer.get_signal(df)
        self.assertIn(signal, ['buy', 'sell', 'neutral'])

if __name__ == '__main__':
    unittest.main()
