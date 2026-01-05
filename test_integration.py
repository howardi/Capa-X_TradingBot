import os
import sys
import pandas as pd
import numpy as np
from core.brain import CapacityBayBrain
from core.chaos import ChaosMonkey
from core.quantum import QuantumEngine
from core.defi import DeFiManager

# Mock Bot class to pass to ChaosMonkey
class MockBot:
    def __init__(self):
        self.symbol = "BTC/USD"
        self.timeframe = "1h"
        self.active = True
        self.data = pd.DataFrame()
    
    def fetch_data(self):
        print("MockBot: Fetching data...")
        # Create dummy data
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='h')
        self.data = pd.DataFrame({
            'open': np.random.randn(100) + 50000,
            'high': np.random.randn(100) + 51000,
            'low': np.random.randn(100) + 49000,
            'close': np.random.randn(100) + 50000,
            'volume': np.random.randn(100) + 1000
        }, index=dates)
        return self.data

def test_quantum_brain():
    print("Testing Quantum Brain...")
    brain = CapacityBayBrain()
    
    # Create dummy market data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='h')
    df = pd.DataFrame({
        'open': np.random.randn(100) + 100,
        'high': np.random.randn(100) + 105,
        'low': np.random.randn(100) + 95,
        'close': np.random.randn(100) + 100,
        'volume': np.random.randn(100) * 1000 + 10000,
        'atr': np.random.rand(100) * 5
    }, index=dates)
    
    # Test regime detection
    regime = brain.detect_market_regime(df)
    print(f"Detected Regime: {regime}")
    
    # Test Quantum Portfolio Optimization (Annealing)
    print("Testing Quantum Annealing...")
    assets = ['BTC', 'ETH', 'SOL']
    # Create dummy returns for 3 assets
    returns_df = pd.DataFrame(np.random.randn(100, 3) * 0.01, columns=assets)
    
    weights = brain.quantum.simulated_annealing_portfolio(assets, returns_df)
    print(f"Optimized Weights: {weights}")
    
    assert 'type' in regime
    assert 'quantum_state' in regime
    assert len(weights) == 3
    assert abs(sum(weights.values()) - 1.0) < 0.01 # Weights sum to 1
    print("Quantum Brain Test Passed.")

def test_chaos_monkey():
    print("\nTesting Chaos Monkey...")
    bot = MockBot()
    monkey = ChaosMonkey(bot)
    
    # Test mild chaos
    result = monkey.unleash_chaos(level='mild')
    print(f"Chaos Result: {result}")
    
    assert 'status' in result
    assert 'type' in result
    print("Chaos Monkey Test Passed.")

if __name__ == "__main__":
    try:
        test_quantum_brain()
        test_chaos_monkey()
        print("\nAll System Tests Passed Successfully.")
    except Exception as e:
        print(f"\nTest Failed: {e}")
        sys.exit(1)
