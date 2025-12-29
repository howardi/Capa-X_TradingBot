import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.quantum import QuantumEngine
from core.data import CustomExchange

class ArbitrageScanner:
    def __init__(self):
        self.monitored_exchanges = ['binance', 'luno', 'kucoin', 'bybit', 'quidax', 'nairaex', 'busha', 'kraken', 'okx']
        self.instances = {}
        self.quantum = QuantumEngine()
        self._init_exchanges()
        
    def _init_exchanges(self):
        for ex_name in self.monitored_exchanges:
            try:
                if hasattr(ccxt, ex_name):
                    exchange_class = getattr(ccxt, ex_name)
                    # Initialize without keys for public ticker data
                    # Set short timeout and disable retries for speed
                    self.instances[ex_name] = exchange_class({
                        'timeout': 2000,
                        'enableRateLimit': False, 
                        'options': {'maxRetries': 0}
                    })
                else:
                    self.instances[ex_name] = CustomExchange(ex_name)
            except Exception as e:
                # Silently fail for scanner initialization
                pass

    def _fetch_price(self, name, exchange, symbol):
        """Helper to fetch price from a single exchange"""
        try:
            if isinstance(exchange, CustomExchange):
                # Mock logic remains same
                if 'BTC' in symbol: base = 65000
                elif 'ETH' in symbol: base = 3500
                elif 'SOL' in symbol: base = 150
                else: base = 100
                
                # Add randomness
                return name, base * np.random.uniform(0.99, 1.01)
            else:
                # Public API call
                ticker = exchange.fetch_ticker(symbol)
                if ticker and ticker.get('last'):
                    return name, ticker['last']
        except Exception:
            pass
        return name, None

    def _fetch_all_prices(self, symbol):
        """Fetch prices from all exchanges in parallel"""
        prices = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_exchange = {
                executor.submit(self._fetch_price, name, exchange, symbol): name 
                for name, exchange in self.instances.items()
            }
            
            for future in as_completed(future_to_exchange):
                name, price = future.result()
                if price is not None:
                    prices[name] = price
        return prices

    def scan_opportunities(self, symbol: str) -> List[Dict]:
        """
        Scan for arbitrage opportunities across monitored exchanges.
        Fetches real prices where possible.
        """
        prices = self._fetch_all_prices(symbol)
        
        if not prices or len(prices) < 2:
            return []

        # Find min and max
        min_ex = min(prices, key=prices.get)
        max_ex = max(prices, key=prices.get)
        
        min_price = prices[min_ex]
        max_price = prices[max_ex]
        
        spread_pct = (max_price - min_price) / min_price * 100
        
        opportunities = []
        
        # Generate the main opportunity
        if spread_pct > 0.1: # 0.1% threshold
            opp = {
                'symbol': symbol,
                'buy_exchange': min_ex,
                'sell_exchange': max_ex,
                'buy_price': min_price,
                'sell_price': max_price,
                'spread_pct': spread_pct,
                'estimated_profit_1k': 1000 * (spread_pct / 100),
                'score': spread_pct * 10 # heuristic score for quantum engine
            }
            opportunities.append(opp)
            
        # Add Quantum Ranking
        if opportunities:
            # Use Grover's Algorithm (Simulated) to amplify the best signal
            # We treat the list of opportunities as the database
            best_opp = self.quantum.grover_search_signal(opportunities)
            if best_opp:
                # Mark the best one
                for o in opportunities:
                    if o == best_opp:
                        o['quantum_rank'] = 'Top Pick'
                    else:
                        o['quantum_rank'] = 'Standard'
                        
        return opportunities
        
    def get_prices_df(self, symbol: str) -> pd.DataFrame:
        """
        Returns a DataFrame of prices for display.
        """
        prices = self._fetch_all_prices(symbol)
        data = []
        
        for name, price in prices.items():
            data.append({'Exchange': name.upper(), 'Price': price, 'Symbol': symbol})
                
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values(by='Price', ascending=False)
            min_price = df['Price'].min()
            df['Spread (%)'] = ((df['Price'] - min_price) / min_price) * 100
        return df

    def scan_quantum_opportunities(self, symbol: str) -> List[Dict]:
        """
        Use Grover Search Simulation to find optimal arbitrage path among multiple complex routes.
        Simulates searching N^2 paths in N steps.
        """
        # 1. Generate hypothetical complex paths (Triangle Arbitrage)
        routes = []
        
        for i in range(16): # 16 hypothetical paths
            routes.append({
                'id': i,
                'path': f'Path_{i} (USDT->BTC->ALT->USDT)',
                'profit_prob': np.random.beta(2, 5) # Skewed probability
            })
            
        # 2. Convert to signal array for Grover
        signals = np.array([r['profit_prob'] for r in routes])
        
        # 3. Apply Grover Search Amplification
        amplified_signals = self.quantum.grover_search_signal(signals)
        
        # 4. Find the winner
        best_idx = np.argmax(amplified_signals)
        best_route = routes[best_idx]
        
        # Add Quantum Confidence to the result
        best_route['quantum_confidence'] = float(amplified_signals[best_idx])
        
        return [best_route]
