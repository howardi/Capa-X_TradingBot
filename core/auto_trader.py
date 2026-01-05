
import time
import pandas as pd
import logging
import threading
import os
import json
try:
    import yaml
except ImportError:
    yaml = None

from core.strategies import WeightedSignalStrategy, SmartTrendStrategy
from config.settings import DEFAULT_SYMBOL

# Setup Logging
logging.basicConfig(level=logging.INFO)

class Config:
    def __init__(self, path="config.yaml"):
        self.cfg = {}
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    if yaml:
                        self.cfg = yaml.safe_load(f)
                    else:
                        logging.warning("PyYAML not found. Attempting to parse config as JSON or ignoring.")
                        # Try json fallback if user accidentally used json syntax in yaml file or if it's actually json
                        try:
                            self.cfg = json.load(f)
                        except:
                            logging.error("Failed to load config: PyYAML missing and not valid JSON.")
            except Exception as e:
                logging.error(f"Error loading config: {e}")
        else:
            logging.warning(f"Config file {path} not found. Using defaults.")

    def get(self, k, default=None):
        return self.cfg.get(k, default)

class AutoTrader:
    """
    CapacityBay Logic Implementation.
    Acts as an autonomous trading engine within the broader system.
    """
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.thread = None
        
        # Load Config
        self.cfg = Config("config.yaml")
        
        # Use existing components mapped to CapacityBay structure
        self.ex = bot.data_manager # ExchangeAdapter equivalent
        self.risk = bot.risk_manager
        self.exec = bot.execution
        
        # Default to Smart Trend (CapacityBay Standard)
        self.signal = SmartTrendStrategy(bot)  
        
        # Apply Config to Components
        self._apply_config()
        
        self.equity_start = self.risk.current_capital

    def _apply_config(self):
        """Apply YAML config values to bot components"""
        # 1. Symbols & Timeframe
        self.symbols = self.cfg.get("symbols", [self.bot.symbol] if self.bot.symbol else [DEFAULT_SYMBOL])
        self.tf = self.cfg.get("timeframe", self.bot.timeframe)
        self.min_confidence = self.cfg.get("min_confidence", 0.6)
        self.poll_seconds = 15 # Could be added to config
        
        # 2. Risk Params
        risk_cfg = self.cfg.get("risk", {})
        if risk_cfg:
            self.risk.configure(
                risk_per_trade=risk_cfg.get("risk_per_trade", 0.005) * 100, # Convert back to % for configure method? 
                # Wait, configure takes % if named risk_per_trade? 
                # Let's check risk.py: base_risk_per_trade = risk_per_trade / 100.0
                # User config says 0.005 (0.5%).
                # If I pass 0.005 to configure(risk_per_trade=0.005), it divides by 100 -> 0.00005.
                # I should pass 0.5 to configure.
                # OR set directly.
                stop_atr_mult=risk_cfg.get("stop_atr_mult"),
                tp_atr_mult=risk_cfg.get("tp_atr_mult")
            )
            # Handle max_drawdown manually since configure doesn't expose it fully or naming differs
            if "max_drawdown" in risk_cfg:
                self.risk.max_dd = risk_cfg["max_drawdown"]

        # 3. Execution Params
        exec_cfg = self.cfg.get("execution", {})
        # Slippage is usually handled in bot config or logic, current exec engine uses internal params
        # We can inject it if needed, but ExecutionEngine.place uses self.params in the original code.
        # Our ExecutionEngine is attached to bot.
        
        logging.info(f"AutoTrader Configured: {self.symbols} {self.tf}")

    def run_once(self, symbol):
        """
        Single iteration of the trading loop.
        """
        try:
            # 1. Fetch Data
            # Limit 300 matches user code
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe=self.tf, limit=300)
            if ohlcv.empty:
                logging.warning(f"{symbol}: No data fetched.")
                return

            # 2. Compute Features & Signal
            price = ohlcv['close'].iloc[-1]
            atr = (ohlcv['high'].iloc[-1] - ohlcv['low'].iloc[-1]) # Default Crude ATR

            # Support both WeightedSignalStrategy (exposed compute_features) and SmartTrendStrategy (encapsulated)
            if hasattr(self.signal, 'compute_features'):
                df = self.signal.compute_features(ohlcv)
                row = df.iloc[-1]
                if "atr" in row and pd.notna(row["atr"]):
                    atr = row["atr"]
            
            # Use Strategy Logic to get Score
            # execute() fetches its own data usually, but passing data could be optimized in future
            signal_obj = self.signal.execute(symbol, data=ohlcv)
            
            if not signal_obj:
                logging.info(f"{symbol}: No signal generated (Hold/Neutral).")
                return
            
            # Update price/atr from signal if available
            price = signal_obj.price
            if signal_obj.indicators and 'atr' in signal_obj.indicators:
                 atr = signal_obj.indicators['atr']
                
            side = signal_obj.type.lower() # 'buy', 'sell'
            conf = signal_obj.confidence
            details = signal_obj.decision_details
            
            # 3. Filter
            if side == "flat" or side == "hold" or conf < self.min_confidence:
                logging.info(f"{symbol}: Flat/conf={conf:.2f} | details={details}")
                return

            # 4. Circuit Breaker
            if not self.risk.check_circuit_breakers(self.equity_start, self.risk.current_capital):
                logging.warning("Circuit breaker active. Halting trading.")
                self.stop() # Stop the loop
                return

            # 5. Sizing
            qty, stop_distance = self.risk.position_size(price, atr)
            if qty <= 0:
                logging.info("Qty too small; skipping.")
                return

            # 6. Execution
            # Note: self.risk passed as arg to match user code signature I added to execution.py
            trade = self.exec.place(symbol, side, qty, price, atr, self.risk)
            
            # 7. Portfolio Update
            # Bot has internal position tracking, we can update it
            if self.bot.trading_mode not in self.bot.positions:
                 self.bot.positions[self.bot.trading_mode] = []
                 
            self.bot.positions[self.bot.trading_mode].append({
                "symbol": symbol,
                "side": side,
                "qty": qty, 
                "price": price, 
                "atr": atr, 
                **trade
            })
            self.bot.save_positions()
            
            # 8. Log Trade for Dashboard Report
            try:
                packet = {
                    "symbol": symbol,
                    "bias": side.upper(),
                    "entry": price,
                    "stop_loss": trade.get('sl', 0),
                    "take_profit": trade.get('tp', 0),
                    "position_size": qty,
                    "strategy": getattr(self.signal, 'name', 'AutoTrader'),
                    "confidence": conf,
                    "decision": "EXECUTE",
                    "market_regime": details.get('regime', 'Auto'),
                    "execution_score": 1.0, # Assumed perfect execution
                    "components": getattr(signal_obj, 'components', {})
                }
                self.bot.log_trade(packet)
            except Exception as log_err:
                logging.error(f"Failed to log auto trade: {log_err}")

            logging.info(f"Executed: {trade}")
            
        except Exception as e:
            logging.error(f"Error in run_once({symbol}): {e}")

    def monitor_positions(self):
        """
        Monitor open positions for SL/TP hits.
        Acts as a safety net for modes where exchange-side OCO isn't used (like Demo or Simple CEX).
        """
        mode = self.bot.trading_mode
        if mode not in self.bot.positions:
            return

        positions = self.bot.positions[mode]
        # Iterate backwards to allow safe removal
        for i in range(len(positions) - 1, -1, -1):
            pos = positions[i]
            symbol = pos['symbol']
            side = pos['side']
            sl = pos.get('sl', 0)
            tp = pos.get('tp', 0)
            entry = pos.get('entry', 0)
            
            # Skip if no SL/TP
            if not sl and not tp:
                continue
                
            # Get current price
            # We can use fetch_ticker for fresh data
            try:
                ticker = self.ex.fetch_ticker(symbol)
                if not ticker: continue
                
                current_price = ticker['bid'] if side == 'buy' else ticker['ask'] # Conservative price
                
                close_reason = None
                
                # Check SL
                if sl > 0:
                    if side == 'buy' and current_price <= sl:
                        close_reason = "Stop Loss"
                    elif side == 'sell' and current_price >= sl:
                        close_reason = "Stop Loss"
                        
                # Check TP
                if tp > 0:
                    if side == 'buy' and current_price >= tp:
                        close_reason = "Take Profit"
                    elif side == 'sell' and current_price <= tp:
                        close_reason = "Take Profit"
                        
                if close_reason:
                    logging.info(f"{symbol} hit {close_reason} at {current_price} (Entry: {entry}). Closing...")
                    
                    # Execute Close
                    close_side = 'sell' if side == 'buy' else 'buy'
                    self.exec.execute_robust(symbol, close_side, pos['qty'], strategy="market")
                    
                    # Log
                    packet = {
                        "symbol": symbol,
                        "bias": close_side.upper(),
                        "entry": entry,
                        "exit": current_price,
                        "pnl": (current_price - entry) * pos['qty'] if side == 'buy' else (entry - current_price) * pos['qty'],
                        "reason": close_reason,
                        "strategy": "AutoMonitor"
                    }
                    self.bot.log_trade(packet)
                    
                    # Remove from list
                    positions.pop(i)
                    self.bot.save_positions()
                    
            except Exception as e:
                logging.error(f"Error monitoring {symbol}: {e}")

    def loop(self):
        """
        Main Loop
        """
        logging.info("Starting AutoTrader Loop...")
        self.is_running = True
        while self.is_running:
            # 1. Check for New Trades
            for s in self.symbols:
                try:
                    self.run_once(s)
                except Exception as e:
                    logging.exception(f"Error on {s}: {e}")
            
            # 2. Monitor Existing Positions (Auto-Close)
            try:
                self.monitor_positions()
            except Exception as e:
                logging.error(f"Monitor loop error: {e}")
            
            # Sleep logic
            for _ in range(int(self.poll_seconds)):
                if not self.is_running: break
                time.sleep(1)
        logging.info("AutoTrader Loop Stopped.")

    def start(self):
        if not self.is_running:
            self.equity_start = self.risk.current_capital # Reset baseline
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
            print("AutoTrader started in background.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("AutoTrader stopped.")
