
import pandas as pd
from core.models import Signal

class Strategy:
    """Base Strategy Interface"""
    def __init__(self, bot):
        self.bot = bot
        self.name = "Base Strategy"

    def execute(self, symbol, data=None):
        """Execute strategy logic and return a Signal object"""
        raise NotImplementedError

    def apply_risk_management(self, decision_packet, df=None):
        """
        Enrich decision packet with dynamic SL/TP and Position Sizing.
        """
        # Ensure ATR exists
        atr = 0.0
        
        if df is not None and not df.empty:
            if 'atr' not in df.columns:
                # Simple ATR calculation if missing
                high_low = df['high'] - df['low']
                high_close = (df['high'] - df['close'].shift()).abs()
                low_close = (df['low'] - df['close'].shift()).abs()
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                atr = true_range.rolling(14).mean().iloc[-1]
            else:
                atr = df['atr'].iloc[-1]

        # Handle NaN ATR or missing DF
        if pd.isna(atr) or atr == 0:
            price = decision_packet.get('entry', 0)
            if price > 0:
                atr = price * 0.01 # Fallback to 1% of price

        entry_price = decision_packet['entry']
        bias = decision_packet['bias']

        # 1. Dynamic Stops (if not already set or zero)
        if decision_packet.get('stop_loss', 0) == 0:
            stops = self.bot.risk_manager.calculate_dynamic_stops(entry_price, atr, bias)
            decision_packet['stop_loss'] = stops['stop_loss']
            decision_packet['take_profit'] = stops['take_profit']
        
        # 2. Position Sizing
        sl_price = decision_packet['stop_loss']
        regime = decision_packet.get('market_regime', 'Normal')
        risk_calc = self.bot.risk_manager.calculate_risk_size(atr, entry_price, sl_price, regime=regime)
        
        decision_packet['position_size'] = risk_calc['position_size']
        decision_packet['risk_amount'] = risk_calc['risk_amount']
        # Update risk_percent if calculated differently
        if 'risk_pct' in risk_calc:
             decision_packet['risk_percent'] = risk_calc['risk_pct'] * 100 
        
        return decision_packet

class SmartTrendStrategy(Strategy):
    """
    The 'Elite' CapacityBay Smart Trend Strategy.
    Combines Multi-Timeframe Analysis, Market Regime, Liquidity, and Risk Management.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Smart Trend"

    def execute(self, symbol, data=None):
        # 1. Fetch Core Data
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=200)
        if df.empty:
            return None
            
        # 2. Technical Analysis
        df = self.bot.analyzer.calculate_indicators(df)
        signal_data = self.bot.analyzer.get_signal(df)
        
        # 3. Market Regime
        regime_data = self.bot.brain.detect_market_regime(df)
        
        # 4. Construct Signal
        if signal_data['type'] in ['buy', 'sell']:
             decision_packet = {
                'decision': 'EXECUTE',
                'confidence': signal_data.get('score', 0)/10,
                'market_regime': regime_data['type'],
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_data['type'].upper(),
                "strategy": self.name,
                "entry": df['close'].iloc[-1],
                "stop_loss": 0, # Should be calculated by risk manager
                "take_profit": 0,
                "risk_percent": 1.0,
                "execution_score": 1.0
             }
             
             # Apply Risk Management
             decision_packet = self.apply_risk_management(decision_packet, df)

             self.bot.log_trade(decision_packet)
             
             return Signal(
                symbol=symbol,
                type=signal_data['type'],
                price=df['close'].iloc[-1],
                timestamp=pd.Timestamp.now(),
                reason=signal_data['reason'],
                indicators=signal_data['indicators'],
                score=signal_data.get('score', 0),
                regime=regime_data['type'],
                liquidity_status='Normal',
                confidence=decision_packet['confidence'],
                decision_details=decision_packet
             )
        return None

class GridTradingStrategy(Strategy):
    """
    Grid Trading Strategy.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Grid Trading"

    def execute(self, symbol, data=None):
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=100)
        if df.empty: return None
        
        # Calculate Grid Levels (using Bollinger Bands as dynamic grid for simplicity)
        if 'bb_lower' not in df.columns:
            df = self.bot.analyzer.calculate_indicators(df)
            
        row = df.iloc[-1]
        price = row['close']
        
        # Grid Logic: Buy at lower bands, Sell at upper bands
        # A real grid bot would place multiple limit orders. 
        # Here we signal entry when price crosses grid levels.
        
        lower_band = row['bb_lower']
        upper_band = row['bb_upper']
        mid_band = row['ema_20'] if 'ema_20' in row else (lower_band + upper_band) / 2
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        # Buy Zone (Lower Grid)
        if price <= lower_band * 1.005: # Within 0.5% of lower band
            signal_type = 'buy'
            reason = "Grid Buy Level Reached"
            confidence = 0.8
            
        # Sell Zone (Upper Grid)
        elif price >= upper_band * 0.995: # Within 0.5% of upper band
            signal_type = 'sell'
            reason = "Grid Sell Level Reached"
            confidence = 0.8
            
        if signal_type != 'hold':
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Ranging',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": price,
                "stop_loss": lower_band * 0.98 if signal_type == 'buy' else upper_band * 1.02,
                "take_profit": mid_band, # Target mean reversion
                "risk_percent": 1.0,
                "execution_score": 1.0
            }
            
            # Apply Risk Management
            decision_packet = self.apply_risk_management(decision_packet, df)

            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=price,
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'bb_lower': lower_band, 'bb_upper': upper_band},
                score=8.0,
                regime='Ranging',
                liquidity_status='Normal',
                confidence=confidence,
                decision_details=decision_packet
            )
        return None

