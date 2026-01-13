import math
import numpy as np

# Try importing AIEngine
try:
    from core.ai import AIEngine
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: Core AI module not found. Advanced AI disabled.")

class StrategyService:
    def __init__(self):
        self.strategies = {
            'sma_crossover': self.sma_crossover,
            'rsi_momentum': self.rsi_momentum,
            'macd_trend': self.macd_trend,
            'combined_ai': self.combined_ai,
            'advanced_ai': self.advanced_ai_analysis
        }
        
        self.ai_engine = None
        if AI_AVAILABLE:
            try:
                self.ai_engine = AIEngine()
            except Exception as e:
                print(f"Failed to initialize AI Engine: {e}")


    # --- Helpers ---
    def _sma(self, data, period):
        if len(data) < period:
            return [0.0] * len(data)
        sma = []
        for i in range(len(data)):
            if i < period - 1:
                sma.append(0.0)
            else:
                window = data[i - period + 1 : i + 1]
                sma.append(sum(window) / period)
        return sma

    def _rsi(self, data, period=14):
        if len(data) < period + 1:
            return [50.0] * len(data) # Default neutral
        
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [abs(d) if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi_list = [50.0] * period # Pad initial
        
        if avg_loss == 0:
            rsi_list.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_list.append(100.0 - (100.0 / (1.0 + rs)))
            
        # Smooth subsequent
        for i in range(period, len(deltas)):
            gain = gains[i]
            loss = losses[i]
            
            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period
            
            if avg_loss == 0:
                rsi_list.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_list.append(100.0 - (100.0 / (1.0 + rs)))
                
        return rsi_list

    def _ema(self, data, period):
        if len(data) < period:
            return [0.0] * len(data)
        
        k = 2 / (period + 1)
        ema = [data[0]] # Initialize with first price
        
        for i in range(1, len(data)):
            val = (data[i] * k) + (ema[-1] * (1 - k))
            ema.append(val)
            
        return ema

    def _macd(self, data):
        # Standard MACD 12, 26, 9
        ema_12 = self._ema(data, 12)
        ema_26 = self._ema(data, 26)
        
        macd_line = [e12 - e26 for e12, e26 in zip(ema_12, ema_26)]
        signal_line = self._ema(macd_line, 9)
        
        return macd_line, signal_line

    def _bollinger_bands(self, data, period=20, std_dev=2):
        if len(data) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0}
        
        sma = self._sma(data, period)[-1]
        
        # Calculate Standard Deviation
        window = data[-period:]
        variance = sum([((x - sma) ** 2) for x in window]) / period
        std = variance ** 0.5
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return {'upper': upper, 'middle': sma, 'lower': lower}

    def _stoch_rsi(self, rsi_data, period=14, k_period=3, d_period=3):
        if len(rsi_data) < period:
            return [0.5] * len(rsi_data), [0.5] * len(rsi_data)
            
        stoch_rsi = []
        for i in range(len(rsi_data)):
            if i < period - 1:
                stoch_rsi.append(0.5)
            else:
                window = rsi_data[i - period + 1 : i + 1]
                min_val = min(window)
                max_val = max(window)
                if max_val - min_val == 0:
                    stoch_rsi.append(0.5)
                else:
                    stoch_rsi.append((rsi_data[i] - min_val) / (max_val - min_val))
                    
        k = self._sma(stoch_rsi, k_period)
        d = self._sma(k, d_period)
        return k, d

    def analyze(self, strategy_name, candles):
        """
        Run a specific strategy on candle data.
        candles: list of dicts {'open', 'high', 'low', 'close', 'volume'}
        """
        if not candles:
             return {'signal': 'neutral', 'confidence': 0.0, 'reason': 'No Data'}

        closes = [c['close'] for c in candles]
        volumes = [c.get('volume', 0) for c in candles]
        
        if strategy_name == 'combined_ai':
            return self.combined_ai(closes, volumes)
            
        if strategy_name == 'advanced_ai':
             return self.advanced_ai_analysis(closes, volumes)

        if strategy_name not in self.strategies:
            # Fallback to combined_ai if strategy not found
            return self.combined_ai(closes, volumes)

        return self.strategies[strategy_name](closes)

    def combined_ai(self, closes, volumes=None):
        """
        AI Ensemble Strategy (RSI + MACD + SMA + Bollinger + StochRSI + Volume)
        Target: 80-95% Win Rate
        """
        # 1. RSI
        rsi_series = self._rsi(closes)
        rsi = rsi_series[-1]
        
        # 2. Stoch RSI
        k_line, d_line = self._stoch_rsi(rsi_series)
        stoch_k = k_line[-1]
        stoch_d = d_line[-1]
        
        # 3. MACD
        macd_line, signal_line = self._macd(closes)
        macd = macd_line[-1]
        sig = signal_line[-1]
        
        # 4. Bollinger Bands
        bb = self._bollinger_bands(closes)
        last_price = closes[-1]
        
        # 5. SMA Trend
        sma_short = self._sma(closes, 10)[-1]
        sma_long = self._sma(closes, 50)[-1]
        
        # 6. Volume Analysis (if available)
        vol_score = 0
        if volumes and len(volumes) > 1:
            avg_vol = sum(volumes[-10:]) / 10 if len(volumes) >= 10 else sum(volumes) / len(volumes)
            current_vol = volumes[-1]
            if current_vol > avg_vol * 1.5:
                vol_score = 1 # High volume confirmation
        
        score = 0
        reasons = []
        
        # --- Scoring Logic ---
        
        # RSI Logic (Weight: 2)
        if rsi < 30: 
            score += 2
            reasons.append(f"RSI Oversold ({rsi:.1f})")
        elif rsi > 70: 
            score -= 2
            reasons.append(f"RSI Overbought ({rsi:.1f})")
            
        # Stoch RSI Logic (Weight: 1)
        if stoch_k < 0.2 and stoch_d < 0.2 and stoch_k > stoch_d: # Bullish Cross in Oversold
            score += 1.5
            reasons.append("StochRSI Bull Cross")
        elif stoch_k > 0.8 and stoch_d > 0.8 and stoch_k < stoch_d: # Bearish Cross in Overbought
            score -= 1.5
            reasons.append("StochRSI Bear Cross")
            
        # MACD Logic (Weight: 2)
        if macd > sig:
            if macd < 0: # Bullish reversal below zero line is stronger
                score += 2
                reasons.append("MACD Bull Reversal")
            else:
                score += 1
                reasons.append("MACD Bullish")
        else:
            if macd > 0: # Bearish reversal above zero line is stronger
                score -= 2
                reasons.append("MACD Bear Reversal")
            else:
                score -= 1
                reasons.append("MACD Bearish")
            
        # Bollinger Logic (Weight: 2)
        if last_price < bb['lower']: 
            score += 2
            reasons.append("Price < BB Lower")
        elif last_price > bb['upper']: 
            score -= 2
            reasons.append("Price > BB Upper")
            
        # SMA Trend (Weight: 1)
        if sma_short > sma_long:
            score += 1
        else:
            score -= 1
            
        # Volume Confirmation
        if score > 0 and vol_score > 0:
            score += 1
            reasons.append("High Volume Buy")
        elif score < 0 and vol_score > 0:
            score -= 1
            reasons.append("High Volume Sell")
            
        # Decision
        # Max theoretical score approx: 2(RSI) + 1.5(Stoch) + 2(MACD) + 2(BB) + 1(SMA) + 1(Vol) = 9.5
        confidence = min(abs(score) / 8.0, 0.99) 
        
        indicators = {
            'rsi': rsi,
            'sma_10': sma_short,
            'sma_50': sma_long,
            'sentiment': 'positive' if score > 0 else 'negative' if score < 0 else 'neutral',
            'quantum_prob': 0.0 # Placeholder
        }

        if score >= 3.5:
            return {'signal': 'buy', 'confidence': confidence, 'reason': ' + '.join(reasons), 'indicators': indicators}
        elif score <= -3.5:
            return {'signal': 'sell', 'confidence': confidence, 'reason': ' + '.join(reasons), 'indicators': indicators}
            
        return {'signal': 'neutral', 'confidence': confidence, 'reason': 'Consolidation / Mixed Signals', 'indicators': indicators}


    def sma_crossover(self, closes):
        sma_10 = self._sma(closes, 10)
        sma_30 = self._sma(closes, 30)
        
        if len(closes) < 30:
             return {'signal': 'neutral', 'confidence': 0.0, 'reason': 'Not enough data'}

        last_idx = -1
        prev_idx = -2
        
        # Bullish Crossover
        if sma_10[prev_idx] < sma_30[prev_idx] and sma_10[last_idx] > sma_30[last_idx]:
            return {'signal': 'buy', 'confidence': 0.8, 'reason': 'SMA Crossover'}
        # Bearish Crossover
        elif sma_10[prev_idx] > sma_30[prev_idx] and sma_10[last_idx] < sma_30[last_idx]:
            return {'signal': 'sell', 'confidence': 0.8, 'reason': 'SMA Crossover'}
            
        return {'signal': 'neutral', 'confidence': 0.0, 'reason': 'SMA Crossover'}

    def rsi_momentum(self, closes):
        rsi = self._rsi(closes, 14)
        last_rsi = rsi[-1]
        
        if last_rsi < 30:
            return {'signal': 'buy', 'confidence': 0.9, 'reason': f'RSI Oversold ({last_rsi:.1f})'}
        elif last_rsi > 70:
            return {'signal': 'sell', 'confidence': 0.9, 'reason': f'RSI Overbought ({last_rsi:.1f})'}
            
        return {'signal': 'neutral', 'confidence': 0.0, 'reason': 'RSI Neutral'}

    def macd_trend(self, closes):
        macd_line, signal_line = self._macd(closes)
        
        last_macd = macd_line[-1]
        last_signal = signal_line[-1]
        
        if last_macd > last_signal and last_macd > 0:
             return {'signal': 'buy', 'confidence': 0.7, 'reason': 'MACD Bullish'}
        elif last_macd < last_signal and last_macd < 0:
             return {'signal': 'sell', 'confidence': 0.7, 'reason': 'MACD Bearish'}
             
        return {'signal': 'neutral', 'confidence': 0.0, 'reason': 'MACD Neutral'}

    def advanced_ai_analysis(self, closes, volumes=None):
        """
        Integrates Deep Learning (LSTM/Transformer) with Traditional Technical Analysis.
        """
        # 1. Get Baseline from Traditional AI
        base_result = self.combined_ai(closes, volumes)
        base_signal = base_result['signal']
        base_conf = base_result['confidence']
        reasons = [base_result['reason']]
        
        if not self.ai_engine or not AI_AVAILABLE:
            return base_result
            
        # 2. Prepare Data for Deep Learning Models
        # We need at least 50 points to calculate indicators and have a sequence
        if len(closes) < 50:
            return base_result
            
        try:
            # Calculate Indicators for Features
            rsi = self._rsi(closes)
            macd, signal = self._macd(closes)
            sma10 = self._sma(closes, 10)
            sma50 = self._sma(closes, 50)
            
            # Normalize Data (Simple Min-Max for the window)
            def normalize(data):
                min_val = min(data)
                max_val = max(data)
                if max_val - min_val == 0: return [0.5] * len(data)
                return [(x - min_val) / (max_val - min_val) for x in data]
                
            norm_closes = normalize(closes)
            norm_vol = normalize(volumes) if volumes else [0] * len(closes)
            norm_rsi = [x / 100.0 for x in rsi] # RSI is 0-100
            
            # Construct Feature Matrix (Last 10 steps for LSTM context)
            seq_len = 10
            features = []
            for i in range(seq_len):
                idx = -(seq_len - i) # -10, -9, ... -1
                row = [
                    norm_closes[idx],
                    norm_vol[idx] if idx < len(norm_vol) else 0,
                    norm_rsi[idx],
                    macd[idx], # MACD/Signal are not strictly bounded, but usually small
                    signal[idx],
                    sma10[idx] / closes[idx] if closes[idx] else 0, # Normalize by price
                    sma50[idx] / closes[idx] if closes[idx] else 0,
                    0, 0, 0 # Padding for 10 dims
                ]
                features.append(row)
                
            feature_array = np.array(features, dtype=np.float32)
            
            # 3. Get Model Predictions
            lstm_pred = self.ai_engine.predict_next_price_lstm(feature_array)
            sentiment_score = self.ai_engine.predict_sentiment_transformer(feature_array)
            
            # 4. Interpret Predictions
            current_price = closes[-1]
            
            # LSTM Interpretation (Normalized output, so we check direction relative to last input)
            # Since LSTM output is abstract in this un-trained state, we simulate logic:
            # If we were training, we'd denormalize. Here we assume output > last_input means up.
            lstm_signal = 0
            if lstm_pred > feature_array[-1][0]: # Compare with last normalized close
                lstm_signal = 1 # Bullish
                reasons.append("LSTM Price Up")
            else:
                lstm_signal = -1 # Bearish
                reasons.append("LSTM Price Down")
                
            # Transformer Sentiment (Assuming output is -1 to 1 or similar)
            # Placeholder model output might be random, but let's assume it's a "probability of up"
            sentiment_signal = 0
            if sentiment_score > 0.5:
                sentiment_signal = 1
                reasons.append("AI Sentiment Bullish")
            elif sentiment_score < -0.5:
                sentiment_signal = -1
                reasons.append("AI Sentiment Bearish")
                
            # 5. Fuse Signals
            # Weighted Ensemble: Traditional (50%), LSTM (30%), Transformer (20%)
            
            # Convert base to score (-1 to 1)
            base_score = 0
            if base_signal == 'buy': base_score = base_conf
            elif base_signal == 'sell': base_score = -base_conf
            
            final_score = (base_score * 0.5) + (lstm_signal * 0.3) + (sentiment_signal * 0.2)
            
            final_conf = abs(final_score)
            final_signal = 'neutral'
            if final_score > 0.2: final_signal = 'buy'
            elif final_score < -0.2: final_signal = 'sell'
            
            return {
                'signal': final_signal,
                'confidence': min(final_conf, 0.99),
                'reason': ' | '.join(reasons)
            }
            
        except Exception as e:
            print(f"Advanced AI Error: {e}")
            return base_result

    # --- Advanced Analytics ---

    def analyze_orderbook(self, orderbook):
        """
        Analyze Order Book for Support/Resistance and Sentiment.
        orderbook: {'bids': [[price, size], ...], 'asks': [[price, size], ...]}
        """
        try:
            bids = orderbook['bids']
            asks = orderbook['asks']
            
            if not bids or not asks:
                return {'sentiment': 'neutral', 'spread': 0.0, 'imbalance': 0.0}
            
            # 1. Spread Analysis
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100
            
            # 2. Depth/Wall Analysis (Top 10 levels)
            bid_vol = sum([float(x[1]) for x in bids[:10]])
            ask_vol = sum([float(x[1]) for x in asks[:10]])
            
            # Imbalance Ratio (-1 to 1)
            # Positive = Buy Pressure (More bids)
            # Negative = Sell Pressure (More asks)
            total_vol = bid_vol + ask_vol
            imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0
            
            sentiment = 'neutral'
            if imbalance > 0.2: sentiment = 'bullish'
            elif imbalance < -0.2: sentiment = 'bearish'
            
            return {
                'sentiment': sentiment,
                'spread': spread,
                'spread_pct': spread_pct,
                'bid_volume': bid_vol,
                'ask_volume': ask_vol,
                'imbalance_ratio': imbalance,
                'buy_wall': bid_vol > (ask_vol * 1.5),
                'sell_wall': ask_vol > (bid_vol * 1.5)
            }
        except Exception as e:
            return {'error': str(e)}

    def calculate_risk_metrics(self, trades):
        """
        Calculate Portfolio Risk Metrics.
        trades: list of dicts {'pnl': float, 'amount': float}
        """
        if not trades:
            return {'sharpe_ratio': 0.0, 'max_drawdown': 0.0, 'win_rate': 0.0, 'total_pnl': 0.0}
            
        pnls = [t['pnl'] for t in trades]
        total_pnl = sum(pnls)
        
        # Win Rate
        wins = [p for p in pnls if p > 0]
        win_rate = len(wins) / len(pnls) if pnls else 0.0
        
        # Cumulative Returns for Drawdown
        cum_pnl = []
        running_total = 0
        for p in pnls:
            running_total += p
            cum_pnl.append(running_total)
            
        # Max Drawdown
        max_drawdown = 0.0
        peak = -float('inf')
        for val in cum_pnl:
            if val > peak:
                peak = val
            drawdown = val - peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown
                
        # Sharpe Ratio
        mean_return = total_pnl / len(pnls)
        variance = sum([(p - mean_return) ** 2 for p in pnls]) / len(pnls)
        std_return = math.sqrt(variance)
        
        sharpe = (mean_return / std_return) if std_return != 0 else 0.0
        
        return {
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'total_pnl': total_pnl
        }

    def analyze_market_heat(self, candles):
        """
        Calculate Volatility and Momentum Heat.
        """
        if not candles: return 0.0
        
        # Volatility (ATR-like normalized)
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        closes = [c['close'] for c in candles]
        
        trs = [h - l for h, l in zip(highs, lows)]
        avg_tr = sum(trs) / len(trs) if trs else 0
        avg_close = sum(closes) / len(closes) if closes else 1
        
        volatility = avg_tr / avg_close
        
        # Momentum (ROC)
        close_start = closes[0]
        close_end = closes[-1]
        momentum = abs((close_end - close_start) / close_start) if close_start != 0 else 0
        
        # Heat Score (0 to 100)
        # Normalized heuristic
        heat_score = (volatility * 500) + (momentum * 500)
        return min(100.0, heat_score)
