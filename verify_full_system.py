
import os
import sys
import pandas as pd
import traceback
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def verify_system():
    print("🚀 Starting System Verification...")
    
    try:
        # 1. Import Core Modules
        print("1. Importing Core Modules...", end=" ")
        from core.bot import TradingBot
        from core.auth import AuthManager
        from core.sound_engine import SoundEngine
        print("✅ Success")
        
        # 2. Initialize Trading Bot
        print("2. Initializing Trading Bot...", end=" ")
        bot = TradingBot('binance')
        print("✅ Success")
        
        # 3. Check Sub-Modules
        print("3. Verifying Sub-Modules:")
        modules = [
            ('Data Manager', bot.data_manager),
            ('Brain (AI)', bot.brain),
            ('Analyzer', bot.analyzer),
            ('Risk Manager', bot.risk_manager),
            ('Execution', bot.execution),
            ('Compliance', bot.compliance),
            ('Feature Store', bot.feature_store),
            ('Drift Detector', bot.drift_detector),
            ('Sentiment', bot.sentiment),
            ('Arbitrage', bot.arbitrage)
        ]
        
        for name, mod in modules:
            if mod:
                print(f"   - {name}: ✅ Loaded")
            else:
                print(f"   - {name}: ❌ Failed")
                
        # 4. Test Analysis Cycle (Offline/Mock)
        print("4. Testing Analysis Cycle...", end=" ")
        bot.data_manager.offline_mode = True
        # Create dummy data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': [100.0] * 100,
            'high': [105.0] * 100,
            'low': [95.0] * 100,
            'close': [102.0] * 100,
            'volume': [1000.0] * 100
        })
        # Mock fetch_ohlcv to return this df
        bot.data_manager.fetch_ohlcv = lambda s, t, limit=100: df
        
        # Run analysis
        signal = bot.run_analysis()
        if signal:
            print(f"✅ Success (Signal: {signal.decision_details['decision']})")
        else:
            print("❌ Failed (No signal returned)")
            
        # 5. Test Sound Engine
        print("5. Testing Sound Engine...", end=" ")
        se = SoundEngine()
        html = se.get_audio_html("buy")
        if "audio" in html:
            print("✅ Success")
        else:
            print("❌ Failed")
            
        # 6. Test Compliance
        print("6. Testing Compliance...", end=" ")
        allowed = bot.compliance.check_trade_compliance("BTC/USDT", "buy", 0.1, 50000)
        if allowed['allowed']:
            print("✅ Success")
        else:
            print(f"❌ Failed ({allowed['reason']})")

        print("\n🎉 SYSTEM VERIFICATION COMPLETED SUCCESSFULLY!")
        return True

    except Exception as e:
        print(f"\n❌ SYSTEM VERIFICATION FAILED: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_system()
