import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from core.models import Signal

class BacktestBot:
    """
    A mock Bot class for backtesting.
    It mimics the interface of TradingBot but serves historical data.
    """
    def __init__(self, full_df, analyzer, brain, risk_manager):
        self.full_df = full_df
        self.current_index = 0
        self.analyzer = analyzer
        self.brain = brain
        self.risk_manager = risk_manager
        self.symbol = "BACKTEST/USD"
        self.timeframe = "1h"
        self.last_trade_time = None
        self.data_manager = self # Mock data manager
        
        # Pre-calculate indicators for performance
        # In a real rigorous backtest, we should calculate step-by-step to avoid lookahead bias,
        # but for speed, we often pre-calculate. 
        # However, SmartTrendStrategy calls calculate_indicators internally.
        # We need to be careful.
        
    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        # Return data up to current_index
        # We ensure we return at least 'limit' rows if possible
        end = self.current_index + 1
        start = max(0, end - limit)
        return self.full_df.iloc[start:end].copy()

    def fetch_order_book(self, symbol, limit=20):
        # Mock order book
        return {'bids': [], 'asks': []}

    def fetch_ticker(self, symbol):
        # Mock ticker
        current_price = self.full_df.iloc[self.current_index]['close']
        return {'last': current_price}

class BacktestEngine:
    def __init__(self, bot):
        # We use the real bot's components (analyzer, brain, risk)
        # but we will swap the bot instance passed to strategy with a BacktestBot
        self.real_bot = bot

    def run(self, strategy_name, symbol, timeframe, days=30):
        """
        Run a backtest for the given strategy.
        """
        # 1. Fetch Historical Data
        print(f"Fetching {days} days of history for {symbol}...")
        # We need a lot of data. 
        # If timeframe is 1h, 30 days = 720 candles.
        # If 15m, 30 days = 2880 candles.
        limit = 1000 # Cap for now
        if timeframe == '1d': limit = 365
        elif timeframe == '4h': limit = 1000
        elif timeframe == '1h': limit = 1000
        else: limit = 2000
        
        full_df = self.real_bot.data_manager.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if full_df.empty:
            return {"error": "No data available"}
            
        # 2. Setup Backtest Environment
        backtest_bot = BacktestBot(full_df, self.real_bot.analyzer, self.real_bot.brain, self.real_bot.risk_manager)
        backtest_bot.symbol = symbol
        backtest_bot.timeframe = timeframe
        
        # Instantiate the strategy with the BacktestBot
        # We need to dynamically import or use the class from the real bot's registry if possible
        # But we only have the name.
        # Let's assume we can map names to classes or just re-instantiate if we know the class.
        # For now, we will use the logic from the real bot's strategies dict if we can access the class.
        
        # A better way: The real bot strategies are instances. We need the class.
        # We can look up the class type of the active strategy.
        strategy_instance = self.real_bot.strategies.get(strategy_name)
        if not strategy_instance:
            return {"error": f"Strategy {strategy_name} not found"}
            
        strategy_class = type(strategy_instance)
        strategy = strategy_class(backtest_bot)
        
        # 3. Simulation Loop
        trades = []
        equity = 10000 # Initial Capital
        equity_curve = []
        position = None # {type: 'buy'/'sell', entry: price, size: amount, sl: price, tp: price}
        
        # Start from index 200 (to have enough history for indicators)
        start_index = 200
        if len(full_df) < start_index + 10:
            return {"error": "Not enough data for backtest"}
            
        print(f"Starting simulation on {len(full_df)} candles...")
        
        for i in range(start_index, len(full_df)):
            backtest_bot.current_index = i
            current_candle = full_df.iloc[i]
            current_price = current_candle['close']
            current_time = current_candle['timestamp']
            
            # Check Exit Conditions if in Position
            if position:
                pnl = 0
                exit_reason = ""
                
                if position['type'] == 'buy':
                    if current_candle['low'] <= position['sl']:
                        pnl = (position['sl'] - position['entry']) * position['size']
                        exit_reason = "Stop Loss"
                        exit_price = position['sl']
                    elif current_candle['high'] >= position['tp']:
                        pnl = (position['tp'] - position['entry']) * position['size']
                        exit_reason = "Take Profit"
                        exit_price = position['tp']
                        
                elif position['type'] == 'sell':
                    if current_candle['high'] >= position['sl']:
                        pnl = (position['entry'] - position['sl']) * position['size']
                        exit_reason = "Stop Loss"
                        exit_price = position['sl']
                    elif current_candle['low'] <= position['tp']:
                        pnl = (position['entry'] - position['tp']) * position['size']
                        exit_reason = "Take Profit"
                        exit_price = position['tp']
                
                if exit_reason:
                    equity += pnl
                    trades.append({
                        'entry_time': position['time'],
                        'exit_time': current_time,
                        'type': position['type'],
                        'entry': position['entry'],
                        'exit': exit_price,
                        'pnl': pnl,
                        'reason': exit_reason
                    })
                    position = None
            
            # Execute Strategy (only if no position - simplified)
            # In a real engine, we might manage multiple positions or allow reversals.
            if position is None:
                try:
                    signal = strategy.execute(symbol)
                    
                    if signal and signal.type in ['buy', 'sell']:
                        # Simulate Entry
                        # We use 1% risk logic or fixed size? 
                        # Let's use fixed 10% of equity for simplicity in this version
                        size = (equity * 0.1) / current_price
                        
                        # We need SL/TP. The strategy usually returns a signal, but SmartTrend calculates SL/TP internally 
                        # and logs it? Wait, Strategy.execute returns a Signal object.
                        # The Signal object has 'price', 'type'.
                        # SmartTrendStrategy.execute also returns a Signal, but the logic inside calculates SL/TP 
                        # and stores it in the 'decision_packet' which is logged but not fully returned in Signal?
                        # Let's check Signal model.
                        
                        # Signal(symbol, type, price, timestamp, reason)
                        # It doesn't have sl/tp fields by default.
                        
                        # However, in SmartTrendStrategy:
                        # decision_packet has sl/tp.
                        # But it returns `Signal(...)`.
                        
                        # We need to extract SL/TP. 
                        # For backtesting purposes, we can recalculate SL/TP using RiskManager or assume default ATR based.
                        
                        atr = backtest_bot.risk_manager.calculate_atr(full_df.iloc[:i+1]) # Re-calc ATR
                        current_atr = atr.iloc[-1]
                        
                        if signal.type == 'buy':
                            sl = current_price - (current_atr * 2)
                            tp = current_price + (current_atr * 3)
                        else:
                            sl = current_price + (current_atr * 2)
                            tp = current_price - (current_atr * 3)
                            
                        position = {
                            'type': signal.type,
                            'entry': current_price,
                            'time': current_time,
                            'size': size,
                            'sl': sl,
                            'tp': tp
                        }
                except Exception as e:
                    # Strategy might fail on partial data or mock errors
                    pass
            
            equity_curve.append({'time': current_time, 'equity': equity})

        # 4. Compile Results
        df_trades = pd.DataFrame(trades)
        total_trades = len(trades)
        win_trades = len(df_trades[df_trades['pnl'] > 0]) if total_trades > 0 else 0
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = equity - 10000
        
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "final_equity": equity,
            "trades": trades,
            "equity_curve": equity_curve
        }
