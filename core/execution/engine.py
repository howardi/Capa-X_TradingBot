import time
import pandas as pd
from typing import Dict, Optional
try:
    from tenacity import retry, stop_after_attempt, wait_exponential
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Mock decorator if tenacity missing
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def stop_after_attempt(n): return None
    def wait_exponential(min, max): return None

class ExecutionEngine:
    def __init__(self, bot):
        self.bot = bot
        self.active_orders = []
        
    def execute_twap(self, symbol: str, side: str, total_amount: float, duration_minutes: int, chunks: int):
        """
        Execute a Time-Weighted Average Price (TWAP) order.
        Splits a large order into smaller chunks over time.
        """
        chunk_size = total_amount / chunks
        interval = (duration_minutes * 60) / chunks
        
        execution_plan = []
        
        start_time = pd.Timestamp.now()
        
        for i in range(chunks):
            exec_time = start_time + pd.Timedelta(seconds=interval * i)
            execution_plan.append({
                'chunk_id': i + 1,
                'symbol': symbol,
                'side': side,
                'amount': chunk_size,
                'scheduled_time': exec_time,
                'status': 'Pending'
            })
            
        return execution_plan

    def place(self, symbol, side, qty, price, atr, risk_manager):
        """
        Place order with attached SL/TP.
        Matches CapacityBay requirements.
        """
        # Calculate SL/TP using the passed risk manager
        sl, tp = risk_manager.stop_take_levels(side, price, atr)
        stop_loss_price = sl  # Alias for compatibility if referenced explicitly
        
        # Log intent
        print(f"Placing {side} {qty} {symbol} at {price:.2f} | SL {sl:.2f} TP {tp:.2f}")
        
        # Execute via Robust Engine
        # CapacityBay uses limit orders by default logic
        order = self.execute_robust(symbol, side, qty, price, strategy="limit", sl=sl, tp=tp)
        
        return {"order": order, "sl": sl, "tp": tp}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def execute_robust(self, symbol, side, amount, price=None, strategy="limit", sl=None, tp=None):
        """
        Robust execution with retries (Tenacity).
        Wraps execute_smart_order.
        """
        print(f"Executing Robust Order: {side} {amount} {symbol} (Attempting...)")
        result = self.execute_smart_order(symbol, side, amount, price, strategy, sl, tp)
        
        # Check if result indicates failure (dict with status 'Failed' or None)
        if result is None or (isinstance(result, dict) and result.get('status') == 'Failed'):
            raise Exception(f"Order Execution Failed: {result}")
            
        # Track Order
        self.active_orders.insert(0, result)
        if len(self.active_orders) > 50:
            self.active_orders.pop()
            
        return result

    def execute_smart_order(self, symbol: str, side: str, amount: float, price: float = None, strategy: str = "limit", sl=None, tp=None):
        """
        Route order based on strategy (Limit, Market, Iceberg)
        Supports: Demo, CEX_Proxy, CEX_Direct, DEX
        """
        stop_loss_price = sl  # Ensure variable is bound if referenced locally
        mode = self.bot.trading_mode
        
        # 1. DEMO MODE
        if mode == 'Demo':
            # Simulation Logic
            order = None
            if strategy in ["market", "manual_close"]:
                order = {'id': f'mkt_{int(time.time())}', 'status': 'Filled', 'price': 'Market', 'amount': amount, 'side': side}
                
            elif strategy == "limit":
                if price is None:
                    ticker = self.bot.data_manager.fetch_ticker(symbol)
                    price = ticker['bid'] if side == 'buy' else ticker['ask'] if ticker else 0
                order = {'id': f'lmt_{int(time.time())}', 'status': 'Open', 'price': price, 'amount': amount, 'side': side}
                
            elif strategy == "iceberg":
                visible_amount = amount * 0.1
                order = {'id': f'ice_{int(time.time())}', 'status': 'Working', 'visible': visible_amount, 'total': amount}
            
            # Attach SL/TP to demo order for tracking
            if order:
                order['sl'] = sl
                order['tp'] = tp
                
                # Manual Ledger: Update Balance (Demo)
                # Ensure we have a price
                entry_price = order.get('price')
                if entry_price == 'Market':
                    # Fetch current price if market
                    ticker = self.bot.data_manager.fetch_ticker(symbol)
                    entry_price = ticker['bid'] if side == 'buy' else ticker['ask'] if ticker else 0
                    
                cost = amount * entry_price
                if cost > 0:
                     if side == 'buy':
                         self.bot.risk_manager.deduct_capital(cost)
                     elif side == 'sell':
                         self.bot.risk_manager.credit_capital(cost)
                     
            return order

        # 2. CEX MODES (Proxy & Direct)
        elif mode in ['CEX_Proxy', 'CEX_Direct']:
            try:
                result = None
                if strategy in ["market", "manual_close"]:
                    result = self.bot.data_manager.create_order(symbol, 'market', side, amount)
                
                elif strategy == "limit":
                    if price is None:
                        ticker = self.bot.data_manager.fetch_ticker(symbol)
                        if not ticker:
                            return None
                        price = ticker['bid'] if side == 'buy' else ticker['ask']
                    result = self.bot.data_manager.create_order(symbol, 'limit', side, amount, price)
                
                elif strategy == "iceberg":
                    # Simple iceberg implementation for live (executes first chunk)
                    visible_amount = amount * 0.1
                    result = self.bot.data_manager.create_order(symbol, 'limit', side, visible_amount)
                
                # Attach SL/TP if successful
                if result:
                    result['sl'] = sl
                    result['tp'] = tp
                    
                    # Manual Ledger: Update Balance
                    cost = amount * price if price else 0
                    if cost > 0:
                        if side == 'buy':
                            self.bot.risk_manager.deduct_capital(cost)
                        elif side == 'sell':
                            self.bot.risk_manager.credit_capital(cost)

                    # Sync balance immediately after trade to reflect changes
                    print(f"Trade Executed ({mode}). Syncing balance...")
                    try:
                        if hasattr(self.bot, 'sync_live_balance'):
                            self.bot.sync_live_balance()
                    except Exception as e:
                        print(f"Balance Sync Warning: {e}")
                
                return result

                    
            except Exception as e:
                print(f"CEX Execution Error ({mode}): {e}")
                return {'status': 'Failed', 'error': str(e)}

        # 3. DEX MODE
        elif mode == 'DEX':
            try:
                print(f"Executing DEX Swap: {side.upper()} {amount} {symbol}")
                if hasattr(self.bot.defi, 'execute_swap'):
                    result = self.bot.defi.execute_swap(symbol, side, amount)
                    return result
                else:
                    return {'status': 'Failed', 'error': 'DEX Execution not implemented in DeFiManager'}
            except Exception as e:
                 print(f"DEX Execution Error: {e}")
                 return {'status': 'Failed', 'error': str(e)}

        # 4. LIVE / WEB3 MODE
        elif mode == 'Live':
             # Try Web3 Wallet first
             if hasattr(self.bot, 'web3_wallet') and self.bot.web3_wallet.is_connected():
                 try:
                     print(f"Executing Live Web3 Transaction: {side.upper()} {amount} {symbol}")
                     # For real execution, we need a destination address (e.g. Router or Recipient)
                     # Since this is a generic 'place order' call, we assume interaction with a Router/Contract 
                     # or a transfer if explicitly defined. 
                     # For now, we will return an error if specific routing logic isn't defined, 
                     # rather than using a fake simulation address.
                     
                     # TODO: Implement proper router address resolution for Live Trading
                     return {'status': 'Failed', 'error': 'Live Web3 Execution requires a valid destination/router address.'}
                 except Exception as e:
                     print(f"Web3 Execution Error: {e}")
                     return {'status': 'Failed', 'error': str(e)}
             
             # Fallback to CEX logic if not Web3 (e.g. Binance API)
             if self.bot.data_manager.exchange:
                 try:
                     if strategy == "market":
                         return self.bot.data_manager.create_order(symbol, 'market', side, amount)
                     elif strategy == "limit":
                         if price is None:
                             ticker = self.bot.data_manager.fetch_ticker(symbol)
                             price = ticker['bid'] if side == 'buy' else ticker['ask']
                         return self.bot.data_manager.create_order(symbol, 'limit', side, amount, price)
                 except Exception as e:
                     return {'status': 'Failed', 'error': str(e)}

        return None

    def close_position(self, position):
        """
        Close a specific position.
        """
        symbol = position.get('symbol')
        amount = position.get('amount', position.get('position_size', 0))
        side = position.get('side', position.get('type', 'buy')).lower()
        
        # Determine close side
        close_side = 'sell' if side in ['buy', 'long'] else 'buy'
        
        try:
            print(f"Closing Position: {symbol} {side} {amount} -> {close_side}")
            self.execute_robust(symbol, close_side, amount, strategy='manual_close')
            
            # Remove from positions list
            if position in self.bot.open_positions:
                self.bot.open_positions.remove(position)
                self.bot.save_positions()
                
            return True
        except Exception as e:
            print(f"Failed to close {symbol}: {e}")
            return False

    def close_all(self):
        """
        Close all open positions for the current mode.
        """
        print("Closing ALL Positions...")
        positions = self.bot.open_positions
        positions_to_remove = []
        
        # We iterate a copy because we might modify the list (or the callbacks might)
        for pos in list(positions):
            symbol = pos.get('symbol')
            amount = pos.get('amount')
            side = pos.get('side', 'buy').lower()
            
            # Determine close side
            close_side = 'sell' if side in ['buy', 'long'] else 'buy'
            
            try:
                self.execute_robust(symbol, close_side, amount, strategy='manual_close')
                print(f"Closed {symbol} ({amount})")
                positions_to_remove.append(pos)
            except Exception as e:
                print(f"Failed to close {symbol}: {e}")
        
        # Remove successfully closed positions
        for pos in positions_to_remove:
            if pos in self.bot.open_positions:
                self.bot.open_positions.remove(pos)
                
        self.bot.save_positions()

    def execute_vwap(self, symbol: str, side: str, total_amount: float, duration_minutes: int):
        """
        Execute a Volume-Weighted Average Price (VWAP) order.
        Approximates VWAP by weighting execution based on typical volume profiles (U-shape).
        """
        chunks = 10
        interval = (duration_minutes * 60) / chunks
        
        # Simplified Volume Profile (U-Shape: High at start/end, Low in middle)
        # Weights: [0.15, 0.12, 0.10, 0.08, 0.05, 0.05, 0.08, 0.10, 0.12, 0.15]
        weights = [0.15, 0.12, 0.10, 0.08, 0.05, 0.05, 0.08, 0.10, 0.12, 0.15]
        
        # Normalize weights if they don't sum to 1
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        execution_plan = []
        start_time = pd.Timestamp.now()
        
        for i in range(chunks):
            chunk_amount = total_amount * weights[i]
            exec_time = start_time + pd.Timedelta(seconds=interval * i)
            
            execution_plan.append({
                'chunk_id': i + 1,
                'symbol': symbol,
                'side': side,
                'amount': chunk_amount,
                'scheduled_time': exec_time,
                'algo': 'VWAP',
                'status': 'Pending'
            })
            
        return execution_plan
