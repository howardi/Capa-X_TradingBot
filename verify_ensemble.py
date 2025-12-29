import pandas as pd
from core.bot import TradingBot

def verify_ensemble():
    print("Initializing TradingBot...")
    bot = TradingBot()
    
    # Mock Data for testing
    print("Mocking Data...")
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq='1h')
    data = {
        'timestamp': dates,
        'open': [100 + i for i in range(200)],
        'high': [105 + i for i in range(200)],
        'low': [95 + i for i in range(200)],
        'close': [102 + i for i in range(200)],
        'volume': [1000 for _ in range(200)]
    }
    df = pd.DataFrame(data)
    
    # Mock fetch_ohlcv to return this data
    bot.data_manager.fetch_ohlcv = lambda s, t, limit: df
    
    # Mock Order Book
    bot.data_manager.fetch_order_book = lambda s, limit: {'bids': [[100, 1]], 'asks': [[101, 1]]}
    
    # Mock Sentiment
    bot.sentiment.analyze_sentiment = lambda s: {'score': 80, 'classification': 'Bullish', 'trending_topics': [], 'sources_analyzed': 100}
    
    # Run Strategy
    print("Running Smart Trend Strategy...")
    bot.set_strategy("Smart Trend")
    signal = bot.run_analysis()
    
    if signal:
        print("\n--- Signal Generated ---")
        print(f"Type: {signal.type}")
        print(f"Confidence: {signal.confidence}")
        print(f"Decision Details: {signal.decision_details}")
        
        comps = signal.decision_details.get('components', {})
        print(f"\nEnsemble Components:")
        print(f"Technical: {comps.get('technical')}")
        print(f"ML: {comps.get('ml')}")
        print(f"Sentiment: {comps.get('sentiment')}")
        print(f"RL: {comps.get('rl')}")
        
        if 'ensemble_score' in signal.decision_details or 'final_score' in signal.decision_details:
             print("\nSUCCESS: Ensemble Score found in decision details.")
        else:
             print("\nWARNING: Ensemble Score NOT found.")
    else:
        print("No signal generated.")

if __name__ == "__main__":
    verify_ensemble()