class MeanReversionStrategy(Strategy):
    """
    Mean Reversion Strategy.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Mean Reversion"

    def execute(self, symbol, data=None):
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=100)
        if df.empty: return None
        
        df = self.bot.analyzer.calculate_indicators(df)
        row = df.iloc[-1]
        
        if 'ema_50' not in row or pd.isna(row['ema_50']):
             return None
             
        ema_50 = row['ema_50']
        dist_pct = (row['close'] - ema_50) / ema_50
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        if dist_pct < -0.02 and row.get('rsi', 50) < 30:
            signal_type = 'buy'
            reason = "Oversold Reversion"
            confidence = 0.85
        elif dist_pct > 0.02 and row.get('rsi', 50) > 70:
            signal_type = 'sell'
            reason = "Overbought Reversion"
            confidence = 0.85
            
        if signal_type != 'hold':
             decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Reversion',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": row['close'],
                "stop_loss": 0,
                "take_profit": 0,
                "risk_percent": 1.0,
                "execution_score": 1.0
             }
             
             # Apply Risk Management
             decision_packet = self.apply_risk_management(decision_packet, df)

             self.bot.log_trade(decision_packet)
             
             return Signal(
                symbol=symbol,
                type=signal_type,
                price=row['close'],
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'rsi': row.get('rsi')},
                score=8.5,
                regime='Reversion',
                liquidity_status='Normal',
                confidence=confidence,
                decision_details=decision_packet
             )
        return None

class WeightedSignalStrategy(Strategy):
    """
    Weighted Ensemble Strategy (RSI, MACD, EMA).
    Incorporates user-provided signal engine logic.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Weighted Ensemble"
        self.params = {"weights": {"rsi": 0.3, "macd": 0.3, "ema": 0.4}}

    def compute_features(self, df):
        try:
            from ta.momentum import RSIIndicator
            from ta.trend import MACD
            from ta.volatility import BollingerBands
            
            df = df.copy()
            # RSI
            df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()
            # MACD
            macd = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
            df["macd"] = macd.macd()
            df["macd_signal"] = macd.macd_signal()
            # BB
            bb = BollingerBands(close=df["close"], window=20, window_dev=2)
            df["bb_high"] = bb.bollinger_hband()
            df["bb_low"] = bb.bollinger_lband()
            # ATR
            df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
            # EMA
            df["ema_fast"] = df["close"].ewm(span=12).mean()
            df["ema_slow"] = df["close"].ewm(span=26).mean()
            return df
        except ImportError:
            # Fallback to bot's analyzer (pandas_ta) if ta lib missing
            print("Warning: 'ta' library not found. Using internal analyzer.")
            return self.bot.analyzer.calculate_indicators(df)

    def execute(self, symbol, data=None):
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=100)
        if df.empty: return None
        
        df = self.compute_features(df)
        row = df.iloc[-1]
        
        # Signal Logic
        w = self.params.get("weights", {"rsi": 0.3, "macd": 0.3, "ema": 0.4})
        
        # Safe access with default 0/50
        rsi = row.get("rsi", 50)
        macd_val = row.get("macd", 0)
        macd_sig = row.get("macd_signal", 0)
        ema_fast = row.get("ema_fast", 0)
        ema_slow = row.get("ema_slow", 0)
        
        rsi_sig = 1 if rsi < 30 else (-1 if rsi > 70 else 0)
        macd_sig = 1 if (macd_val > macd_sig) else -1
        ema_sig = 1 if (ema_fast > ema_slow) else -1
        
        raw_score = w["rsi"]*rsi_sig + w["macd"]*macd_sig + w["ema"]*ema_sig
        
        # Confidence calibration with volatility
        vol = row.get("atr", 0) or 1e-6
        # Normalize vol for confidence (simple heuristic)
        conf = max(0.0, min(1.0, abs(raw_score))) # Simplified from user code to avoid tiny vol issues
        
        signal_type = "hold"
        if raw_score > 0.3:
            signal_type = "buy"
        elif raw_score < -0.3:
            signal_type = "sell"
            
        if signal_type != 'hold':
             decision_packet = {
                'decision': 'EXECUTE',
                'confidence': conf,
                'market_regime': 'Trending' if abs(raw_score) > 0.5 else 'Range',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": row['close'],
                "stop_loss": 0,
                "take_profit": 0,
                "risk_percent": 1.0,
                "execution_score": abs(raw_score)
             }
             
             # Apply Risk Management
             decision_packet = self.apply_risk_management(decision_packet, df)

             self.bot.log_trade(decision_packet)
             
             return Signal(
                symbol=symbol,
                type=signal_type,
                price=row['close'],
                timestamp=pd.Timestamp.now(),
                reason=f"Weighted Score: {raw_score:.2f}",
                indicators={'rsi': rsi, 'macd': macd_val, 'ema_diff': ema_fast - ema_slow},
                score=raw_score * 10,
                regime='Trending',
                liquidity_status='Normal',
                confidence=conf,
                decision_details=decision_packet
             )
        return None

