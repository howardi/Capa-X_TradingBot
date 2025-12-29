import time
import pandas as pd
from typing import Dict, Optional

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

    def execute_smart_order(self, symbol: str, side: str, amount: float, strategy: str = "limit"):
        """
        Route order based on strategy (Limit, Market, Iceberg)
        Supports: Demo, CEX_Proxy, CEX_Direct, DEX
        """
        mode = self.bot.trading_mode
        
        # 1. DEMO MODE
        if mode == 'Demo':
            # Simulation Logic
            if strategy == "market":
                return {'id': f'mkt_{int(time.time())}', 'status': 'Filled', 'price': 'Market', 'amount': amount, 'side': side}
                
            elif strategy == "limit":
                ticker = self.bot.data_manager.fetch_ticker(symbol)
                price = ticker['bid'] if side == 'buy' else ticker['ask'] if ticker else 0
                return {'id': f'lmt_{int(time.time())}', 'status': 'Open', 'price': price, 'amount': amount, 'side': side}
                
            elif strategy == "iceberg":
                visible_amount = amount * 0.1
                return {'id': f'ice_{int(time.time())}', 'status': 'Working', 'visible': visible_amount, 'total': amount}

        # 2. CEX MODES (Proxy & Direct)
        elif mode in ['CEX_Proxy', 'CEX_Direct']:
            try:
                if strategy == "market":
                    return self.bot.data_manager.create_order(symbol, 'market', side, amount)
                
                elif strategy == "limit":
                    ticker = self.bot.data_manager.fetch_ticker(symbol)
                    if not ticker:
                        return None
                    price = ticker['bid'] if side == 'buy' else ticker['ask']
                    return self.bot.data_manager.create_order(symbol, 'limit', side, amount, price)
                
                elif strategy == "iceberg":
                    # Simple iceberg implementation for live (executes first chunk)
                    visible_amount = amount * 0.1
                    return self.bot.data_manager.create_order(symbol, 'limit', side, visible_amount)
                    
            except Exception as e:
                print(f"CEX Execution Error ({mode}): {e}")
                return {'status': 'Failed', 'error': str(e)}

        # 3. DEX MODE
        elif mode == 'DEX':
            try:
                print(f"Executing DEX Swap: {side.upper()} {amount} {symbol}")
                if hasattr(self.bot.defi, 'execute_swap'):
                    return self.bot.defi.execute_swap(symbol, side, amount)
                else:
                    return {'status': 'Failed', 'error': 'DEX Execution not implemented in DeFiManager'}
            except Exception as e:
                 print(f"DEX Execution Error: {e}")
                 return {'status': 'Failed', 'error': str(e)}
        
        return None

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
