
import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    try:
        import pandas_ta_classic as ta
    except ImportError:
        print("Warning: pandas_ta not found. Technical Analysis modules may fail.")
        ta = None
from config.settings import RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD

class TechnicalAnalysis:
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate a comprehensive suite of technical indicators"""
        if df.empty:
            return df

        # Ensure DatetimeIndex for time-based indicators like VWAP
        if not isinstance(df.index, pd.DatetimeIndex):
            # Try to find a timestamp column
            if 'timestamp' in df.columns:
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                except:
                    pass
            elif 'date' in df.columns:
                try:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                except:
                    pass
        
        # Ensure index is sorted
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()

        # Trend Indicators
        if ta is None:
            print("Warning: pandas_ta not initialized. Skipping indicator calculation.")
            return df

        # MACD
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        
        # EMAs
        ema_50 = df.ta.ema(length=50)
        if isinstance(ema_50, pd.Series):
            df['ema_50'] = ema_50
            
        ema_200 = df.ta.ema(length=200)
        if isinstance(ema_200, pd.Series):
            df['ema_200'] = ema_200
            
        # SMAs (Simple Moving Averages)
        sma_20 = df.ta.sma(length=20)
        if isinstance(sma_20, pd.Series):
            df['sma_20'] = sma_20
            
        sma_50 = df.ta.sma(length=50)
        if isinstance(sma_50, pd.Series):
            df['sma_50'] = sma_50
            
        sma_200 = df.ta.sma(length=200)
        if isinstance(sma_200, pd.Series):
            df['sma_200'] = sma_200
        
        # ADX (Average Directional Index) - Trend Strength
        adx = df.ta.adx(length=14)
        if adx is not None:
            df = pd.concat([df, adx], axis=1)
            # Normalize column name for easier access
            if 'ADX_14' in df.columns:
                df['adx'] = df['ADX_14']

        # Ichimoku Cloud
        ichimoku = df.ta.ichimoku()
        if ichimoku is not None:
            # pandas_ta returns a tuple (dfs), we usually want the first one
            df = pd.concat([df, ichimoku[0]], axis=1)

        # Momentum Indicators
        # RSI
        rsi = df.ta.rsi(length=RSI_PERIOD)
        if isinstance(rsi, pd.DataFrame):
            df['rsi'] = rsi.iloc[:, 0]
        else:
            df['rsi'] = rsi
        
        # Stochastic RSI
        stoch_rsi = df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3)
        if stoch_rsi is not None:
            df = pd.concat([df, stoch_rsi], axis=1)

        # Volume Indicators
        # OBV (On Balance Volume)
        obv = df.ta.obv()
        if isinstance(obv, pd.DataFrame):
            df['obv'] = obv.iloc[:, 0]
        else:
            df['obv'] = obv

        # Volatility Indicators
        # Bollinger Bands
        bb = df.ta.bbands(length=20, std=2)
        if bb is not None:
            df = pd.concat([df, bb], axis=1)
            # Calculate Bandwidth for Squeeze detection
            # Columns are typically BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0 (Bandwidth), BBP_20_2.0 (Percent)
            # We need to find the specific column names dynamically or assume standard pandas_ta naming
            cols = df.columns
            try:
                bbb_cols = [c for c in cols if c.startswith('BBB')]
                if bbb_cols:
                    df['bb_width'] = df[bbb_cols[0]]
                else:
                    # Fallback calculation if BBB not returned
                    bbu_cols = [c for c in cols if c.startswith('BBU')]
                    bbl_cols = [c for c in cols if c.startswith('BBL')]
                    bbm_cols = [c for c in cols if c.startswith('BBM')]
                    
                    if bbu_cols and bbl_cols and bbm_cols:
                        bbu = bbu_cols[0]
                        bbl = bbl_cols[0]
                        bbm = bbm_cols[0]
                        df['bb_width'] = (df[bbu] - df[bbl]) / df[bbm] * 100
            except Exception:
                pass

        # ATR (Average True Range)
        atr = df.ta.atr(length=14)
        if isinstance(atr, pd.DataFrame):
            df['atr'] = atr.iloc[:, 0]
        else:
            df['atr'] = atr

        # SuperTrend (Trend Signal)
        try:
            st = df.ta.supertrend(length=10, multiplier=3)
            if st is not None:
                df = pd.concat([df, st], axis=1)
                # Normalize columns
                # SUPERT_10_3.0 (Trend Line), SUPERTd_10_3.0 (Direction: 1/-1)
                cols = df.columns
                st_lines = [c for c in cols if c.startswith('SUPERT_')]
                st_dirs = [c for c in cols if c.startswith('SUPERTd_')]
                
                if st_lines:
                    df['supertrend'] = df[st_lines[0]]
                if st_dirs:
                    df['supertrend_dir'] = df[st_dirs[0]]
        except Exception:
            pass

        # Candlestick Pattern Recognition
        # We'll use a few reliable patterns
        try:
            # CDL_PATTERN returns 0 if no pattern, 100 if bullish, -100 if bearish
            # Engulfing
            engulfing = df.ta.cdl_pattern(name="engulfing")
            if engulfing is not None:
                df = pd.concat([df, engulfing], axis=1)
                
            # Hammer (Bullish Reversal)
            hammer = df.ta.cdl_pattern(name="hammer")
            if hammer is not None:
                df = pd.concat([df, hammer], axis=1)
                
            # Shooting Star (Bearish Reversal)
            star = df.ta.cdl_pattern(name="shootingstar")
            if star is not None:
                df = pd.concat([df, star], axis=1)
                
            # Doji (Indecision)
            doji = df.ta.cdl_pattern(name="doji")
            if doji is not None:
                df = pd.concat([df, doji], axis=1)
        except Exception as e:
            pass

        # Advanced Indicators (World Standard)
        try:
            # VWAP
            if 'volume' in df.columns:
                vwap = df.ta.vwap()
                if vwap is not None:
                    df = pd.concat([df, vwap], axis=1)
                    if 'VWAP_D' in df.columns: df['vwap'] = df['VWAP_D']
            
            # CCI
            df['cci'] = df.ta.cci(length=20)
        
            # CMF (Chaikin Money Flow)
            cmf = df.ta.cmf()
            if cmf is not None:
                if isinstance(cmf, pd.DataFrame):
                     df = pd.concat([df, cmf], axis=1)
                else:
                     # If Series, assign directly
                     df['cmf'] = cmf
                     
                # Rename if necessary, pandas_ta usually returns 'CMF_20'
                cols = df.columns
                cmf_col = [c for c in cols if c.startswith('CMF')]
                if cmf_col:
                    df['cmf'] = df[cmf_col[0]]

            # MFI
            if 'volume' in df.columns:
                mfi = df.ta.mfi(length=14)
                if isinstance(mfi, pd.DataFrame):
                    df['mfi'] = mfi.iloc[:, 0]
                else:
                    df['mfi'] = mfi
                
            # PSAR
            psar = df.ta.psar()
            if psar is not None:
                df = pd.concat([df, psar], axis=1)
                
            # Keltner Channels
            kc = df.ta.kc()
            if kc is not None:
                df = pd.concat([df, kc], axis=1)
                
            # Donchian Channels
            donchian = df.ta.donchian()
            if donchian is not None:
                df = pd.concat([df, donchian], axis=1)

        except Exception as e:
            pass

        # Deduplicate columns to prevent "DuplicateError"
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    @staticmethod
    def get_signal(df: pd.DataFrame, htf_trend: str = "neutral") -> dict:
        """
        Generate a signal based on multiple factors (Confluence Strategy).
        Now includes Multi-Timeframe (HTF) context and Candlestick Patterns.
        Returns a dictionary with signal details.
        """
        if df.empty or len(df) < 50:
            return {'type': 'hold', 'score': 0, 'reason': 'Insufficient Data'}
        
        row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Scoring System (-10 to +10) for Pro Accuracy
        score = 0
        reasons = []
        
        # 0. Multi-Timeframe (HTF) Filter
        # If HTF trend aligns with signal, boost score significantly
        # If HTF trend opposes, penalize score
        # HTF Trend is passed in as 'bullish', 'bearish', or 'neutral'
        
        # 1. Trend Analysis (EMA)
        # Check if columns exist
        if 'ema_50' in df.columns and 'ema_200' in df.columns:
            if row['close'] > row['ema_50'] > row['ema_200']:
                score += 2
                reasons.append("Bullish Trend (Price > EMA50 > EMA200)")
                if htf_trend == "bullish":
                    score += 2
                    reasons.append("HTF Confirmation (Bullish)")
                elif htf_trend == "bearish":
                    score -= 2 # Penalize fighting the higher trend
                    reasons.append("HTF Conflict (Bearish)")
                    
            elif row['close'] < row['ema_50'] < row['ema_200']:
                score -= 2
                reasons.append("Bearish Trend (Price < EMA50 < EMA200)")
                if htf_trend == "bearish":
                    score -= 2
                    reasons.append("HTF Confirmation (Bearish)")
                elif htf_trend == "bullish":
                    score += 2 # Penalize fighting the higher trend
                    reasons.append("HTF Conflict (Bullish)")
        
        # 2. ADX Filter (Trend Strength)
        # ADX usually returns ADX_14, DMP_14, DMN_14
        try:
            adx_val = row['ADX_14']
            if adx_val > 25:
                # Strong trend, amplify trend signal
                if score > 0: score += 1
                elif score < 0: score -= 1
                reasons.append(f"Strong Trend (ADX: {adx_val:.1f})")
        except KeyError: pass

        # 3. RSI Condition & Divergence
        rsi_val = row['rsi']
        if rsi_val < RSI_OVERSOLD:
            score += 2
            reasons.append(f"RSI Oversold ({rsi_val:.1f})")
        elif rsi_val > RSI_OVERBOUGHT:
            score -= 2
            reasons.append(f"RSI Overbought ({rsi_val:.1f})")
        
        # Simple Divergence Check (5-period lookback)
        try:
            price_5 = df.iloc[-6]['close']
            rsi_5 = df.iloc[-6]['rsi']
            
            # Bullish Divergence: Price Lower, RSI Higher
            if row['close'] < price_5 and row['rsi'] > rsi_5:
                score += 2
                reasons.append("Bullish Divergence (Price L, RSI H)")
            
            # Bearish Divergence: Price Higher, RSI Lower
            elif row['close'] > price_5 and row['rsi'] < rsi_5:
                score -= 2
                reasons.append("Bearish Divergence (Price H, RSI L)")
        except: pass
            
        # 4. Bollinger Bands Reversion & Squeeze
        try:
            # Dynamic Column Access
            cols = df.columns
            bbl = [c for c in cols if c.startswith('BBL')][0]
            bbu = [c for c in cols if c.startswith('BBU')][0]
            
            if row['close'] < row[bbl]:
                score += 1
                reasons.append("Price below Lower BB")
            elif row['close'] > row[bbu]:
                score -= 1
                reasons.append("Price above Upper BB")
                
            # Check for Squeeze (Low Volatility)
            if 'bb_width' in df.columns:
                # Check if current width is in the lowest 10% of the last 50 periods
                recent_widths = df['bb_width'].tail(50)
                if row['bb_width'] < recent_widths.quantile(0.10):
                    reasons.append("Volatility Squeeze Detected")
                    # Squeeze itself isn't directional, but indicates potential explosive move
        except: pass

        # 5. MACD Crossover
        try:
            macd_line = row['MACD_12_26_9']
            signal_line = row['MACDs_12_26_9']
            prev_macd = prev_row['MACD_12_26_9']
            prev_signal = prev_row['MACDs_12_26_9']
            
            if prev_macd < prev_signal and macd_line > signal_line:
                score += 2
                reasons.append("MACD Bullish Crossover")
            elif prev_macd > prev_signal and macd_line < signal_line:
                score -= 2
                reasons.append("MACD Bearish Crossover")
        except KeyError: pass

        # 6. OBV Confirmation (Simple Slope)
        try:
            if row['obv'] > prev_row['obv'] and score > 0:
                score += 1 # Volume confirms bullish
            elif row['obv'] < prev_row['obv'] and score < 0:
                score -= 1 # Volume confirms bearish
        except: pass

        # --- New Indicator Logic ---

        # 8. VWAP Trend (Intraday)
        if 'vwap' in df.columns:
            if row['close'] > row['vwap']:
                score += 1
                reasons.append("Price > VWAP (Bullish Intraday)")
            elif row['close'] < row['vwap']:
                score -= 1
                reasons.append("Price < VWAP (Bearish Intraday)")

        # 9. CCI (Momentum)
        # CCI > 100 (Strong Bullish), CCI < -100 (Strong Bearish)
        if 'cci' in df.columns:
            if row['cci'] > 100:
                score += 1
                reasons.append("CCI > 100 (Strong Momentum)")
            elif row['cci'] < -100:
                score -= 1
                reasons.append("CCI < -100 (Strong Downside Momentum)")

        # 10. MFI (Money Flow) - Like RSI but with volume
        if 'mfi' in df.columns:
            if row['mfi'] < 20:
                score += 1
                reasons.append("MFI Oversold")
            elif row['mfi'] > 80:
                score -= 1
                reasons.append("MFI Overbought")

        # 11. PSAR (Parabolic SAR) - Trend Reversal
        # Columns typically PSARl_0.02_0.2 (Long) and PSARs_0.02_0.2 (Short)
        # If PSARl is non-NaN, we are in uptrend. If PSARs is non-NaN, downtrend.
        try:
            psar_l = [c for c in df.columns if c.startswith('PSARl')]
            psar_s = [c for c in df.columns if c.startswith('PSARs')]
            
            if psar_l and not pd.isna(row[psar_l[0]]):
                score += 1
                reasons.append("PSAR Bullish")
            elif psar_s and not pd.isna(row[psar_s[0]]):
                score -= 1
                reasons.append("PSAR Bearish")
        except: pass

        # 12. Keltner Channels (Volatility)
        try:
            # Assumes indicators calculated in calculate_indicators
            kcp_cols = [c for c in df.columns if c.startswith('KCP')]
            if kcp_cols:
                if row[kcp_cols[0]] > 1.0:
                    reasons.append("Price > Upper Keltner Channel")
                elif row[kcp_cols[0]] < 0.0:
                    reasons.append("Price < Lower Keltner Channel")
        except: pass

        # 13. Donchian Channels (Breakout)
        try:
             dcu_cols = [c for c in df.columns if c.startswith('DCU')] # Upper
             dcl_cols = [c for c in df.columns if c.startswith('DCL')] # Lower
             
             if dcu_cols and row['close'] > row[dcu_cols[0]]:
                  score += 1
                  reasons.append("Donchian Upper Breakout")
             elif dcl_cols and row['close'] < row[dcl_cols[0]]:
                  score -= 1
                  reasons.append("Donchian Lower Breakout")
        except: pass

        # 14. SuperTrend (Trend Direction)
        if 'supertrend_dir' in df.columns:
            st_dir = row['supertrend_dir']
            if st_dir == 1:
                score += 2
                reasons.append("SuperTrend Bullish")
            elif st_dir == -1:
                score -= 2
                reasons.append("SuperTrend Bearish")

        # 7. Candlestick Patterns (AI-like recognition)
        try:
            # CDL_ENGULFING: 100/-100
            # CDL_HAMMER: 100
            # CDL_SHOOTINGSTAR: -100
            # Need to match exact column names from pandas_ta
            # Usually 'CDL_ENGULFING', 'CDL_HAMMER', etc.
            cols = df.columns
            
            # Engulfing
            engulfing_col = [c for c in cols if 'ENGULFING' in c]
            if engulfing_col:
                val = row[engulfing_col[0]]
                if val == 100:
                    score += 1
                    reasons.append("Bullish Engulfing Pattern")
                elif val == -100:
                    score -= 1
                    reasons.append("Bearish Engulfing Pattern")
            
            # Hammer (Bullish only usually)
            hammer_col = [c for c in cols if 'HAMMER' in c]
            if hammer_col and row[hammer_col[0]] == 100:
                 # Hammer at bottom of downtrend is significant
                 if score < 0: # Potential reversal
                     score += 1
                     reasons.append("Hammer (Potential Reversal)")
            
            # Shooting Star (Bearish only usually)
            star_col = [c for c in cols if 'SHOOTINGSTAR' in c]
            if star_col and row[star_col[0]] == -100:
                if score > 0: # Potential reversal
                    score -= 1
                    reasons.append("Shooting Star (Potential Reversal)")
                    
        except Exception as e:
            pass
        
        # Deduplicate columns to prevent "DuplicateError"
        df = df.loc[:, ~df.columns.duplicated()]

        # Determine Signal
        signal_type = 'hold'
        # Stricter thresholds for "High Accuracy"
        if score >= 6:
            signal_type = 'strong_buy'
        elif score >= 4:
            signal_type = 'buy'
        elif score <= -6:
            signal_type = 'strong_sell'
        elif score <= -4:
            signal_type = 'sell'
            
        return {
            'type': signal_type,
            'score': score,
            'reason': ", ".join(reasons) if reasons else "No strong signals",
            'indicators': {
                'rsi': row['rsi'],
                'atr': row.get('atr', 0),
                'close': row['close'],
                'adx': row.get('ADX_14', 0)
            }
        }