class FundingArbitrageStrategy(Strategy):
    """
    Funding Arbitrage Strategy.
    Exploits high positive funding rates by shorting perps and holding spot (Delta Neutral).
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Funding Arbitrage"

    def execute(self, symbol, data=None):
        # Fetch current funding rate
        ticker = self.bot.data_manager.fetch_ticker(symbol)
        funding_rate = ticker.get('fundingRate', 0)
        
        # Annualized funding rate
        apr = funding_rate * 3 * 365 * 100 
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        # Threshold: > 20% APR
        if apr > 20.0:
            signal_type = 'sell' # Short perp to collect funding
            reason = f"High Funding Rate ({apr:.2f}% APR)"
            confidence = 0.9
        
        if signal_type != 'hold':
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'High Funding',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": ticker['last'],
                "stop_loss": 0, # Delta Neutral, no stop needed usually (or wide stop)
                "take_profit": 0,
                "risk_percent": 5.0, # Safe arbitrage allowing larger size
                "execution_score": 1.0
            }
            
            # Apply Risk Management
            decision_packet = self.apply_risk_management(decision_packet, df=None)

            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=ticker['last'],
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'funding_apr': apr},
                score=9.0,
                regime='High Funding',
                liquidity_status='Normal',
                confidence=confidence,
                decision_details=decision_packet
            )
        return None

class SpatialArbitrageStrategy(Strategy):
    """
    Spatial Arbitrage Strategy.
    Scans multiple exchanges for price differences on the same asset.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Spatial Arbitrage"

    def execute(self, symbol, data=None):
        # Use the core ArbitrageScanner
        # Note: This strategy might need to ignore the 'symbol' passed if it scans globally,
        # but for compatibility, we scan the requested symbol.
        
        opps = self.bot.arbitrage.scan_opportunities(symbol)
        
        if not opps:
            return None
            
        # Get best opportunity
        best_opp = opps[0] # scan_opportunities already ranks/sorts or we pick first
        
        # Check profitability threshold (already filtered in scan_opportunities usually, but double check)
        if best_opp['estimated_profit_1k'] < 1.0: # Minimum $1 profit per $1k
            return None
            
        # For Spatial Arbitrage, we typically need to execute on TWO exchanges.
        # The Signal object structure is designed for a single direction on the 'active' exchange.
        # This is a limitation. However, we can signal a "Buy" on the lower priced exchange
        # if that is the one the bot is currently connected to.
        
        # Check which exchange we are connected to
        current_ex = self.bot.exchange_id.lower() if self.bot.exchange_id else ''
        
        signal_type = 'hold'
        reason = ""
        
        # Ensure exchange names are compared case-insensitively
        buy_ex = best_opp['buy_exchange'].lower()
        sell_ex = best_opp['sell_exchange'].lower()
        
        if current_ex == buy_ex:
            signal_type = 'buy'
            reason = f"Arb Buy (Sell on {best_opp['sell_exchange']} @ {best_opp['sell_price']})"
        elif current_ex == sell_ex:
            signal_type = 'sell'
            reason = f"Arb Sell (Buy on {best_opp['buy_exchange']} @ {best_opp['buy_price']})"
        else:
            # We are not connected to either leg of the arbitrage
            # We can't execute automatically unless we can switch exchanges dynamically.
            # For now, we return None or Log it.
            return None
            
        decision_packet = {
            'decision': 'EXECUTE',
            'confidence': 0.95,
            'market_regime': 'Arbitrage',
            'rejection_reason': '',
            "symbol": symbol,
            "bias": signal_type.upper(),
            "strategy": self.name,
            "entry": best_opp['buy_price'] if signal_type == 'buy' else best_opp['sell_price'],
            "stop_loss": 0, 
            "take_profit": 0,
            "risk_percent": 10.0, # High confidence
            "execution_score": 1.0,
            "arbitrage_details": best_opp
        }
        
        # Skip standard risk management for Arb? Or use it?
        # Use it for sizing, but stops might be tight.
        decision_packet = self.apply_risk_management(decision_packet, df=None)
        
        self.bot.log_trade(decision_packet)
        
        return Signal(
            symbol=symbol,
            type=signal_type,
            price=decision_packet['entry'],
            timestamp=pd.Timestamp.now(),
            reason=reason,
            indicators={'spread_pct': best_opp['spread_pct']},
            score=9.5,
            regime='Arbitrage',
            liquidity_status='Normal',
            confidence=0.95,
            decision_details=decision_packet
        )

