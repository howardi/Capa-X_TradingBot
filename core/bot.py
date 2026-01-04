
import time
# Ensure DNS fix is active
import core.dns_fix
from datetime import datetime
import pandas as pd
from core.data import DataManager
from core.analysis import TechnicalAnalysis
from core.fundamentals import FundamentalAnalysis
from core.models import Signal
from core.risk import AdaptiveRiskManager
from core.strategies import (
    SmartTrendStrategy, GridTradingStrategy, MeanReversionStrategy, 
    FundingArbitrageStrategy, BasisTradeStrategy, LiquiditySweepStrategy, OrderFlowStrategy,
    SwingRangeStrategy, SniperStrategy, WeightedSignalStrategy
)
from core.arbitrage import ArbitrageScanner
from core.sentiment import SentimentEngine
from core.execution import ExecutionEngine
from core.security import SecurityManager
from core.defi import DeFiManager
from core.alerts import NotificationManager
from core.feature_store import FeatureStore
from core.compliance import ComplianceManager
from core.auto_trader import AutoTrader
# Keep ProfitOptimizer lightweight import or lazy load if possible.
# But it is used in __init__. Let's import it but check if it's heavy.
# It imports pandas and numpy. Not too heavy.
from core.allocator import ProfitOptimizer 
from config.settings import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME

import json
import os

