
import time
# Ensure DNS fix is active
import core.dns_fix
from datetime import datetime
import pandas as pd
from core.data import DataManager
from core.models import Signal
from core.risk import AdaptiveRiskManager
from core.security import SecurityManager
from core.alerts import NotificationManager
from config.settings import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME
from config.trading_config import TRADING_CONFIG
from core.storage import StorageManager
from core.auth import AuthManager
from core.web3_wallet import Web3Wallet
from core.fiat.fiat_manager import FiatManager

import json
import os
import importlib

class TradingBot:
    def __init__(self, exchange_id='binance'):
        self.exchange_id = exchange_id
        self.storage = StorageManager() # Local DB
        self.auth_manager = AuthManager() # Secure Key Management
        
        self.data_manager = DataManager(exchange_id)
        self.web3_wallet = Web3Wallet() # Web3 Integration
        
        # Lazy Loading for Heavy Modules
        self._analyzer = None
        self._fundamentals = None
        self._brain = None
        self._quantum = None
        self._portfolio_opt = None
        self._drift_detector = None
        self._ai_trainer = None
        self._risk_manager = None
        self._security = None
        self._arbitrage = None
        self._sentiment = None
        self._execution = None
        self._defi = None
        self._fiat = None
        self._notifications = None
        self._feature_store = None
        self._compliance = None
        self._auto_trader = None
        self._strategies = None
        
        # --- One-time Balance Migration for User Request ---
        if self.storage.get_setting("balance_fix_applied_v2", "false") != "true":
             print("Applying One-time Balance Fix (Add 500 NGN, 0.99 USDT)...")
             try:
                 current_ngn = float(self.storage.get_setting("fiat_balance_ngn", 0.0))
             except:
                 current_ngn = 0.0
            
             try:
                 current_usdt = float(self.storage.get_setting("usdt_balance", 0.0))
             except:
                 current_usdt = 0.0
             
             new_ngn = current_ngn + 500.0
             new_usdt = current_usdt + 0.99
             
             self.storage.save_setting("fiat_balance_ngn", new_ngn)
             # Update virtual credit for sync_live_balance to pick it up
             current_virtual = float(self.storage.get_setting("virtual_usdt_credit_usd", 0.0) or 0.0)
             self.storage.save_setting("virtual_usdt_credit_usd", current_virtual + 0.99)
             
             self.storage.save_setting("balance_fix_applied_v2", "true")
             
             # Also update FiatManager in memory if initialized
             if self._fiat:
                 self.fiat.fiat_balance = new_ngn
             print(f"Balance Fix Applied: NGN {new_ngn}, USDT {new_usdt}")
        
        self.is_running = False
        self.symbol = DEFAULT_SYMBOL
        self.timeframe = DEFAULT_TIMEFRAME
        self.auto_trader_timeframe = None
        self.auto_trader_amount = None
        
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
        
        # Default to Profit Optimizer mode: selects best strategy per regime
        self.active_strategy_name = "Profit Optimization Layer"
        # Ensure active_strategy is set for UI access even in optimizer mode
        # self.active_strategy = self.strategies.get("Smart Trend") # Moved to property

    @property
    def analyzer(self):
        if self._analyzer is None:
            from core.analysis import TechnicalAnalysis
            self._analyzer = TechnicalAnalysis()
        return self._analyzer

    @property
    def fundamentals(self):
        if self._fundamentals is None:
            from core.fundamentals import FundamentalAnalysis
            self._fundamentals = FundamentalAnalysis()
        return self._fundamentals

    @property
    def risk_manager(self):
        if self._risk_manager is None:
            from core.risk import AdaptiveRiskManager
            self._risk_manager = AdaptiveRiskManager(storage_manager=self.storage)
        return self._risk_manager

    @property
    def security(self):
        if self._security is None:
            from core.security import SecurityManager
            self._security = SecurityManager()
        return self._security

    @property
    def arbitrage(self):
        if self._arbitrage is None:
            from core.arbitrage import ArbitrageScanner
            self._arbitrage = ArbitrageScanner()
        return self._arbitrage

    @property
    def sentiment(self):
        if self._sentiment is None:
            from core.sentiment import SentimentEngine
            self._sentiment = SentimentEngine()
        return self._sentiment

    @property
    def execution(self):
        if self._execution is None:
            from core.execution import ExecutionEngine
            self._execution = ExecutionEngine(self)
        return self._execution

    @property
    def defi(self):
        if self._defi is None:
            from core.defi import DeFiManager
            self._defi = DeFiManager()
        return self._defi

    @property
    def fiat(self):
        if self._fiat is None:
            self._fiat = FiatManager(self)
        return self._fiat

    @property
    def notifications(self):
        if self._notifications is None:
            self._notifications = NotificationManager()
        return self._notifications

    @property
    def feature_store(self):
        if self._feature_store is None:
            from core.feature_store import FeatureStore
            self._feature_store = FeatureStore()
        return self._feature_store

    @property
    def compliance(self):
        if self._compliance is None:
            from core.compliance import ComplianceManager
            self._compliance = ComplianceManager(self)
        return self._compliance

    @property
    def auto_trader(self):
        if self._auto_trader is None:
            from core.auto_trader import AutoTrader
            self._auto_trader = AutoTrader(self)
        return self._auto_trader

    @property
    def strategies(self):
        if self._strategies is None:
            from core.strategies import (
                SmartTrendStrategy, GridTradingStrategy, MeanReversionStrategy, 
                FundingArbitrageStrategy, BasisTradeStrategy, LiquiditySweepStrategy, OrderFlowStrategy,
                SwingRangeStrategy, SniperStrategy, WeightedSignalStrategy,
                SpatialArbitrageStrategy,
                EnsembleStrategy
            )
            self._strategies = {
                "Smart Trend": SmartTrendStrategy(self),
                "Sniper Mode": SniperStrategy(self),
                "Grid Trading": GridTradingStrategy(self),
                "Mean Reversion": MeanReversionStrategy(self),
                "Funding Arbitrage": FundingArbitrageStrategy(self),
                "Basis Trade": BasisTradeStrategy(self),
                "Liquidity Sweep": LiquiditySweepStrategy(self),
                "Order Flow": OrderFlowStrategy(self),
                "Swing Range": SwingRangeStrategy(self),
                "Weighted Ensemble": WeightedSignalStrategy(self),
                "Spatial Arbitrage": SpatialArbitrageStrategy(self),
                "Ensemble Brain": EnsembleStrategy(self)
            }
        return self._strategies

    @property
    def active_strategy(self):
        return self.strategies.get("Smart Trend")

    @active_strategy.setter
    def active_strategy(self, value):
        # We don't actually store the active strategy instance on self anymore, 
        # but we might need to support legacy code that sets it.
        # For now, pass. The logic seems to rely on active_strategy_name
        pass

    def initialize_credentials(self, username):
        """
        Load encrypted credentials for the user and initialize connections.
        """
        print(f"Initializing Credentials for {username}...")
        
        # 1. Load CEX Credentials
        # We try to find keys for the current exchange_id
        keys = self.auth_manager.get_api_keys(username, self.exchange_id)
        if keys and 'api_key' in keys and 'api_secret' in keys:
            api_key = keys['api_key']
            api_secret = keys['api_secret']
            print(f"✅ Found API Keys for {self.exchange_id}. Updating DataManager...")
            self.data_manager.update_credentials(api_key, api_secret)
        else:
            print(f"ℹ️ No API Keys found for {self.exchange_id} (User: {username})")

        # 2. Load Web3 Wallet (First available)
        wallets = self.auth_manager.get_user_wallets(username)
        if wallets:
            # Try to connect the first one found
            first_wallet = wallets[0]
            address = first_wallet['address']
            chain_id = first_wallet.get('chain_id', '1')
            
            # Get Private Key
            pk = self.auth_manager.get_private_key(username, address)
            if pk:
                print(f"✅ Found Web3 Wallet {address}. Connecting...")
                success = self.web3_wallet.connect(pk, chain_id=chain_id)
                if success:
                    print(f"✅ Web3 Wallet Connected: {address} ({chain_id})")
                else:
                    print(f"❌ Failed to connect Web3 Wallet {address}")
        else:
            print(f"ℹ️ No Web3 Wallets found (User: {username})")

        # 3. Initialize Fiat Adapter
        if hasattr(self, 'fiat'):
             self.fiat.initialize_adapter(username)

    def withdraw_crypto(self, asset: str, amount: float, address: str, network: str = None):
        """
        Initiate Crypto Withdrawal (CEX or Web3).
        Prioritizes CEX if mode is CEX_Direct/Proxy.
        """
        print(f"💸 Initiating Withdrawal: {amount} {asset} -> {address}")
        
        # 1. CEX Withdrawal
        if self.trading_mode in ['CEX_Direct', 'CEX_Proxy']:
            return self.data_manager.withdraw_crypto(asset, amount, address, network=network)
            
        # 2. Web3 Withdrawal
        elif self.trading_mode == 'DEX' or (hasattr(self, 'web3_wallet') and self.web3_wallet.is_connected()):
            # Detect if Native or Token
            if asset in ['ETH', 'BNB', 'MATIC', 'AVAX', 'CRO', 'FTM', 'GLMR', 'MOVR', 'ONE', 'KLAY']:
                return self.web3_wallet.send_native(address, amount)
            else:
                # Need Token Address - Dynamic Lookup based on Chain ID
                chain_id = str(self.web3_wallet.chain_id)
                
                # Multi-Chain Token Map
                # Structure: { 'ASSET': { 'chain_id': 'address', ... } }
                token_map = {
                    'USDT': {
                        '1': '0xdAC17F958D2ee523a2206206994597C13D831ec7', # Ethereum
                        '56': '0x55d398326f99059fF775485246999027B3197955', # BSC
                        '137': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F', # Polygon
                        '42161': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9', # Arbitrum
                        '10': '0x94b008aA00579c1307B0EF2c499aD98a8ce98e48', # Optimism
                        '43114': '0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7', # Avalanche
                    },
                    'USDC': {
                        '1': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', # Ethereum
                        '56': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d', # BSC
                        '137': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174', # Polygon
                        '42161': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8', # Arbitrum
                        '10': '0x7F5c764cBc14f9669B88837ca1490cCa17c31607', # Optimism
                        '43114': '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E', # Avalanche
                    }
                }
                
                asset_tokens = token_map.get(asset, {})
                token_addr = asset_tokens.get(chain_id)
                
                # Fallback: Check if asset is a raw address (simple heuristic)
                if not token_addr and asset.startswith('0x') and len(asset) == 42:
                    token_addr = asset
                
                if not token_addr:
                    return {"status": "error", "message": f"Token Address for {asset} on Chain {chain_id} not found."}
                
                return self.web3_wallet.send_token(token_addr, address, amount)
        
        else:
            return {"status": "error", "message": "No active withdrawal method found (CEX or Web3 Disconnected)"}

    def sync_live_balance(self):
        """
        Fetch real balance from connected Exchange/Wallet and update Risk Manager.
        """
        try:
            balance = 0.0
            
            # 1. CEX Balance
            if self.trading_mode in ['CEX_Proxy', 'CEX_Direct']:
                if self.data_manager.exchange:
                    # Fetch free balance of the quote currency (e.g., USDT)
                    # We assume the bot trades USDT pairs.
                    # This fetches all balances, might be heavy.
                    # Let's try fetch_balance()
                    try:
                        balances = self.data_manager.exchange.fetch_balance()
                        # Assume USDT or USD
                        quote = 'USDT'
                        if quote in balances:
                            balance = float(balances[quote]['free'])
                        elif 'USD' in balances:
                             balance = float(balances['USD']['free'])
                    except Exception as e:
                        print(f"CEX Balance Fetch Error: {e}")
                        
            # 2. DEX Balance
            elif self.trading_mode == 'DEX':
                if self.web3_wallet.connected:
                    balance = self.web3_wallet.get_balance()
            
            # Update Risk Manager
            if balance > 0:
                print(f"Syncing Live Balance: {balance} ({self.trading_mode})")
                self.risk_manager.update_live_balance(balance)
                
        except Exception as e:
            print(f"Failed to sync live balance: {e}")

    @property
    def open_positions(self):
        """Helper to get positions for current mode"""
        key = self.trading_mode
        # Fallback if mapped incorrectly
        if key == 'Live': key = 'CEX_Direct'
            
        if key not in self.positions:
            self.positions[key] = []
        return self.positions[key]

    @open_positions.setter
    def open_positions(self, value):
        key = self.trading_mode
        if key == 'Live': key = 'CEX_Direct'
        self.positions[key] = value
        self.active_strategy = self.strategies.get(self.active_strategy_name)
        
        # Initialize Profit Optimizer (Contextual Multi-Armed Bandit)
        self.profit_optimizer = ProfitOptimizer(list(self.strategies.keys()))
        
    @property
    def brain(self):
        if self._brain is None:
            # Use safe import to avoid circular dependency issues
            import core.brain
            import importlib
            
            # Robust check for attribute existence to handle potential circular import artifacts
            if not hasattr(core.brain, 'CapacityBayBrain'):
                print("⚠️ core.brain.CapacityBayBrain missing! Attempting reload...")
                try:
                    importlib.reload(core.brain)
                except Exception as e:
                    print(f"❌ Failed to reload core.brain: {e}")
            
            # Double check
            if hasattr(core.brain, 'CapacityBayBrain'):
                self._brain = core.brain.CapacityBayBrain()
            else:
                # Fallback or fatal error
                raise ImportError("Could not load CapacityBayBrain from core.brain after reload")
                
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
                try:
                    self.data_manager.set_proxy_mode(use_proxy=False)
                except Exception as e:
                    print(f"[WARN] Failed to set proxy mode (or load markets) for DEX mode: {e}")
                    print("[INFO] Continuing in DEX mode (CEX DataManager might be offline)")
                    self.data_manager.offline_mode = True
                    self.data_manager.connection_status = "Error (Ignored for DEX)"
            
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
        self.latest_gas_fees = {} # Reset gas fees
        
        try:
            # 0. WEB3 / DEX MODE (Priority if Web3 Wallet Connected)
            if hasattr(self, 'web3_wallet') and self.web3_wallet.connected:
                print(f"DEBUG: Syncing Web3 Wallet Balance ({self.web3_wallet.chain_id})")
                native_bal = self.web3_wallet.get_balance()
                
                # Fetch Live Gas Fees
                try:
                    gas_info = self.web3_wallet.get_gas_price()
                    if gas_info:
                        self.latest_gas_fees = gas_info
                        print(f"⛽ Live Gas Monitoring ({self.web3_wallet.get_network_name()}): {gas_info}")
                except Exception as e:
                    print(f"Error fetching gas fees: {e}")

                # Get Chain Symbol
                # Default mapping for known chain IDs to symbols
                symbol_map = {
                    'bitcoin': 'BTC',
                    'litecoin': 'LTC',
                    'dogecoin': 'DOGE',
                    'tron': 'TRX',
                    'solana': 'SOL',
                    'cosmos': 'ATOM',
                    'ton': 'TON',
                    '1': 'ETH',
                    'ethereum': 'ETH',
                    '56': 'BNB',
                    '137': 'MATIC',
                    '43114': 'AVAX',
                    '250': 'FTM',
                    '10': 'OP',
                    '42161': 'ETH'
                }
                
                chain_sym = symbol_map.get(str(self.web3_wallet.chain_id), 'ETH')
                
                # If chain ID is numeric and not in map, try to get from CHAINS config
                if chain_sym == 'ETH' and self.web3_wallet.chain_id in self.web3_wallet.CHAINS:
                     chain_sym = self.web3_wallet.CHAINS[self.web3_wallet.chain_id]['symbol']
                
                # Update Risk Manager
                # We need USD price of Native Token
                pair_symbol = f"{chain_sym}/USDT"
                price = 0.0
                try:
                    price = self.data_manager.get_current_price(pair_symbol)
                    if not price or price == 0:
                        # No hardcoded fallbacks - return 0 if price unavailable
                        price = 0.0
                except:
                    # No price available - do not use hardcoded fake prices
                    print(f"[WARN] Could not fetch price for {pair_symbol}. USD balance will be 0.")
                    price = 0.0
                
                usd_bal = native_bal * price
                self.risk_manager.update_live_balance(usd_bal)
                
                # Add to Wallet Balances for UI
                self.wallet_balances.append({
                    'asset': chain_sym,
                    'total': native_bal,
                    'free': native_bal,
                    'locked': 0.0,
                    'value_usd': usd_bal
                })
                
                # If we have Jettons/Tokens in Web3Wallet (TODO: Implement token scan in Web3Wallet)
                # For now, just Native.
                
                # If ONLY Web3 is connected (not CEX), return here.
                # If CEX is ALSO connected, we continue to fetch CEX balance and append.
                if not (self.trading_mode in ['CEX_Proxy', 'CEX_Direct']):
                    return

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
                        
                        # ADD VIRTUAL CREDIT (DEX)
                        if hasattr(self, 'storage'):
                            try:
                                credit = float(self.storage.get_setting("virtual_usdt_credit_usd", 0.0) or 0.0)
                                if credit > 0:
                                     usd_bal += credit
                                     # print(f"Applying Virtual Credit (DEX): ${credit}")
                            except:
                                pass
                        
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
                
                # Debug Log File - DISABLED for Performance
                # with open("debug_wallet_log.txt", "w", encoding='utf-8') as f:
                #    f.write(f"[{datetime.now()}] Starting Sync\n")
                #    if self.data_manager.offline_mode:
                #        f.write("WARNING: DataManager is in Offline Mode! Balance data is fake/mock.\n")

                # 1. Fetch Default Balance (Unified/Spot)
                try:
                    balance = self.data_manager.get_balance()
                    
                    # STRICT CHECK: Ensure 'total' exists (Critical for correct parsing)
                    if balance and 'total' not in balance:
                         print("[WARN] Spot balance missing 'total' field. Retrying once...")
                         balance = self.data_manager.get_balance(force_refresh=True)
                         
                    # with open("debug_wallet_log.txt", "a", encoding='utf-8') as f:
                    #    f.write(f"Spot Balance Keys: {list(balance.keys())}\n")
                    #    # Log raw structure for debugging
                    #    f.write(f"Raw Balance Type: {type(balance)}\n")
                    #    if balance:
                    #        f.write(f"Raw Balance Sample: {str(balance)[:500]}...\n")
                        
                    #    # DEBUG: Inspect specific assets requested by user
                    #    target_assets = ['HMSTR', 'LDPEPE', 'PIXEL', 'SOL', 'USDT', 'BTC']
                    #    f.write("\n--- Target Asset Inspection ---\n")
                    #    for asset in target_assets:
                    #        if asset in balance:
                    #            f.write(f"Asset: {asset}\n")
                    #            f.write(f"  Value: {balance[asset]}\n")
                    #            f.write(f"  Type: {type(balance[asset])}\n")
                    #        else:
                    #            f.write(f"Asset: {asset} NOT FOUND in keys.\n")
                    #    f.write("-----------------------------\n")

                    #    if 'total' in balance:
                    #        f.write(f"Spot Total Dict found. Items: {len(balance['total'])}\n")
                    #    else:
                    #        f.write("Spot 'total' Dict NOT found.\n")
                            
                except Exception as e:
                    error_str = str(e)
                    # with open("debug_wallet_log.txt", "a", encoding='utf-8') as f:
                    #    f.write(f"ERROR Fetching Spot: {error_str}\n")
                    
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
                                # Calculate USD Value
                                usd_val = 0.0
                                if float(amount) > 0:
                                    try:
                                        if currency in ['USDT', 'USDC', 'BUSD', 'DAI']:
                                            usd_val = float(amount)
                                        else:
                                            pair = f"{currency}/USDT"
                                            price = self.data_manager.get_current_price(pair)
                                            if price:
                                                usd_val = float(amount) * price
                                    except:
                                        pass

                                self.wallet_balances.append({
                                    'asset': currency,
                                    'free': float(funding_balance.get('free', {}).get(currency, 0)),
                                    'locked': float(funding_balance.get('used', {}).get(currency, 0)),
                                    'total': float(amount),
                                    'value_usd': round(usd_val, 2),
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

                                # Calculate USD Value
                                usd_val = 0.0
                                if float(amount) > 0:
                                    try:
                                        # Handle USDT/USDC directly
                                        if currency in ['USDT', 'USDC', 'BUSD', 'DAI']:
                                            usd_val = float(amount)
                                        else:
                                            # Try fetching price
                                            pair = f"{currency}/USDT"
                                            price = self.data_manager.get_current_price(pair)
                                            if price:
                                                usd_val = float(amount) * price
                                    except:
                                        pass

                                self.wallet_balances.append({
                                    'asset': display_asset,
                                    'total': float(amount),
                                    'free': free_val,
                                    'locked': locked_val,
                                    'value_usd': round(usd_val, 2)
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
                                
                                # Calculate USD Value
                                usd_val = 0.0
                                if total > 0:
                                    try:
                                        if currency in ['USDT', 'USDC', 'BUSD', 'DAI']:
                                            usd_val = total
                                        else:
                                            pair = f"{currency}/USDT"
                                            price = self.data_manager.get_current_price(pair)
                                            if price:
                                                usd_val = total * price
                                    except:
                                        pass

                                self.wallet_balances.append({
                                    'asset': display_asset,
                                    'total': total,
                                    'free': free,
                                    'locked': used,
                                    'value_usd': round(usd_val, 2)
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
                            
                            # Calculate USD Value
                            usd_val = 0.0
                            if total > 0:
                                try:
                                    if currency in ['USDT', 'USDC', 'BUSD', 'DAI']:
                                        usd_val = total
                                    else:
                                        pair = f"{currency}/USDT"
                                        price = self.data_manager.get_current_price(pair)
                                        if price:
                                            usd_val = total * price
                                except:
                                    pass

                            self.wallet_balances.append({
                                'asset': display_asset,
                                'total': total,
                                'free': float(data.get('free', 0.0)),
                                'locked': float(data.get('used', 0.0)),
                                'value_usd': round(usd_val, 2)
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
                                        # Calculate USD Value
                                        usd_val = 0.0
                                        asset_sym = c.get('coin')
                                        try:
                                            if asset_sym in ['USDT', 'USDC', 'BUSD', 'DAI']:
                                                usd_val = w_bal
                                            else:
                                                pair = f"{asset_sym}/USDT"
                                                price = self.data_manager.get_current_price(pair)
                                                if price:
                                                    usd_val = w_bal * price
                                        except:
                                            pass

                                        self.wallet_balances.append({
                                            'asset': asset_sym,
                                            'total': w_bal,
                                            'free': float(c.get('availableToWithdraw', w_bal)),
                                            'locked': float(c.get('locked', 0)),
                                            'value_usd': round(usd_val, 2)
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

                # Add Fiat (NGN) Balance converted to USD
                if hasattr(self, 'fiat') and self.fiat.fiat_balance > 0:
                    ngn_bal = self.fiat.fiat_balance
                    # Rate: NGN/USD ~ 1/1650 = 0.0006
                    # We try to get USDT/NGN price from DataManager if possible
                    rate_usdt_ngn = 1650.0 
                    try:
                        # Try fetch
                        t = self.data_manager.get_current_price("USDT/NGN")
                        if t and t > 0: rate_usdt_ngn = t
                    except:
                        pass
                    
                    usd_val_fiat = ngn_bal / rate_usdt_ngn
                    
                    # Add to Total Equity (since user wants to see it in Total Balance)
                    usdt_bal += usd_val_fiat
                    
                    self.wallet_balances.append({
                        'asset': 'NGN (Fiat)',
                        'total': ngn_bal,
                        'free': ngn_bal,
                        'locked': 0.0,
                        'value_usd': round(usd_val_fiat, 2)
                    })

                if hasattr(self, 'storage'):
                    try:
                        credit = float(self.storage.get_setting("virtual_usdt_credit_usd", 0.0) or 0.0)
                        usdt_bal = usdt_bal + credit
                    except Exception:
                        pass
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
        # Alias mapping
        if strategy_name == "Meta-Allocator":
            strategy_name = "Profit Optimization Layer"
            
        if strategy_name == "Profit Optimization Layer" or strategy_name in self.strategies:
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
            "amount": clean_packet.get('position_size', 0),
            "stop_loss": clean_packet.get('stop_loss', 0),
            "take_profit": clean_packet.get('take_profit', 0),
            "risk_percent": clean_packet.get('risk_percent', 0),
            "confidence": clean_packet.get('confidence', 0),
            "regime": clean_packet.get('market_regime', 'Unknown'),
            "execution_score": clean_packet.get('execution_score', 0),
            "components": clean_packet.get('components', {}),
            "explanation": clean_packet.get('explanation', ""),
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
            else:
                # Trailing Stop & Breakeven logic
                try:
                    df = self.data_manager.fetch_ohlcv(symbol, self.timeframe, limit=50)
                    if df is not None and not df.empty:
                        atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
                        if pd.isna(atr) or atr <= 0:
                            atr = abs(current_price) * 0.01
                        # 1R distance based on initial stop distance or ATR fallback
                        r_dist = abs(entry - sl) if sl and sl > 0 else atr * 1.5

                        if bias == 'BUY':
                            # Move to breakeven after 1R
                            if current_price >= entry + r_dist and (sl == 0 or sl < entry):
                                position['stop_loss'] = entry
                            # Trail by ~1.2 ATR behind price
                            trail_sl = current_price - (atr * 1.2)
                            if trail_sl > position.get('stop_loss', 0):
                                position['stop_loss'] = trail_sl
                            hh = df['high'].rolling(22).max().iloc[-1]
                            chand = hh - (atr * 3.0)
                            if chand > position.get('stop_loss', 0):
                                position['stop_loss'] = chand
                        elif bias == 'SELL':
                            if current_price <= entry - r_dist and (sl == 0 or sl > entry):
                                position['stop_loss'] = entry
                            trail_sl = current_price + (atr * 1.2)
                            # For short, a smaller stop_loss value is tighter
                            if position.get('stop_loss', 0) == 0 or trail_sl < position['stop_loss']:
                                position['stop_loss'] = trail_sl
                            ll = df['low'].rolling(22).min().iloc[-1]
                            chand_s = ll + (atr * 3.0)
                            if position.get('stop_loss', 0) == 0 or chand_s < position['stop_loss']:
                                position['stop_loss'] = chand_s

                        # Partial take-profit at 1.5R, once per position
                        try:
                            took = position.get('partial_taken', False)
                            if not took:
                                target_move = 1.5 * r_dist
                                moved = (current_price - entry) if bias == 'BUY' else (entry - current_price)
                                if moved >= target_move:
                                    half_size = position['position_size'] * 0.5
                                    if half_size > 0:
                                        # Realize half the position
                                        realized_pnl = moved * half_size
                                        capital_released = entry * half_size
                                        trade_result = 'win' if realized_pnl > 0 else 'loss'
                                        self.risk_manager.update_metrics(pnl_amount=realized_pnl, last_trade_result=trade_result, capital_released=capital_released)
                                        # Reduce size and set flag
                                        position['position_size'] = position['position_size'] - half_size
                                        position['partial_taken'] = True
                                        # Move stop to breakeven for remaining
                                        position['stop_loss'] = entry
                                        self.save_positions()
                                        print(f"[TP1] Partial profit taken (50%). Remaining size: {position['position_size']:.6f}")
                            took2 = position.get('partial2_taken', False)
                            if position.get('partial_taken', False) and not took2:
                                target_move2 = 2.5 * r_dist
                                moved = (current_price - entry) if bias == 'BUY' else (entry - current_price)
                                if moved >= target_move2:
                                    half_rem = position['position_size'] * 0.5
                                    if half_rem > 0:
                                        realized_pnl2 = moved * half_rem
                                        capital_released2 = entry * half_rem
                                        trade_result2 = 'win' if realized_pnl2 > 0 else 'loss'
                                        self.risk_manager.update_metrics(pnl_amount=realized_pnl2, last_trade_result=trade_result2, capital_released=capital_released2)
                                        position['position_size'] = position['position_size'] - half_rem
                                        position['partial2_taken'] = True
                                        position['stop_loss'] = entry
                                        self.save_positions()
                                        print(f"[TP2] Second partial taken (50% of remaining). Remaining size: {position['position_size']:.6f}")
                        except Exception as e:
                            print(f"Partial TP failed: {e}")

                        self.save_positions()
                except Exception as e:
                    print(f"Trailing stop update failed: {e}")

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
        # Optimization: Pass df_features to avoid recalculating indicators in Brain
        regime_data = self.brain.detect_market_regime(df_features)
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
        print("CapacityBay System Activated...")

    def stop(self):
        self.is_running = False
        print("CapacityBay System Deactivated...")

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

                    # Cooldown: avoid overtrading unless very high confidence
                    from datetime import datetime, timedelta
                    # Regime-aware cooldown
                    regime_for_cooldown = getattr(signal, 'regime', 'Unknown')
                    min_cooldown = timedelta(minutes=20) if regime_for_cooldown in ['Volatile', 'Extreme Volatility'] else timedelta(minutes=15)
                    if self.last_trade_time and (datetime.now() - self.last_trade_time) < min_cooldown:
                        if signal.confidence < 0.85:
                            print("[!] Cooldown active: skipping low-confidence signal to reduce overtrading.")
                            time.sleep(60)
                            continue
                    
                    # Global kill-switch check
                    if self.risk_manager.check_kill_switch():
                        print("[!] Kill Switch Active: Trading paused due to drawdown protection.")
                        time.sleep(60)
                        continue

                    # Minimum confidence gate (from config)
                    base_conf = TRADING_CONFIG['allocation'].get('min_confidence_threshold', 0.75)
                    dd_adj = self.risk_manager.max_drawdown * 0.5
                    streak_adj = 0.05 if self.risk_manager.loss_streak > 2 else 0.0
                    min_conf = min(0.9, max(base_conf, base_conf + dd_adj + streak_adj))
                    if signal.confidence < min_conf:
                        print(f"[!] Confidence {signal.confidence:.2f} < threshold {min_conf:.2f}: skipping.")
                        time.sleep(10)
                        continue

                    # Prepare Execution Packet
                    packet = {
                        "symbol": self.symbol,
                        "bias": signal.type.upper(),
                        "entry": signal.price,
                        "stop_loss": signal.decision_details.get('stop_loss', 0),
                        "take_profit": signal.decision_details.get('take_profit', 0),
                        "position_size": signal.decision_details.get('position_size', 0),
                        "strategy": self.active_strategy_name,
                        "confidence": signal.confidence,
                        "decision": "EXECUTE",
                        "market_regime": signal.decision_details.get('regime', 'Unknown')
                    }

                    # Portfolio exposure limits
                    allowed, reason = self.risk_manager.check_portfolio_limits(self.symbol, packet['position_size'])
                    if not allowed:
                        print(f"[!] Portfolio Limit Blocked: {reason}")
                        time.sleep(10)
                        continue

                    # Sanity: require non-zero size and valid SL/TP
                    if packet['position_size'] <= 0 or packet['stop_loss'] == 0 or packet['take_profit'] == 0:
                        print("[!] Invalid sizing or levels: skipping execution.")
                        time.sleep(10)
                        continue

                    # Pre-trade explanation for auditability
                    packet["explanation"] = (
                        f"Strategy: {packet['strategy']} | Regime: {packet['market_regime']} | "
                        f"Entry: {packet['entry']:.2f} | SL: {packet['stop_loss']:.2f} | TP: {packet['take_profit']:.2f} | "
                        f"Size: {packet['position_size']:.6f} | Confidence: {packet['confidence']:.2f}"
                    )
                    print(packet["explanation"]) 
                    
                    # Execute Trade
                    result = self.execution.execute_order(packet)
                    
                    if result and result.get('status') == 'FILLED':
                        self.log_trade(packet)
                        self.last_trade_time = datetime.now()
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