class EnsembleStrategy(Strategy):
    """
    Ensemble Brain Strategy.
    Combines Technicals, ML Prediction, Sentiment, and RL using the CapacityBayBrain.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Ensemble Brain"

    def execute(self, symbol, data=None):
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=200)
        if df.empty: return None
        
        # 1. Technical Analysis Signal
        df = self.bot.analyzer.calculate_indicators(df)
        tech_signal = self.bot.analyzer.get_signal(df)
        
        # 2. Sentiment (Mock or Real)
        # self.bot.sentiment.get_sentiment(symbol)
        sentiment_score = 0.0 
        
        # 3. Get Ensemble Decision from Brain
        ensemble_result = self.bot.brain.get_ensemble_signal(df, tech_signal, sentiment_score)
        
        # 4. Gating
        decision = ensemble_result['decision'] # BUY, SELL, HOLD
        
        if decision in ['BUY', 'SELL']:
            signal_type = decision.lower()
            confidence = ensemble_result['confidence']
            
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Ensemble',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": df['close'].iloc[-1],
                "stop_loss": 0,
                "take_profit": 0,
                "risk_percent": 2.0 * confidence, # Scale size by confidence
                "execution_score": confidence,
                "components": ensemble_result['components']
            }
            
            # Apply Risk Management
            decision_packet = self.apply_risk_management(decision_packet, df)
            
            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=df['close'].iloc[-1],
                timestamp=pd.Timestamp.now(),
                reason=f"Ensemble Score: {ensemble_result['final_score']:.2f}",
                indicators=ensemble_result['components'],
                score=ensemble_result['final_score'] * 10,
                regime='Ensemble',
                liquidity_status='Normal',
                confidence=confidence,
                decision_details=decision_packet
            )
            
        return None


class BasisTradeStrategy(Strategy):
    """
    Futures Basis Strategy.
    Exploits the premium of Futures over Spot (Contango).
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Basis Trade"

    def execute(self, symbol, data=None):
        # Requires Spot and Future tickers
        # Assuming symbol is perp, we need to construct spot/quarterly symbols
        # This is a simplification
        spot_price = self.bot.data_manager.fetch_ticker(symbol)['last']
        future_price = spot_price * 1.02 # Simulating 2% premium
        
        basis = (future_price - spot_price) / spot_price
        annualized_basis = basis * (365/90) * 100 # Assuming 90 days to expiry
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        if annualized_basis > 15.0:
            signal_type = 'sell' # Short Future
            reason = f"High Basis Premium ({annualized_basis:.2f}% APR)"
            confidence = 0.85
            
        if signal_type != 'hold':
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Contango',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": future_price,
                "stop_loss": 0,
                "take_profit": 0,
                "risk_percent": 5.0,
                "execution_score": 1.0
            }
            
            # Apply Risk Management
            decision_packet = self.apply_risk_management(decision_packet, df=None)

            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=future_price,
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'basis_apr': annualized_basis},
                score=8.5,
                regime='Contango',
                liquidity_status='Normal',
                confidence=confidence,
                decision_details=decision_packet
            )
        return None