class TradingBot:
    def __init__(self, exchange_id='binance'):
        self.data_manager = DataManager(exchange_id)
        self.analyzer = TechnicalAnalysis()
        self.fundamentals = FundamentalAnalysis()
        
        # Lazy Loading for Heavy Modules
        self._brain = None
        self._quantum = None
        self._portfolio_opt = None
        self._drift_detector = None
        self._ai_trainer = None
        
        self.risk_manager = AdaptiveRiskManager()
        self.security = SecurityManager()
        
        # New Modules
        self.arbitrage = ArbitrageScanner()
        self.sentiment = SentimentEngine()
        self.execution = ExecutionEngine(self)
        self.defi = DeFiManager()
        self.notifications = NotificationManager()
        self.feature_store = FeatureStore()
        self.compliance = ComplianceManager(self)
        
        self.is_running = False
        self.symbol = DEFAULT_SYMBOL
        self.timeframe = DEFAULT_TIMEFRAME
        
        # Auto-Trading Engine (CapaXBot Logic)
        self.auto_trader = AutoTrader(self)
        self.trading_mode = 'Demo' # Default to Demo
        self.last_trade_time = None
        self.trade_log_file = "trade_log.json"
        
        self.positions_file = "active_positions.json"
        # Initialize positions for all 4 modes
        self.positions = {
            'Demo': [], 
            'CEX_Proxy': [], 
            'CEX_Direct': [], 
            'DEX': []
        }
        self.pending_transactions = [] # For Manual/Web3 Approvals
        self.load_positions()
        
        # Wallet State
        self.wallet_balances = [] # Stores detailed asset breakdown (List of dicts)
        
        # Initialize Strategies
        self.strategies = {
            "Smart Trend": SmartTrendStrategy(self),
            "Sniper Mode": SniperStrategy(self),
            "Grid Trading": GridTradingStrategy(self),
            "Mean Reversion": MeanReversionStrategy(self),
            "Funding Arbitrage": FundingArbitrageStrategy(self),
            "Basis Trade": BasisTradeStrategy(self),
            "Liquidity Sweep": LiquiditySweepStrategy(self),
            "Order Flow": OrderFlowStrategy(self),
            "Swing Range": SwingRangeStrategy(self),
            "Weighted Ensemble": WeightedSignalStrategy(self)
        }
        self.active_strategy_name = "Smart Trend"
        self.active_strategy = self.strategies[self.active_strategy_name]
        
        # Initialize Profit Optimizer (Contextual Multi-Armed Bandit)
        self.profit_optimizer = ProfitOptimizer(list(self.strategies.keys()))
        
    @property
    def brain(self):
        if self._brain is None:
            from core.brain import CapaXBrain
            self._brain = CapaXBrain()
        return self._brain

    @property
    def quantum(self):
        if self._quantum is None:
            from core.quantum import QuantumEngine
            self._quantum = QuantumEngine()
        return self._quantum

    @property
    def portfolio_opt(self):
        if self._portfolio_opt is None:
            from core.ai import PortfolioOptimizer
            self._portfolio_opt = PortfolioOptimizer()
        return self._portfolio_opt

    @property
    def drift_detector(self):
        if self._drift_detector is None:
            from core.ai import DriftDetector
            self._drift_detector = DriftDetector()
        return self._drift_detector

    @property
    def ai_trainer(self):
        if self._ai_trainer is None:
            from core.ai_optimizer import AITrainer
            self._ai_trainer = AITrainer(self)
        return self._ai_trainer

    @property
    def open_positions(self):
        """Return the list of positions for the active trading mode"""
        return self.positions.get(self.trading_mode, [])
    
    @open_positions.setter
    def open_positions(self, value):
        """Set positions (mostly for initialization or clearing)"""
        self.positions[self.trading_mode] = value

    def load_positions(self):
        """Load active positions from file to persist state across restarts"""
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    data = json.load(f)
                    
                    # Migration Logic: Old formats to New
                    if 'Simulation' in data:
                        if 'Demo' not in data: data['Demo'] = data.pop('Simulation')
                    if 'Live' in data:
                         # Default legacy 'Live' to 'CEX_Direct' if undefined, or keep as is?
                         # Let's map Live -> CEX_Direct for safety
                        if 'CEX_Direct' not in data: data['CEX_Direct'] = data.pop('Live')
                        
                    # Ensure all keys exist
                    for mode in ['Demo', 'CEX_Proxy', 'CEX_Direct', 'DEX']:
                        if mode not in data:
                            data[mode] = []
                            
                    self.positions = data
            
            # Sync with Risk Manager
            self.risk_manager.open_positions = self.positions.get(self.trading_mode, [])
            
        except Exception as e:
            print(f"Failed to load positions: {e}")

    def save_positions(self):
        """Save active positions to file"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=4)
        except Exception as e:
            print(f"Failed to save positions: {e}")

    def set_trading_mode(self, mode):
        """Switch between 4 Trading Environments"""
        valid_modes = ['Demo', 'CEX_Proxy', 'CEX_Direct', 'DEX']
        
        if mode in valid_modes:
            print(f"[INFO] Switching Trading Mode: {self.trading_mode} -> {mode}")
            self.trading_mode = mode
            
            # 1. Configure Risk Manager Mode
            # Pass the specific mode to Risk Manager (Demo, CEX_Proxy, CEX_Direct, DEX)
            self.risk_manager.set_mode(mode)
            
            # 2. Configure Connection / Proxy
            if mode == 'CEX_Proxy':
                self.data_manager.set_proxy_mode(use_proxy=True)
            elif mode == 'CEX_Direct':
                # Use proxy if configured in settings (Critical for restricted regions)
                # If no proxy is set in settings, this has no effect.
                self.data_manager.set_proxy_mode(use_proxy=True)
            elif mode == 'DEX':
                # DEX Logic (might not need DataManager proxy change, but let's default to no proxy for RPC)
                # Unless RPC requires it? Usually not.
                self.data_manager.set_proxy_mode(use_proxy=False)
            
            # 3. Sync positions to Risk Manager
            self.risk_manager.open_positions = self.positions.get(mode, [])
            
            # 4. Sync Balance
            if mode != 'Demo':
                self.sync_live_balance()
            else:
                print(f"Demo Balance: ${self.risk_manager.current_capital:.2f}")
                
            return True
        else:
            print(f"❌ Invalid Mode: {mode}")
            return False

    def sync_live_balance(self):
        """Fetch real balance from exchange/chain and update risk manager"""
        # Ensure wallet_balances exists and is reset
        self.wallet_balances = []
        
        try:
            if self.trading_mode == 'DEX':
                # Fetch Wallet Balance via DeFi Manager
                if self.defi.account or (self.defi.current_chain == 'solana'):
                    # 1. Get Native Balance (e.g., 1.5 ETH)
                    native_bal = self.defi.get_balance()
                    
                    # 2. Get Price in USD (e.g., ETH/USDT)
                    chain_config = self.defi.CHAINS.get(self.defi.current_chain, {})
                    native_symbol = chain_config.get('symbol', 'ETH')
                    pair_symbol = f"{native_symbol}/USDT"
                    
                    price = self.data_manager.get_current_price(pair_symbol)
                    
                    # 3. Calculate USD Value
                    if price > 0:
                        usd_bal = native_bal * price
                        print(f"Synced DEX Balance: {native_bal:.4f} {native_symbol} (~${usd_bal:.2f})")
                        self.risk_manager.update_live_balance(usd_bal)
                    else:
                        print(f"⚠️ Could not fetch price for {pair_symbol}. Balance: {native_bal:.4f} {native_symbol}")
                        # Fallback: Don't update USD balance or update with 0? 
                        # Better to keep previous or 0 if completely unknown.
                        # For now, let's update with 0 if price is missing to be safe
                        self.risk_manager.update_live_balance(0.0) 
                else:
                    print("[WARN] No Wallet Loaded for DEX Mode")
            
            elif self.trading_mode in ['CEX_Proxy', 'CEX_Direct']:
                print("DEBUG: Fetching balance from DataManager...")
                
                # Debug Log File
                with open("debug_wallet_log.txt", "w", encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] Starting Sync\n")
                    if self.data_manager.offline_mode:
                        f.write("WARNING: DataManager is in Offline Mode! Balance data is fake/mock.\n")

                # 1. Fetch Default Balance (Unified/Spot)
                try:
                    balance = self.data_manager.get_balance()
                    
                    # STRICT CHECK: Ensure 'total' exists (Critical for correct parsing)
                    if balance and 'total' not in balance:
                         print("[WARN] Spot balance missing 'total' field. Retrying once...")
                         balance = self.data_manager.get_balance(force_refresh=True)
                         
                    with open("debug_wallet_log.txt", "a", encoding='utf-8') as f:
                        f.write(f"Spot Balance Keys: {list(balance.keys())}\n")
                        # Log raw structure for debugging
                        f.write(f"Raw Balance Type: {type(balance)}\n")
                        if balance:
                            f.write(f"Raw Balance Sample: {str(balance)[:500]}...\n")
                        
                        # DEBUG: Inspect specific assets requested by user
                        target_assets = ['HMSTR', 'LDPEPE', 'PIXEL', 'SOL', 'USDT', 'BTC']
                        f.write("\n--- Target Asset Inspection ---\n")
                        for asset in target_assets:
                            if asset in balance:
                                f.write(f"Asset: {asset}\n")
                                f.write(f"  Value: {balance[asset]}\n")
                                f.write(f"  Type: {type(balance[asset])}\n")
                            else:
                                f.write(f"Asset: {asset} NOT FOUND in keys.\n")
                        f.write("-----------------------------\n")

                        if 'total' in balance:
                            f.write(f"Spot Total Dict found. Items: {len(balance['total'])}\n")
                        else:
                            f.write("Spot 'total' Dict NOT found.\n")
                            
                except Exception as e:
                    error_str = str(e)
                    with open("debug_wallet_log.txt", "a", encoding='utf-8') as f:
                        f.write(f"ERROR Fetching Spot: {error_str}\n")
                    
                    # STRICT ERROR HANDLING: Check for Invalid API Key (-2008)
                    if "-2008" in error_str or "Invalid Api-Key ID" in error_str:
                        print("\n[CRITICAL] INVALID API KEY DETECTED (-2008)")
                        print("Stopping Sync. Invalidating Credentials.")
                        
                        # Invalidate in DataManager
                        if self.data_manager.exchange:
                            self.data_manager.exchange.apiKey = None
                            self.data_manager.exchange.secret = None
                        
                        raise Exception("CRITICAL_API_ERROR: -2008 Invalid Api-Key ID. Credentials have been invalidated. Please re-enter them.")
                        
                    # Stop sync on any API error (Strict Mode)
                    raise e

                print(f"DEBUG: Balance fetched. Keys: {list(balance.keys())[:5]}")
                
                # 2. Fetch Funding Wallet (Strict Mode)
                try:
                    print("DEBUG: Fetching Funding Wallet...")
                    funding_balance = self.data_manager.exchange.fetch_balance({'type': 'funding'})
                    if funding_balance and 'total' in funding_balance:
                        # Merge into main balance logic or append
                        # For now, let's merge the 'total' dicts if we want unified view, 
                        # but user might want separation. The UI expects a flat list in wallet_balances.
                        # We will process it similar to Spot.
                        print(f"DEBUG: Funding Balance Fetched. Items: {len(funding_balance['total'])}")
                        
                        for currency, amount in funding_balance['total'].items():
                            if amount and float(amount) > 0:
                                # Check if already exists from Spot (to avoid duplicates or merge?)
                                # Strategy: Add as separate entry with type 'Funding'
                                self.wallet_balances.append({
                                    'asset': currency,
                                    'free': float(funding_balance.get('free', {}).get(currency, 0)),
                                    'locked': float(funding_balance.get('used', {}).get(currency, 0)),
                                    'total': float(amount),
                                    'value_usd': 0.0, # Will be calculated later
                                    'source': 'Funding'
                                })
                except Exception as e:
                    print(f"[ERROR] Failed to fetch Funding Wallet: {e}")
                    # Strict Mode: Stop sync on any failure as requested
                    raise Exception(f"Funding Wallet Sync Failed: {e}")

                # 3. Fetch Earn/Flexible (Often in Spot as LD*, but sometimes separate)
                # We already handle LD* in Spot. Let's try explicit 'earn' endpoint if available
                # Binance often uses 'sapi' endpoints for this which CCXT might map to specific methods.
                # For now, we rely on Spot LD* + Funding. 
                
                # Store detailed balances for UI
                # self.wallet_balances is already being populated above for Funding.
                # Now process Spot (balance variable)
                
                # Robust extraction of balances (Method A: 'total' dict)
                assets_found = set()
                
                if 'total' in balance:
                    for currency, amount in balance['total'].items():
                        try:
                            # User Request: Show zero balances too.
                            # So we extract everything present in the 'total' dict.
                            # We only filter if amount is None or invalid type.
                            if amount is not None:
                                assets_found.add(currency)
                                # Handle Binance Earn (LD Prefix)
                                display_asset = currency
                                source_tag = 'Spot'
                                if currency.startswith('LD'):
                                    display_asset = f"{currency[2:]}"
                                    source_tag = 'Earn (Flexible)'
                                
                                free_val = 0.0
                                locked_val = 0.0
                                
                                try:
                                    free_val = float(balance.get('free', {}).get(currency, 0))
                                    locked_val = float(balance.get('used', {}).get(currency, 0))
                                except:
                                    pass

                                self.wallet_balances.append({
                                    'asset': display_asset,
                                    'total': float(amount),
                                    'free': free_val,
                                    'locked': locked_val
                                })
                        except Exception as e:
                             with open("debug_wallet_log.txt", "a", encoding='utf-8') as f:
                                f.write(f"ERROR parsing asset {currency}: {e}\n")

                # Method B: Iterate over 'free' dict if 'total' missed some or didn't exist
                if 'free' in balance:
                    for currency, amount in balance['free'].items():
                        try:
                            if currency not in assets_found and amount is not None:
                                # Calculate total if possible
                                free = float(amount)
                                used = float(balance.get('used', {}).get(currency, 0.0))
                                total = free + used
                                
                                assets_found.add(currency)
                                display_asset = currency
                                if currency.startswith('LD'):
                                    display_asset = f"{currency[2:]} (Earn)"
                                
                                self.wallet_balances.append({
                                    'asset': display_asset,
                                    'total': total,
                                    'free': free,
                                    'locked': used
                                })
                        except Exception as e:
                             with open("debug_wallet_log.txt", "a", encoding='utf-8') as f:
                                f.write(f"ERROR parsing free asset {currency}: {e}\n")


                # Method C: Iterate over root keys (for assets that act as objects, e.g. balance['BTC'] = {'free':...})
                # This handles cases where 'total' aggregate dict is missing but individual asset keys exist
                for currency, data in balance.items():
                    if currency in ['info', 'free', 'used', 'total', 'timestamp', 'datetime']:
                        continue
                    if currency in assets_found:
                        continue
                    
                    if isinstance(data, dict):
                        try:
                            # Relaxed filter: Allow 0 balances
                            total = float(data.get('total', 0.0))
                            
                            assets_found.add(currency)
                            display_asset = currency
                            if currency.startswith('LD'):
                                display_asset = f"{currency[2:]} (Earn)"
                            
                            self.wallet_balances.append({
                                'asset': display_asset,
                                'total': total,
                                'free': float(data.get('free', 0.0)),
                                'locked': float(data.get('used', 0.0))
                            })
                        except:
                            pass
                
                # Log Found Assets to Debug File
                with open("debug_wallet_log.txt", "a", encoding='utf-8') as f:
                    f.write(f"\n--- Extracted Assets ({len(self.wallet_balances)}) ---\n")
                    # Log first 20 and last 20 if too many
                    log_items = self.wallet_balances if len(self.wallet_balances) < 50 else self.wallet_balances[:20] + self.wallet_balances[-20:]
                    for item in log_items:
                        f.write(f"{item['asset']}: {item['total']} (Free: {item['free']}, Locked: {item['locked']})\n")
                    if len(self.wallet_balances) >= 50:
                        f.write(f"... and {len(self.wallet_balances) - 40} more ...\n")

                # Fallback for Bybit V5 Unified if CCXT 'total' is empty/incomplete
                if not self.wallet_balances and self.data_manager.exchange_id == 'bybit':
                    try:
                        raw = balance.get('info', {})
                        if raw.get('retCode') == 0:
                            acct_list = raw.get('result', {}).get('list', [])
                            if acct_list:
                                coins = acct_list[0].get('coin', [])
                                for c in coins:
                                    w_bal = float(c.get('walletBalance', 0))
                                    if w_bal > 0:
                                        self.wallet_balances.append({
                                            'asset': c.get('coin'),
                                            'total': w_bal,
                                            'free': float(c.get('availableToWithdraw', w_bal)),
                                            'locked': float(c.get('locked', 0))
                                        })
                    except Exception as parse_err:
                        print(f"Bybit raw balance parse failed: {parse_err}")

                # Try to get Equity from different possible keys
                usdt_bal = 0.0
                if balance:
                    usdt_bal = balance.get('USDT', {}).get('total', 0.0)
                    
                    # Check for LDUSDT (Binance Earn) and treat as liquid
                    ld_usdt = balance.get('LDUSDT', {}).get('total', 0.0)
                    if ld_usdt > 0:
                         usdt_bal += ld_usdt
                         print(f"Added LDUSDT (Earn) to Total Equity: {ld_usdt}")
    
                    if usdt_bal == 0.0:
                         usdt_bal = balance.get('USD', {}).get('total', 0.0)
                
                # UTA Check: If CCXT parsing missed it, check raw 'info'
                if usdt_bal == 0.0 and balance and 'info' in balance:
                    try:
                        # Bybit V5 UTA structure: result -> list -> [0] -> totalEquity
                        info = balance.get('info')
                        if isinstance(info, dict) and 'result' in info:
                             result = info['result']
                             if isinstance(result, dict) and 'list' in result:
                                 account_list = result['list']
                                 if account_list and len(account_list) > 0:
                                     equity = float(account_list[0].get('totalEquity', 0.0))
                                     if equity > 0:
                                         usdt_bal = equity
                                         print(f"Found UTA Equity: {equity}")
                    except Exception as e:
                        print(f"UTA Parsing Error: {e}")

                # 2. Fetch Funding Wallet (Logic moved to top of block)
                # Removed duplicate block

                # 3. Fetch Binance Earn (Simple Earn Flexible)
                if self.data_manager.exchange_id == 'binance':
                    try:
                        with open("debug_wallet_log.txt", "a") as f:
                             f.write("Attempting Binance Earn (Flexible) fetch...\n")
                        
                        # Use raw fetch via implicit API if method wrapper missing
                        # Endpoint: GET /sapi/v1/simple-earn/flexible/position
                        earn_data = None
                        if hasattr(self.data_manager.exchange, 'sapi_get_simple_earn_flexible_position'):
                            earn_data = self.data_manager.exchange.sapi_get_simple_earn_flexible_position()
                        
                        if earn_data:
                            rows = []
                            if isinstance(earn_data, dict) and 'rows' in earn_data:
                                rows = earn_data['rows']
                            elif isinstance(earn_data, list):
                                rows = earn_data
                                
                            with open("debug_wallet_log.txt", "a") as f:
                                f.write(f"Earn Rows Found: {len(rows)}\n")

                            for pos in rows:
                                asset = pos.get('asset')
                                amount = float(pos.get('totalAmount', 0.0))
                                if amount > 0:
                                    self.wallet_balances.append({
                                        'asset': f"{asset} (Earn)",
                                        'total': amount,
                                        'free': amount, # Flexible is liquid-ish
                                        'locked': 0.0
                                    })
                                    
                                    # Add to USDT Equity if USDT
                                    if asset == 'USDT':
                                        usdt_bal += amount
                                        
                    except Exception as earn_e:
                        # Strict Mode: Report Earn failure
                        print(f"[ERROR] Earn Fetch Failed: {earn_e}")
                        # Strict Mode: Stop sync on any failure as requested
                        raise Exception(f"Earn Wallet Sync Failed: {earn_e}")

                self.risk_manager.update_live_balance(usdt_bal)
                print(f"Synced Live Balance ({self.trading_mode}): ${usdt_bal:.2f}")
                
        except Exception as e:
            print(f"[ERROR] Failed to sync live balance: {e}")
            
            # Re-raise to ensure UI catches critical errors (like -2008)
            # Extra check: If -2008, ensure we strip credentials in bot instance too if data_manager missed it
            if "-2008" in str(e) or "Invalid Api-Key ID" in str(e):
                 if self.data_manager and self.data_manager.exchange:
                     self.data_manager.exchange.apiKey = None
                     self.data_manager.exchange.secret = None
            
            raise e

    def set_strategy(self, strategy_name):
        if strategy_name == "Meta-Allocator" or strategy_name in self.strategies:
            self.active_strategy_name = strategy_name
            if strategy_name in self.strategies:
                self.active_strategy = self.strategies[strategy_name]
            return True
        return False

    def log_trade(self, decision_packet):
        """
        Self-Audit: Record trade details for post-trade review.
        """
        import numpy as np
        
        # Helper to convert numpy types to native types
        def convert_numpy(obj):
            if isinstance(obj, (np.integer, int)):
                return int(obj)
            elif isinstance(obj, (np.floating, float)):
                return float(obj)
            elif isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            return obj

        # Sanitize packet
        clean_packet = {k: convert_numpy(v) for k, v in decision_packet.items()}
        if 'components' in clean_packet:
            clean_packet['components'] = {k: convert_numpy(v) for k, v in clean_packet['components'].items()}

        trade_record = {
            "timestamp": str(datetime.now()),
            "symbol": self.symbol,
            "type": clean_packet.get('bias', 'UNKNOWN'),
            "strategy": clean_packet.get('strategy', 'Unknown'),
            "entry": clean_packet.get('entry', 0),
            "stop_loss": clean_packet.get('stop_loss', 0),
            "take_profit": clean_packet.get('take_profit', 0),
            "risk_percent": clean_packet.get('risk_percent', 0),
            "confidence": clean_packet.get('confidence', 0),
            "regime": clean_packet.get('market_regime', 'Unknown'),
            "execution_score": clean_packet.get('execution_score', 0),
            "components": clean_packet.get('components', {}),
            "audit_status": "OPEN"
        }
        
        try:
            if os.path.exists(self.trade_log_file):
                try:
                    with open(self.trade_log_file, 'r') as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    print("Warning: trade_log.json corrupted. specific trade log will be reset.")
                    logs = []
            else:
                logs = []
                
            logs.append(trade_record)
            
            with open(self.trade_log_file, 'w') as f:
                json.dump(logs, f, indent=4)
                
            # Track Open Position in Memory
            if decision_packet.get('decision') == 'EXECUTE':
                self.open_positions.append({
                    "symbol": self.symbol,
                    "type": decision_packet.get('bias', 'UNKNOWN'),
                    "entry": decision_packet.get('entry', 0),
                    "stop_loss": decision_packet.get('stop_loss', 0),
                    "take_profit": decision_packet.get('take_profit', 0),
                    "strategy": decision_packet.get('strategy', 'Unknown'),
                    "position_size": decision_packet.get('position_size', 0)
                })
                self.save_positions()
                
        except Exception as e:
            print(f"Failed to log trade: {e}")

    def update_positions(self, current_price):
        """
        Check open positions for Stop Loss or Take Profit hits.
        """
        for position in self.open_positions[:]: # Iterate copy to allow removal
            symbol = position['symbol']
            bias = position['type']
            entry = position['entry']
            sl = position['stop_loss']
            tp = position['take_profit']
            
            # Simple simulation logic
            closed = False
            reason = ""
            pnl = 0.0
            
            if bias == 'BUY':
                if current_price <= sl and sl > 0:
                    closed = True
                    reason = "Stop Loss"
                    pnl = (sl - entry) / entry
                elif current_price >= tp and tp > 0:
                    closed = True
                    reason = "Take Profit"
                    pnl = (tp - entry) / entry
            elif bias == 'SELL':
                if current_price >= sl and sl > 0:
                    closed = True
                    reason = "Stop Loss"
                    pnl = (entry - sl) / entry
                elif current_price <= tp and tp > 0:
                    closed = True
                    reason = "Take Profit"
                    pnl = (entry - tp) / entry
                    
            if closed:
                print(f"Position Closed: {symbol} {bias} | {reason} @ {current_price} | PnL: {pnl:.2%}")
                self.open_positions.remove(position)
                self.save_positions()
                
                # Calculate Real PnL Amount
                pos_size = position.get('position_size', 0)
                pnl_amount = 0.0
                if bias == 'BUY':
                    pnl_amount = (current_price - entry) * pos_size
                elif bias == 'SELL':
                    pnl_amount = (entry - current_price) * pos_size
                
                trade_result = 'win' if pnl_amount > 0 else 'loss'
                
                # Update Balance in Risk Manager
                capital_released = entry * pos_size
                self.risk_manager.update_metrics(pnl_amount=pnl_amount, last_trade_result=trade_result, capital_released=capital_released)
                
                # Update Profit Optimizer
                if position.get('strategy'):
                    # Retrieve regime from position if stored, else Unknown
                    regime = position.get('regime', 'Unknown')
                    self.profit_optimizer.update(position['strategy'], pnl, regime)
                
                # Sync Balance if in Live Mode to reflect realized PnL
                if self.trading_mode in ['CEX_Proxy', 'CEX_Direct']:
                     self.sync_live_balance()
                    
                # Log Close (Simplified)
                # self.log_trade({...}) # Ideally log the close event too

    def run_analysis(self, df=None):
        """
        Execute the selected strategy's logic
        """
        # Fetch raw data centrally if not provided
        if df is None:
            df = self.data_manager.fetch_ohlcv(self.symbol, self.timeframe, limit=200)
        
        if df.empty:
            return None

        # Feature Store: Compute/Retrieve Features
        # This ensures training and serving use the exact same logic
        df_features = self.feature_store.compute_features(df)
        
        # Update Positions (Check SL/TP)
        current_price = df['close'].iloc[-1]
        self.update_positions(current_price)
        
        # MLOps: Check for Data Drift
        drift_result = self.drift_detector.check_drift(df_features)
        if drift_result['status'] in ['moderate_drift', 'severe_drift']:
            print(f"Warning: {drift_result['status']} detected. Score: {drift_result['score']:.2f}")
            # In a real system, this would trigger a retraining pipeline via Airflow/Celery
        
        # Determine Strategy to Run
        strategy_to_run = self.active_strategy
        
        # Detect Regime for Allocation
        regime_data = self.brain.detect_market_regime(df)
        current_regime = regime_data.get('type', 'Unknown')
        
        allocation_weight = 1.0
        
        if self.active_strategy_name == "Profit Optimization Layer":
            # Profit Optimization Mode: Use Bandit to select best strategy
            weights = self.profit_optimizer.get_allocation_weights(current_regime)
            
            # Select strategy with highest weight
            best_strategy_name = max(weights, key=weights.get)
            strategy_to_run = self.strategies.get(best_strategy_name)
            allocation_weight = weights.get(best_strategy_name, 1.0)
            
            # Optional: Log allocation
            # print(f"Profit Optimizer chose: {best_strategy_name} (Weight: {allocation_weight:.2f})")

        # Delegate to the strategy
        if strategy_to_run:
            signal = strategy_to_run.execute(self.symbol, data=df_features)
            
            # Risk & Compliance: Post-Signal Checks
            if signal and signal.type in ['buy', 'sell']:
                # Apply Allocation Weight to Position Size
                if self.active_strategy_name == "Profit Optimization Layer":
                     # Scale position size by allocation weight
                     # We treat weight as a confidence scalar for the max allowed risk
                     original_size = signal.decision_details.get('position_size', 0)
                     adjusted_size = original_size * allocation_weight
                     signal.decision_details['position_size'] = adjusted_size
                     signal.decision_details['allocation_weight'] = allocation_weight
                     signal.decision_details['optimization_mode'] = True

                # Check Compliance (Kill-Switches, Restricted Assets, Limits)
                compliance_check = self.compliance.check_trade_compliance(
                    self.symbol, 
                    signal.type, 
                    signal.decision_details.get('risk_amount', 0), # Amount/Risk
                    signal.price
                )
                
                if not compliance_check['allowed']:
                    print(f"Compliance Block: {compliance_check['reason']}")
                    # Override signal to HOLD
                    signal.type = 'hold'
                    signal.reason = f"Compliance Blocked: {compliance_check['reason']}"
            
            return signal
        else:
            return None

    def start(self):
        self.is_running = True
        print("Capa-X System Activated...")

    def stop(self):
        self.is_running = False
        print("Capa-X System Deactivated...")

    def run(self):
        """
        Main Trading Loop
        """
        self.start()
        print(f"[*] Trading Bot Started in {self.trading_mode} Mode on {self.symbol}")
        
        while self.is_running:
            try:
                # 1. Sync Balance
                if self.trading_mode != 'Demo':
                    self.sync_live_balance()
                
                # 2. Run Analysis
                signal = self.run_analysis()
                
                # 3. Execute Signal
                if signal and signal.type in ['buy', 'sell']:
                    print(f"[*] Signal Generated: {signal.type.upper()} {self.symbol} @ {signal.price}")
                    
                    # Prepare Execution Packet
                    packet = {
                        "symbol": self.symbol,
                        "bias": signal.type.upper(),
                        "entry": signal.price,
                        "stop_loss": signal.decision_details.get('stop_loss', 0),
                        "take_profit": signal.decision_details.get('take_profit', 0),
                        "position_size": signal.decision_details.get('position_size', 0),
                        "strategy": self.active_strategy_name,
                        "confidence": signal.strength,
                        "decision": "EXECUTE",
                        "market_regime": signal.decision_details.get('regime', 'Unknown')
                    }
                    
                    # Execute Trade
                    result = self.execution.execute_order(packet)
                    
                    if result and result.get('status') == 'FILLED':
                        self.log_trade(packet)
                        print(f"[+] Trade Executed: {packet['bias']} {packet['symbol']}")
                
                # 4. Sleep (Poll Interval)
                time.sleep(60)
                
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                print(f"[!] Error in Trading Loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(10)

