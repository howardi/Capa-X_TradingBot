import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    try:
        import pandas_ta_classic as ta
    except ImportError:
        ta = None
        print("⚠️ pandas_ta not found. Analysis disabled.")

class MarketAnalyzer:
    def __init__(self):
        pass

    def analyze(self, candles_data):
        """
        Analyze market data and return technical indicators.
        candles_data: List of dictionaries [{'time': ..., 'open': ..., 'high': ..., 'low': ..., 'close': ...}]
        """
        if not candles_data:
            return None
            
        if ta is None:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(candles_data)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Ensure numeric columns
        cols = ['open', 'high', 'low', 'close']
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 1. RSI (Relative Strength Index)
        df['RSI'] = df.ta.rsi(length=14)

        # 2. MACD (Moving Average Convergence Divergence)
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)

        # 3. Bollinger Bands
        bbands = df.ta.bbands(length=20, std=2)
        if bbands is not None:
            df = pd.concat([df, bbands], axis=1)

        # 4. EMA (Exponential Moving Average) - Trend Filter
        try:
            ema50 = df.ta.ema(length=50)
            if ema50 is not None and not isinstance(ema50, pd.DataFrame):
                df['EMA_50'] = ema50
            
            ema200 = df.ta.ema(length=200)
            if ema200 is not None and not isinstance(ema200, pd.DataFrame):
                df['EMA_200'] = ema200
        except Exception as e:
            print(f"Error calculating EMA: {e}")
        
        # 5. ATR (Average True Range) - For Volatility
        df['ATR'] = df.ta.atr(length=14)

        # 6. ADX (Average Directional Index) - Trend Strength
        adx = df.ta.adx(length=14)
        if adx is not None:
            df['ADX'] = adx['ADX_14']

        # 7. Stochastic RSI
        try:
            stoch_rsi = df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3)
            if stoch_rsi is not None and not stoch_rsi.empty:
                # pandas_ta returns columns like STOCHk_..., STOCHd_...
                # We'll take the first two columns assuming they are k and d
                df['STOCHk'] = stoch_rsi.iloc[:, 0]
                df['STOCHd'] = stoch_rsi.iloc[:, 1]
        except Exception as e:
            print(f"Error calculating StochRSI: {e}")

        return df

    def get_market_sentiment(self):
        """Simulate NLP Sentiment Analysis."""
        import random
        sentiments = ["positive", "neutral", "negative"]
        return random.choice(sentiments)

    def get_quantum_prob(self):
        """Simulate Quantum Probability Engine."""
        import random
        return random.uniform(0.4, 0.99)

    def get_signal(self, df):
        """
        Generate a trading signal based on analysis.
        Returns: 
        - signal: 'buy', 'sell', 'neutral'
        - confidence: 0.0 to 1.0
        - reason: Text explanation
        """
        if df is None or df.empty:
            return 'neutral', 0.0, "No Data"

        # Get latest row
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        signal = 'neutral'
        confidence = 0.0
        reasons = []

        # Advanced Engines
        sentiment = self.get_market_sentiment()
        quantum_prob = self.get_quantum_prob()

        # Extract Values
        rsi = last_row.get('RSI_14', 50)
        
        # MACD
        macd_line = last_row.get('MACD_12_26_9', 0)
        macd_signal = last_row.get('MACDs_12_26_9', 0)
        prev_macd_line = prev_row.get('MACD_12_26_9', 0)
        prev_macd_signal = prev_row.get('MACDs_12_26_9', 0)

        # Bollinger Bands
        bb_lower = last_row.get('BBL_20_2.0', 0)
        bb_upper = last_row.get('BBU_20_2.0', 0)
        close_price = last_row['close']

        # Trend (EMA)
        ema_50 = last_row.get('EMA_50', 0)
        ema_200 = last_row.get('EMA_200', 0)
        trend = "bullish" if ema_50 > ema_200 else "bearish"

        # ADX & StochRSI
        adx = last_row.get('ADX', 0)
        stoch_k = last_row.get('STOCHk', 50)
        stoch_d = last_row.get('STOCHd', 50)

        # --- BUY LOGIC ---
        buy_score = 0
        
        # 1. RSI Oversold (< 30 is standard, < 40 is aggressive)
        if rsi < 30:
            buy_score += 2
            reasons.append("RSI Oversold")
        elif rsi < 40:
            buy_score += 1

        # 2. MACD Bullish Crossover
        if prev_macd_line < prev_macd_signal and macd_line > macd_signal:
            buy_score += 3
            reasons.append("MACD Crossover")
        elif macd_line > macd_signal:
            buy_score += 1

        # 3. Price near Lower Bollinger Band
        if close_price <= bb_lower * 1.01: 
            buy_score += 2
            reasons.append("Price at Lower Band")

        # 4. Trend Confirmation
        if trend == "bullish" and close_price > ema_50:
             buy_score += 1
             reasons.append("Uptrend")

        # 5. Stochastic RSI Oversold
        if stoch_k < 20 and stoch_d < 20:
            buy_score += 2
            reasons.append("StochRSI Oversold")
        elif stoch_k > stoch_d and stoch_k < 80: # Momentum up
            buy_score += 1

        # 6. ADX Strong Trend
        if adx > 25:
            buy_score += 1
            reasons.append("Strong Trend (ADX>25)")

        # --- SELL LOGIC ---
        sell_score = 0

        # Quantum/Sentiment Sell
        if quantum_prob < 0.5:
             sell_score += 1
        if sentiment == "negative":
             sell_score += 1
             reasons.append("Negative Sentiment")

        # 1. RSI Overbought (> 70)
        if rsi > 70:
            sell_score += 2
            reasons.append("RSI Overbought")
        elif rsi > 60:
            sell_score += 1
            
        # 2. MACD Bearish Crossover
        if prev_macd_line > prev_macd_signal and macd_line < macd_signal:
            sell_score += 3
            reasons.append("MACD Bearish Cross")
        elif macd_line < macd_signal:
            sell_score += 1

        # 3. Price near Upper Bollinger Band
        if close_price >= bb_upper * 0.99:
            sell_score += 2
            reasons.append("Price at Upper Band")
            
        # 4. Stochastic RSI Overbought
        if stoch_k > 80 and stoch_d > 80:
            sell_score += 2
            reasons.append("StochRSI Overbought")
            
        # Decision
        # Max Possible Score: 2+3+2+1+2+1 = 11
        # Threshold: 6 for high confidence
        
        if buy_score >= 6:
            signal = 'buy'
            confidence = min(buy_score / 10.0, 0.98) 
        elif sell_score >= 6:
            signal = 'sell'
            confidence = min(sell_score / 10.0, 0.98)
        elif buy_score >= 4: # Weak Buy
             signal = 'buy'
             confidence = 0.5
             reasons.append("(Weak Signal)")
        elif sell_score >= 4: # Weak Sell
             signal = 'sell'
             confidence = 0.5
             reasons.append("(Weak Signal)")
        else:
            signal = 'neutral'
            confidence = 0.0

        return signal, confidence, ", ".join(reasons)