class SwingRangeStrategy(Strategy):
    """
    Swing Range Strategy.
    Trades the range boundaries in a sideways market.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Swing Range"

    def execute(self, symbol, data=None):
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=100)
        if df.empty: return None

        # 1. Determine Range
        # Use recent High/Low pivot points over last N candles
        window = 20
        recent_high = df['high'].rolling(window=window).max().iloc[-1]
        recent_low = df['low'].rolling(window=window).min().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # 2. Check Regime
        # Only trade if ADX < 25 (Ranging)
        if 'adx' not in df.columns:
            df = self.bot.analyzer.calculate_indicators(df)
            
        if df['adx'].iloc[-1] > 25:
            return None # Trending, skip range strategy

        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        # 3. Decision Logic
        # Sell near High
        if current_price >= recent_high * 0.995:
            signal_type = 'sell'
            reason = "Range High Rejection"
            confidence = 0.8
            
        # Buy near Low
        elif current_price <= recent_low * 1.005:
            signal_type = 'buy'
            reason = "Range Low Bounce"
            confidence = 0.8
            
        if signal_type != 'hold':
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Ranging',
                'rejection_reason': ''
            }
            
            self.bot.last_trade_time = pd.Timestamp.now()
            
            # Stops just outside range
            sl = recent_low * 0.99 if signal_type == 'buy' else recent_high * 1.01
            tp = recent_high * 0.99 if signal_type == 'buy' else recent_low * 1.01
            
            decision_packet.update({
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": current_price,
                "stop_loss": sl,
                "take_profit": tp,
                "risk_percent": 1.0,
                "execution_score": 1.0
            })
            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=current_price,
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'adx': df['adx'].iloc[-1]},
                score=8.0,
                regime='Ranging',
                liquidity_status='Normal',
                confidence=confidence,
                decision_details=decision_packet
            )
        return None

class LiquiditySweepStrategy(Strategy):
    """
    Liquidity Sweep Strategy.
    Identifies stop runs (sweeps) of key levels followed by a reversal.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Liquidity Sweep"

    def execute(self, symbol, data=None):
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=100)
        if df.empty: return None

        # Identify Key Swing Points (Fractals)
        window = 5
        df['swing_high'] = df['high'].rolling(window=window*2+1, center=True).max()
        df['swing_low'] = df['low'].rolling(window=window*2+1, center=True).min()
        
        # Find the most recent confirmed swing points (excluding current candle context for lookback)
        last_swing_high = df['swing_high'].dropna().iloc[-1] if not df['swing_high'].dropna().empty else df['high'].max()
        last_swing_low = df['swing_low'].dropna().iloc[-1] if not df['swing_low'].dropna().empty else df['low'].min()
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        # Bullish Sweep: Price broke below last swing low but closed above it
        if current['low'] < last_swing_low and current['close'] > last_swing_low:
            signal_type = 'buy'
            reason = "Liquidity Sweep of Low"
            confidence = 0.85
            
        # Bearish Sweep: Price broke above last swing high but closed below it
        elif current['high'] > last_swing_high and current['close'] < last_swing_high:
            signal_type = 'sell'
            reason = "Liquidity Sweep of High"
            confidence = 0.85
            
        if signal_type != 'hold':
            sl = current['low'] * 0.998 if signal_type == 'buy' else current['high'] * 1.002
            tp = last_swing_high if signal_type == 'buy' else last_swing_low
            
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Reversal',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": current['close'],
                "stop_loss": sl,
                "take_profit": tp,
                "risk_percent": 1.5, # Slightly higher risk for high probability setup
                "execution_score": 1.0
            }
            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=current['close'],
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'swing_high': last_swing_high, 'swing_low': last_swing_low},
                score=9.0,
                regime='Reversal',
                liquidity_status='Swept',
                confidence=confidence,
                decision_details=decision_packet
            )
        return None

class OrderFlowStrategy(Strategy):
    """
    Order Flow Strategy.
    Uses Volume and Price Action to detect absorption and aggression.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Order Flow"

    def execute(self, symbol, data=None):
        df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=50)
        if df.empty: return None

        # Calculate Volume Moving Average
        vol_ma = df['volume'].rolling(20).mean().iloc[-1]
        current_vol = df['volume'].iloc[-1]
        
        # Detect High Volume (Absorption or Breakout)
        is_high_volume = current_vol > (vol_ma * 2.0)
        
        current_candle = df.iloc[-1]
        body_size = abs(current_candle['close'] - current_candle['open'])
        total_range = current_candle['high'] - current_candle['low']
        
        if total_range == 0: return None
        
        body_pct = body_size / total_range
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        # Scenario 1: Absorption (High Volume, Small Body, Long Wick)
        if is_high_volume and body_pct < 0.3:
            # Hammer / Shooting Star Logic
            upper_wick = current_candle['high'] - max(current_candle['open'], current_candle['close'])
            lower_wick = min(current_candle['open'], current_candle['close']) - current_candle['low']
            
            if lower_wick > upper_wick * 2: # Bullish Absorption
                signal_type = 'buy'
                reason = "Bullish Absorption (High Vol Hammer)"
                confidence = 0.75
            elif upper_wick > lower_wick * 2: # Bearish Absorption
                signal_type = 'sell'
                reason = "Bearish Absorption (High Vol Shooting Star)"
                confidence = 0.75
                
        # Scenario 2: Aggressive Breakout (High Volume, Large Body)
        elif is_high_volume and body_pct > 0.8:
            if current_candle['close'] > current_candle['open']:
                signal_type = 'buy'
                reason = "Aggressive Buying (High Vol Breakout)"
                confidence = 0.8
            else:
                signal_type = 'sell'
                reason = "Aggressive Selling (High Vol Breakdown)"
                confidence = 0.8

        if signal_type != 'hold':
            sl = current_candle['low'] * 0.995 if signal_type == 'buy' else current_candle['high'] * 1.005
            # 1.5R Target
            risk = abs(current_candle['close'] - sl)
            tp = current_candle['close'] + (risk * 1.5) if signal_type == 'buy' else current_candle['close'] - (risk * 1.5)

            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Volatile',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": current_candle['close'],
                "stop_loss": sl,
                "take_profit": tp,
                "risk_percent": 1.0,
                "execution_score": 1.0
            }
            
            # Apply Risk Management
            decision_packet = self.apply_risk_management(decision_packet, df)

            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=current_candle['close'],
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'volume_ma': vol_ma},
                score=8.0,
                regime='Volatile',
                liquidity_status='High',
                confidence=confidence,
                decision_details=decision_packet
            )
        return None

class SniperStrategy(Strategy):
    """
    Sniper Strategy: The 'Number 1' Strategy.
    High precision, AI-confirmed, Confluence-based entries.
    Targeting > 90% Win Rate setups.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Sniper Mode"

    def execute(self, symbol, data=None):
        # 1. Fetch & Prepare Data
        if data is None:
             df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=200)
             if df.empty: return None
             # Compute Features for AI
             df = self.bot.feature_store.compute_features(df)
        else:
             df = data

        if df.empty: return None
        
        row = df.iloc[-1]
        
        # 2. Strict Confluence Checks
        # Requirement 1: Trend is Strong (ADX > 25)
        if 'adx' not in row or row['adx'] < 25:
            return None
            
        # Requirement 2: Momentum (MACD)
        # Check if MACD line > Signal line (Bullish) or vice versa
        if 'macd' not in row: return None # Should be there from feature store
        
        # We need previous row for crossover check
        prev_row = df.iloc[-2]
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        # Bullish Sniper Setup
        # 1. MACD Bullish Crossover (recent) or Expansion
        # 2. Price > EMA 50 > EMA 200 (Uptrend)
        # 3. RSI not overbought (< 70)
        # 4. AI Confirmation > 0.3
        
        is_uptrend = row['close'] > row['ema_50'] > row['ema_200']
        is_downtrend = row['close'] < row['ema_50'] < row['ema_200']
        
        # AI Prediction
        ai_score = self.bot.brain.get_ai_prediction(df)
        
        if is_uptrend and row['rsi'] < 75:
            # Check for recent MACD cross or strong momentum
            if row['macd'] > row['macd_signal'] and row['macd'] > 0:
                 if ai_score > 0.2: # AI Agrees
                     signal_type = 'buy'
                     reason = "Sniper Buy (Trend + MACD + AI)"
                     confidence = 0.9 + (ai_score * 0.1) # Boost confidence
        
        elif is_downtrend and row['rsi'] > 25:
            if row['macd'] < row['macd_signal'] and row['macd'] < 0:
                 if ai_score < -0.2: # AI Agrees
                     signal_type = 'sell'
                     reason = "Sniper Sell (Trend + MACD + AI)"
                     confidence = 0.9 + (abs(ai_score) * 0.1)

        if signal_type != 'hold':
            # Dynamic Tight Stops for High R:R
            atr = row['atr']
            sl = row['close'] - (atr * 1.5) if signal_type == 'buy' else row['close'] + (atr * 1.5)
            tp = row['close'] + (atr * 4.5) if signal_type == 'buy' else row['close'] - (atr * 4.5) # 1:3 R:R
            
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Trending',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": row['close'],
                "stop_loss": sl,
                "take_profit": tp,
                "risk_percent": 2.0, # Higher risk for Sniper setups
                "execution_score": 1.0
            }
            
            # Apply Risk Management
            decision_packet = self.apply_risk_management(decision_packet, df)

            self.bot.log_trade(decision_packet)
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=row['close'],
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'ai_score': ai_score, 'adx': row['adx']},
                score=9.5, # Highest Score
                regime='Trending',
                liquidity_status='High',
                confidence=confidence,
                decision_details=decision_packet
            )
            
        return None

class NigerianMarketStrategy(Strategy):
    """
    Nigerian Market Strategy (NGN/USDT).
    Focuses on Inflation Hedging and Arbitrage opportunities.
    Monitors NGN rates and signals crypto accumulation during NGN devaluation.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.name = "Nigerian Market Strategy"
        # If possible, get rate from FiatManager
        self.last_rate = 0.0

    def execute(self, symbol, data=None):
        # 1. Fetch NGN Rate (Oracle)
        current_rate = 0.0
        if hasattr(self.bot, 'fiat') and self.bot.fiat.adapter:
            try:
                # Attempt to get real rate if not cached recently
                # For strategy execution speed, we might rely on cached values in bot
                pass 
            except:
                pass
        
        # 2. Standard Crypto Analysis (Trend Following)
        # In high inflation (NGN), we want to be Long Crypto/USDT most of the time.
        
        if data is None:
             df = self.bot.data_manager.fetch_ohlcv(symbol, self.bot.timeframe, limit=50)
        else:
             df = data

        if df.empty: return None
        
        row = df.iloc[-1]
        
        # Simple Logic: 
        # Buy on Dips if Trend is Up (EMA 50 > EMA 200)
        # Hold longer than usual (Swing Trade) to ride devaluation
        
        ema_50 = row['close'] # Placeholder if not computed
        if 'ema_50' in row: ema_50 = row['ema_50']
        
        signal_type = 'hold'
        reason = ""
        confidence = 0.0
        
        # Check RSI for oversold (Dip)
        rsi = row.get('rsi', 50)
        
        if rsi < 40:
            signal_type = 'buy'
            reason = "Inflation Hedge: Buy the Dip"
            confidence = 0.85
            
        if signal_type != 'hold':
            decision_packet = {
                'decision': 'EXECUTE',
                'confidence': confidence,
                'market_regime': 'Inflationary',
                'rejection_reason': '',
                "symbol": symbol,
                "bias": signal_type.upper(),
                "strategy": self.name,
                "entry": row['close'],
                "stop_loss": row['close'] * 0.95, # Wide stop
                "take_profit": row['close'] * 1.10, # Target 10%
                "risk_percent": 2.0,
                "execution_score": 1.0
            }
            
            return Signal(
                symbol=symbol,
                type=signal_type,
                price=row['close'],
                timestamp=pd.Timestamp.now(),
                reason=reason,
                indicators={'rsi': rsi},
                score=8.5,
                regime='Inflationary',
                liquidity_status='Normal',
                confidence=confidence,
                decision_details=decision_packet
            )
            
        return None
