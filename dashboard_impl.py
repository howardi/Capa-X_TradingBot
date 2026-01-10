import streamlit as st
from core.ui_components import render_top_nav, render_sidebar_menu
try:
    from tenacity import RetryError
except ImportError:
    class RetryError(Exception): pass

# Apply DNS Fix immediately
try:
    from core.dns_fix import apply_dns_fix
    apply_dns_fix()
except Exception as e:
    print(f"DNS Fix Failed: {e}")

import time
import sys
import os
import importlib
import base64
import io
import qrcode
from PIL import Image
from io import BytesIO
import core.styles as styles

# Defensive Import Wrapper
def get_style_func(name, fallback_func=None):
    if hasattr(styles, name):
        return getattr(styles, name)
    else:
        if fallback_func:
            return fallback_func
        else:
            def noop(*args, **kwargs):
                pass
            return noop

# Define Fallbacks
def fallback_metric(label, value, delta=None, color=None):
    st.metric(label, value, delta)

def generate_qr_image(text: str):
    try:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    except Exception:
        return None

def fallback_header(text, level=1):
    if level == 1: st.title(text)
    elif level == 2: st.header(text)
    else: st.subheader(text)

def fallback_container(title, content):
    st.markdown(f"**{title}**")
    st.write(content)

# Map Functions
apply_custom_styles = get_style_func('apply_custom_styles')
metric_card = get_style_func('metric_card', fallback_metric)
neon_header = get_style_func('neon_header', fallback_header)
card_container = get_style_func('card_container', fallback_container)
cyberpunk_logo = get_style_func('cyberpunk_logo')

# core.auth and others are needed for types/constants sometimes, but we'll check usage.
import core.auth
import core.data
import core.risk
# import core.brain       # Optimization: defer
# import core.strategies  # Optimization: defer
# import core.bot         # Optimization: defer
import core.ui_components
from core.auth import AuthManager, UserManager, TOTP, SessionManager
from core.ton_wallet import TonConnectManager
from core.web3_wallet import Web3Wallet
# from core.defi import DeFiManager # Optimization: defer
import pandas as pd
from config.settings import APP_NAME, VERSION, DEFAULT_SYMBOL

# Determine Page Icon (Logo or Emoji)
logo_path = os.path.join("assets", "logo.png")
page_icon = logo_path if os.path.exists(logo_path) else "🦅"

# st.set_page_config(
#     page_title=APP_NAME, 
#     layout="wide",
#     page_icon=page_icon,
#     initial_sidebar_state="expanded",
#     menu_items={
#         'About': f"# {APP_NAME} v{VERSION}\nPowered by Capa-X Quantum AI"
#     }
# )

# Apply Cyberpunk / Professional Styles
apply_custom_styles()

# Initialize Auth
if 'auth_manager' not in st.session_state or not hasattr(st.session_state.auth_manager, 'get_api_keys'):
    st.session_state.auth_manager = AuthManager()

if 'session_manager' not in st.session_state:
    st.session_state.session_manager = SessionManager()

if 'web3_wallet' not in st.session_state:
    st.session_state.web3_wallet = Web3Wallet()

# Auth State Initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_role = None

if 'login_stage' not in st.session_state:
    st.session_state.login_stage = 'credentials'

# --- Session Management & Persistence ---
if st.session_state.get('logged_in'):
    last_active = st.session_state.get('last_active', time.time())
    idle_duration = time.time() - last_active
    
    if idle_duration > 7200:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.query_params["logout"] = "timeout"
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
        st.markdown("<script>localStorage.removeItem('capacitybay_session');</script>", unsafe_allow_html=True)
        st.rerun()
    elif idle_duration > 6900:
        mins_left = int((7200 - idle_duration) / 60)
        st.toast(f"⚠️ Session expiring in {mins_left} minutes due to inactivity.", icon="⏳")
    
    st.session_state.last_active = time.time()

query_params = st.query_params
session_id = query_params.get("session_id", None)
logout_reason = query_params.get("logout", None)

if logout_reason == "timeout":
    st.error("Session expired due to inactivity.")
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        st.session_state.logged_in = False
        st.session_state.username = None
    st.markdown("<script>localStorage.removeItem('capacitybay_session');</script>", unsafe_allow_html=True)

if not st.session_state.logged_in and session_id:
    username = st.session_state.session_manager.validate_session(session_id)
    if username:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.session_token = session_id
        st.session_state.user_manager = UserManager(username)
        st.session_state.user_role = st.session_state.auth_manager.users.get(username, {}).get('role', 'demo')
        st.session_state.last_active = time.time()
        st.success(f"Welcome back, {username}!")
    else:
        st.error("Session expired or invalid.")
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
        st.markdown("<script>localStorage.removeItem('capacitybay_session');</script>", unsafe_allow_html=True)

if not st.session_state.logged_in and not session_id and not logout_reason:
    st.markdown("<script>const token = localStorage.getItem('capacitybay_session');if (token) {window.location.search = '?session_id=' + token;}</script>", unsafe_allow_html=True)

if 'sound_queue' not in st.session_state:
    st.session_state.sound_queue = []

# --- Helper Functions ---
def get_bot(exchange_id):
    # Optimization: Lazy import to speed up startup
    from core.bot import TradingBot
    
    session_key = f"bot_{exchange_id}_{SESSION_VERSION_KEY}"
    if session_key not in st.session_state:
        st.session_state[session_key] = TradingBot(exchange_id)
        cache_key = f"wallet_cache_{exchange_id}_v10"
        if cache_key in st.session_state:
            st.session_state[session_key].wallet_balances = st.session_state[cache_key]
        
    bot = st.session_state[session_key]
    
    if not hasattr(bot, 'wallet_balances'):
        bot.wallet_balances = []

    # Attach Web3 Wallet if available
    if 'web3_wallet' in st.session_state:
        bot.web3_wallet = st.session_state.web3_wallet

    try:
        if st.session_state.get('logged_in') and 'auth_manager' in st.session_state:
            username = st.session_state.get('username')
            if username:
                # Use the centralized credential loader
                # OPTIMIZATION: Check if already initialized to avoid file reads
                if not getattr(bot, '_credentials_initialized', False):
                    bot.initialize_credentials(username)
                    bot._credentials_initialized = True
                
                # Update Session State flags based on bot state
                if bot.data_manager.exchange and bot.data_manager.exchange.apiKey:
                     st.session_state[f"{exchange_id}_connected"] = True
                     st.session_state.exchange_connected = True
                     # If keys exist, default to CEX_Direct unless explicitly set otherwise
                     if bot.trading_mode == 'Demo':
                         bot.trading_mode = 'CEX_Direct'
                
    except Exception as e:
        print(f"Failed to auto-inject credentials: {e}")
        
    return bot

@st.cache_data(ttl=3600)
def get_cached_banks(_fiat_mgr):
    """Cache bank list for 1 hour"""
    return _fiat_mgr.get_banks()

@st.cache_data(ttl=600)
def get_cached_fundamentals(symbol, _bot):
    return _bot.fundamentals.get_asset_details(symbol)

@st.cache_data(ttl=600)
def get_cached_sentiment(_bot):
    return _bot.fundamentals.get_market_sentiment()

@st.cache_data(ttl=10)
def get_cached_ohlcv(_bot, symbol, timeframe, limit=200):
    return _bot.data_manager.fetch_ohlcv(symbol, timeframe, limit=limit)

@st.cache_data(ttl=60)
def get_cached_analysis(_bot, df):
    if df.empty:
        return None
    return _bot.run_analysis(df)

@st.cache_data(ttl=60)
def get_cached_prediction(_bot, df):
    return _bot.brain.predict_next_move(df)

@st.cache_data(ttl=15)
def get_cached_ticker(_bot, symbol):
    return _bot.data_manager.fetch_ticker(symbol)

@st.cache_data(ttl=15)
def get_cached_price(_bot, symbol):
    t = get_cached_ticker(_bot, symbol)
    return t.get('last', 0.0) if t else 0.0

def check_alerts(bot_instance):
    if 'alerts' not in st.session_state or not st.session_state.alerts:
        return

    triggered_alerts = []
    active_alerts = [a for a in st.session_state.alerts if a['active']]
    if not active_alerts:
        return
        
    symbols = set(a['symbol'] for a in active_alerts)
    prices = {}
    
    for sym in symbols:
        try:
            ticker = get_cached_ticker(bot_instance, sym)
            prices[sym] = ticker.get('last')
        except:
            prices[sym] = None
            
    for i, alert in enumerate(st.session_state.alerts):
        if not alert['active']:
            continue
            
        current_price = prices.get(alert['symbol'])
        
        if current_price:
            triggered = False
            if alert['condition'] == 'Above' and current_price > alert['value']:
                triggered = True
            elif alert['condition'] == 'Below' and current_price < alert['value']:
                triggered = True
                
            if triggered:
                triggered_alerts.append((i, alert, current_price))
    
    for i, alert, price in triggered_alerts:
        st.session_state.sound_queue.append("alert")
        st.toast(f"🔔 ALERT: {alert['symbol']} is {alert['condition']} {alert['value']} (Current: {price})", icon="🔔")
        st.session_state.alerts[i]['active'] = False

# --- Authentication Logic ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div class=\"login-header\" style='text-align: center; margin-bottom: 30px;'><h1 style='color: #00f2ff; margin-bottom: 10px; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); font-family: \"JetBrains Mono\", monospace;'>Capa-X</h1><h3 style='color: #e0e6ed; font-size: 1.1rem; margin-bottom: 5px; font-weight: 400;'>The Intelligent Trading Engine</h3><p style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 15px; font-style: italic;'>The Future of Trading, Today</p><p style='color: #64748b; font-size: 0.8rem; margin-top: 5px;'>powered by <span style='color: #00994d; font-weight: 700;'>CapacityBay</span></p></div>", unsafe_allow_html=True)

        
        with st.container():
            st.markdown('<style>.block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; } [data-testid="stForm"] { background-color: rgba(20, 25, 35, 0.8); border: 1px solid rgba(0, 242, 255, 0.2); border-radius: 15px; padding: 1.5rem; box-shadow: 0 0 20px rgba(0, 0, 0, 0.5); margin-top: 0px; } @media (max-width: 768px) { div[data-testid="column"] { width: 100% !important; flex: 1 1 auto !important; min-width: 100% !important; } .block-container { padding-top: 0rem !important; } [data-testid="stForm"] { padding: 1.5rem; margin-top: 0rem; } .login-header h1 { font-size: 2rem !important; } .login-header { margin-bottom: 15px !important; } } .stTextInput input { background-color: rgba(10, 14, 23, 0.9) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; color: white !important; } .stTextInput input:focus { border-color: #00f2ff !important; box-shadow: 0 0 10px rgba(0, 242, 255, 0.2) !important; } .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; } .stTabs [data-baseweb="tab"] { background-color: rgba(255, 255, 255, 0.05); border-radius: 5px; color: #94a3b8; padding: 8px 16px; border: none; } .stTabs [aria-selected="true"] { background-color: rgba(0, 242, 255, 0.1) !important; color: #00f2ff !important; border: 1px solid rgba(0, 242, 255, 0.3) !important; }</style>', unsafe_allow_html=True)
            
            if st.session_state.login_stage == 'credentials':
                tab_login, tab_reg = st.tabs(["ACCESS TERMINAL", "NEW OPERATOR"])
                
                with tab_login:
                    with st.form("login_form"):
                        username = st.text_input("Username", key="login_user")
                        password = st.text_input("Password", type="password", key="login_pass")
                        remember_me = st.checkbox("Remember Me", value=True)
                        submitted = st.form_submit_button("Login", type="primary")
                    
                    if submitted:
                        if not username or not password:
                            st.warning("Please enter both username and password.")
                        else:
                            with st.spinner("Authenticating..."):
                                time.sleep(0.5)
                                success, result = st.session_state.auth_manager.login_user(username, password)
                                if success:
                                    if result.get('2fa_enabled', False):
                                        st.session_state.login_stage = '2fa'
                                        st.session_state.temp_user_data = result
                                        st.session_state.remember_me = remember_me
                                        st.rerun()
                                    else:
                                        st.session_state.logged_in = True
                                        st.session_state.username = username
                                        st.session_state.user_role = result['role']
                                        st.session_state.user_manager = UserManager(username)
                                        st.session_state.last_active = time.time()
                                        token = st.session_state.session_manager.create_session(username, remember_me)
                                        st.session_state.session_token = token
                                        st.query_params["session_id"] = token
                                        st.markdown(f"<script>localStorage.setItem('capacitybay_session', '{token}');</script>", unsafe_allow_html=True)
                                        st.session_state.sound_queue.append("connect")
                                        st.success("Login Successful!")
                                        st.rerun()
                                else:
                                    st.error(result)

                with tab_reg:
                    with st.form("register_form"):
                        new_user = st.text_input("New Username", key="reg_user")
                        new_pass = st.text_input("New Password", type="password", key="reg_pass")
                        new_email = st.text_input("Email", key="reg_email")
                        reg_submitted = st.form_submit_button("Register")
                    
                    if reg_submitted:
                        if not new_user or not new_pass:
                            st.warning("Username and Password are required.")
                        else:
                            with st.spinner("Creating Account..."):
                                time.sleep(0.5)
                                success, msg = st.session_state.auth_manager.register_user(new_user, new_pass, new_email)
                                if success:
                                    st.success(msg)
                                else:
                                    st.error(msg)
        
            elif st.session_state.login_stage == '2fa':
                neon_header("Two-Factor Authentication", level=2)
                with st.form("2fa_form"):
                    code = st.text_input("Enter 6-digit 2FA Code", max_chars=6, key="2fa_code_input")
                    verify_submit = st.form_submit_button("Verify", type="primary")
                
                if verify_submit:
                    with st.spinner("Verifying 2FA..."):
                        time.sleep(0.3)
                        username = st.session_state.login_user
                        if st.session_state.auth_manager.verify_2fa_login(username, code):
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            # Restore user data
                            result = st.session_state.temp_user_data
                            st.session_state.user_role = result['role']
                            st.session_state.user_manager = UserManager(username)
                            st.session_state.last_active = time.time()
                            token = st.session_state.session_manager.create_session(username, st.session_state.remember_me)
                            st.session_state.session_token = token
                            st.query_params["session_id"] = token
                            st.markdown(f"<script>localStorage.setItem('capacitybay_session', '{token}');</script>", unsafe_allow_html=True)
                            st.session_state.login_stage = 'credentials'
                            st.session_state.temp_user_data = None
                            st.session_state.remember_me = None
                            st.session_state.sound_queue.append("connect")
                            st.success("Login Successful!")
                            st.rerun()
                        else:
                            st.error("Invalid 2FA Code")

                if st.button("Cancel"):
                    st.session_state.login_stage = 'credentials'
                    st.session_state.temp_user_data = None
                    st.rerun()

    st.stop()

# --- Main Dashboard ---
import pandas as pd
import numpy as np
import subprocess
import signal
import streamlit.components.v1 as components
from config.trading_config import TRADING_CONFIG
import json
import importlib
import core.data
import core.risk
import core.strategies
import core.bot

SESSION_VERSION_KEY = "v25" 
# Optimization: Disabled heavy reload logic for faster startup
if 'loaded_core_version' not in st.session_state:
    st.session_state.loaded_core_version = SESSION_VERSION_KEY

# Lazy imports implemented to reduce initial load time
# from core.bot import TradingBot -> Moved to get_bot
# from core.defi import DeFiManager -> Moved to usage
# from core.auto_trader import AutoTrader -> Moved to usage
# ...

if 'sound_engine' not in st.session_state:
    from core.sound_engine import SoundEngine
    st.session_state.sound_engine = SoundEngine()
if 'trade_replay' not in st.session_state:
    from core.trade_replay import TradeReplay
    st.session_state.trade_replay = TradeReplay()

# --- Top Navigation ---
render_top_nav(st.session_state.username)

# --- Sidebar Navigation ---
page_nav = render_sidebar_menu()

if "symbol" not in st.session_state:
    st.session_state.symbol = "BTC/USDT"
if "timeframe" not in st.session_state:
    st.session_state.timeframe = "1h"

symbol = st.session_state.symbol
timeframe = st.session_state.timeframe
auto_refresh = False

if 'exchange' not in st.session_state:
    st.session_state.exchange = 'binance'
exchange = st.session_state.exchange

# --- PAGE ROUTING ---

# 1. TRADING DASHBOARD
if page_nav == "Trading Dashboard":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # --- INITIALIZE BOT ---
    try:
        bot = get_bot(exchange)
        bot.symbol = symbol
        bot.timeframe = timeframe
        
        if 'nlp_engine' not in st.session_state:
            st.session_state.nlp_engine = NLPEngine(bot)
        else:
            st.session_state.nlp_engine.bot = bot
            
        # Audio Alerts
        if 'sound_queue' in st.session_state and st.session_state.sound_queue:
            unique_sounds = list(dict.fromkeys(st.session_state.sound_queue))
            for sound in unique_sounds:
                audio_html = st.session_state.sound_engine.get_audio_html(sound)
                if audio_html:
                    st.markdown(audio_html, unsafe_allow_html=True)
            st.session_state.sound_queue = [] 
    except Exception as e:
        st.error(f"Failed to initialize bot: {e}")
        st.stop()
    
    # --- CONTROL PANEL ---
    with st.container():
        c_p1, c_p2, c_p3, c_p4, c_p5 = st.columns([1.5, 1, 1, 2, 1])
        
        with c_p1:
            common_symbols = [
                "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", 
                "DOT/USDT", "LINK/USDT", "MATIC/USDT", "AVAX/USDT", "UNI/USDT", "LTC/USDT", "ATOM/USDT", 
                "NEAR/USDT", "APT/USDT", "QNT/USDT", "ARB/USDT", "OP/USDT", "PEPE/USDT", "SHIB/USDT", 
                "WIF/USDT", "BONK/USDT", "FET/USDT", "RNDR/USDT", "SUI/USDT", "SEI/USDT", "TIA/USDT", 
                "INJ/USDT", "IMX/USDT", "LDO/USDT", "FIL/USDT", "HBAR/USDT", "VET/USDT", "XLM/USDT", 
                "ALGO/USDT", "STX/USDT", "AAVE/USDT", "MKR/USDT", "SNX/USDT", "GRT/USDT", "SAND/USDT", 
                "MANA/USDT", "AXS/USDT", "GALA/USDT", "THETA/USDT", "EGLD/USDT", "XTZ/USDT", "KAS/USDT", "TON/USDT"
            ]
            if symbol not in common_symbols:
                common_symbols.insert(0, symbol)
            selected_symbol = st.selectbox("Market Pair", common_symbols, index=common_symbols.index(symbol))
            if selected_symbol != st.session_state.symbol:
                st.session_state.symbol = selected_symbol
                st.rerun()
                
        with c_p2:
            timeframes = ['30s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
            selected_tf = st.selectbox("Timeframe", timeframes, index=timeframes.index(timeframe) if timeframe in timeframes else 6)
            if selected_tf != st.session_state.timeframe:
                st.session_state.timeframe = selected_tf
                st.rerun()
                
        with c_p3:
             # Dynamic: Show Chain if in DEX/Web3 Mode, else Exchange
             is_web3_mode = st.session_state.get('trading_mode') == 'Live' and not st.session_state.get('exchange_connected', False)
             
             if is_web3_mode and hasattr(bot, 'defi'):
                 # Dynamically fetch supported chains from DeFiManager
                 chains = list(bot.defi.CHAINS.keys()) if hasattr(bot.defi, 'CHAINS') else ['ethereum', 'bsc', 'polygon', 'avalanche', 'solana', 'ton', 'tron']
                 curr_chain = bot.defi.current_chain if hasattr(bot.defi, 'current_chain') else 'ethereum'
                 
                 selected_chain = st.selectbox("Network", chains, index=chains.index(curr_chain) if curr_chain in chains else 0)
                 
                 if selected_chain != curr_chain:
                     bot.defi.connect_to_chain(selected_chain)
                     
                     # Sync Web3Wallet if connected
                     if hasattr(bot, 'web3_wallet') and bot.web3_wallet.connected:
                         try:
                             # Map DeFiManager chain to Web3Wallet chain_id
                             chain_cfg = bot.defi.CHAINS.get(selected_chain, {})
                             chain_type = chain_cfg.get('type', 'evm')
                             
                             new_chain_id = '1' # Default
                             if chain_type == 'evm':
                                 new_chain_id = str(chain_cfg.get('chain_id', 1))
                             elif chain_type == 'solana':
                                 new_chain_id = 'solana'
                             elif chain_type == 'ton':
                                 new_chain_id = 'ton'
                             elif chain_type == 'tron':
                                 new_chain_id = 'tron'
                                 
                             # Re-connect to update RPC/Context
                             creds = bot.web3_wallet.private_key if bot.web3_wallet.private_key else bot.web3_wallet.address
                             bot.web3_wallet.connect(creds, chain_id=new_chain_id, provider=bot.web3_wallet.provider)
                             st.toast(f"Wallet Synced to {selected_chain.upper()}")
                         except Exception as e:
                             print(f"Wallet Sync Error: {e}")

                     st.toast(f"Switched to {selected_chain.upper()}")
                     st.rerun()
             else:
                 exchanges = ['binance', 'coinbase', 'kraken', 'kucoin', 'bybit']
                 selected_ex = st.selectbox("Exchange", exchanges, index=exchanges.index(exchange) if exchange in exchanges else 0)
                 if selected_ex != st.session_state.exchange:
                     st.session_state.exchange = selected_ex
                     st.rerun()
                 
        with c_p2:
            # Dynamic Strategy List
            strategy_options = list(bot.strategies.keys()) if hasattr(bot, 'strategies') else ["Smart Trend"]
            
            # Fallback if empty
            if not strategy_options: strategy_options = ["Smart Trend"]
            
            # Get current index
            curr_strat = bot.active_strategy.name if bot.active_strategy else strategy_options[0]
            try:
                idx = strategy_options.index(curr_strat)
            except ValueError:
                idx = 0
                
            selected_strategy = st.selectbox("Active Strategy", strategy_options, index=idx, key="strat_select_dash")
            
            if selected_strategy != curr_strat:
                bot.set_strategy(selected_strategy)
                st.rerun()
            
        with c_p5:
            # --- Live/Demo Mode ---
            is_web3 = 'web3_wallet' in st.session_state and st.session_state.web3_wallet.is_connected()
            is_cex = st.session_state.get('exchange_connected', False)
            curr_mode = st.session_state.get('trading_mode', 'Demo')
            idx = 0 if curr_mode == 'Live' else 1
            
            new_mode = st.radio("Mode", ["Live", "Demo"], index=idx, label_visibility="collapsed", horizontal=True, key="dash_mode_toggle_top")
            
            if new_mode == 'Live':
                if not (is_web3 or is_cex):
                     st.toast("⚠️ Connect Wallet for Live Mode", icon="⚠️")
                     # We don't force switch back here to allow UI to show "Live" but warn
                else:
                     internal = 'DEX' if is_web3 and not is_cex else 'CEX_Direct'
                     bot.set_trading_mode(internal)
                     bot.risk_manager.set_mode(internal)
                     st.session_state.trading_mode = 'Live'
                     
                     # Quick Sync
                     if is_web3:
                         # Use centralized bot logic to avoid fake/hardcoded prices
                         bot.sync_live_balance()
                         # UI update will happen on rerun/refresh via risk_manager
                         pass
            else:
                bot.set_trading_mode('Demo')
                bot.risk_manager.set_mode('Demo')
                st.session_state.trading_mode = 'Demo'
                
            if st.button("Refresh", use_container_width=True, key="refresh_dash_btn"):
                st.rerun()
            
    # Auto-Refresh Logic (Non-blocking check)
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    
    if st.session_state.auto_refresh:
        time_now = time.time()
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time_now
        
        if time_now - st.session_state.last_refresh > 60:
            st.session_state.last_refresh = time_now
            st.rerun()
        else:
            # Force a rerun after sleep to check again? No, that blocks.
            # We rely on interaction or the user accepting manual refresh for now.
            # To truly support auto-refresh, we'd need a component.
            # For now, we'll just show the toggle state.
            pass

    # --- METRICS ROW ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        # Sync Button Integration
        col_bal, col_sync = st.columns([3, 1])
        with col_bal:
            total_bal = bot.risk_manager.current_capital
            metric_card("Total Balance", f"${total_bal:,.2f}", "+0.0%", "#00f2ff")
        with col_sync:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄", help="Sync Balance", key="sync_bal_main"):
                with st.spinner("Syncing..."):
                    try:
                        bot.sync_live_balance()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sync: {e}")
    with m2:
        metrics = st.session_state.user_manager.get_performance_metrics() if 'user_manager' in st.session_state else {}
        pnl_total = metrics.get('total_pnl', 0.0)
        metric_card("Total Profit", f"${pnl_total:,.2f}", None, "#00ff9d")
    with m3:
        win_rate = metrics.get('win_rate', 0.0)
        metric_card("Win Rate", f"{win_rate:.1f}%", None, "#bd00ff")
    with m4:
        active_trades = len(bot.open_positions)
        metric_card("Active Trades", f"{active_trades}", None, "#f59e0b")

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # --- MAIN GRID LAYOUT ---
    col_chart, col_actions = st.columns([3, 1])
    
    with st.spinner("Fetching Market Data..."):
        raw_df = get_cached_ohlcv(bot, symbol, timeframe)
        
    with col_chart:
        # --- CHART SECTION ---
        pair = symbol.replace("/", "").upper()
        tv_symbol = f"BINANCE:{pair}"
        tv_interval_map = {'30s': '1', '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30', '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720', '1d': 'D'}
        tv_interval = tv_interval_map.get(timeframe, '60')
        
        html_code = f'<div class="tradingview-widget-container" style="height:600px;width:100%"><div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>{{"autosize": true, "symbol": "{tv_symbol}", "interval": "{tv_interval}", "timezone": "Etc/UTC", "theme": "dark", "style": "1", "locale": "en", "enable_publishing": false, "allow_symbol_change": true, "support_host": "https://www.tradingview.com"}}</script></div>'
        components.html(html_code, height=600)
        
    with col_actions:
        # --- QUICK ACTIONS & MANUAL TRADE ---
        neon_header("Quick Actions", level=4)
        
        # Auto-Trading Control
        is_running = False
        if hasattr(bot, 'auto_trader'):
            is_running = bot.auto_trader.is_running
        
        with st.expander("🤖 Auto-Trading Pilot", expanded=True):
            c_at1, c_at2 = st.columns(2)
            with c_at1:
                at_tf = st.selectbox("Bot Timeframe", ['1m', '5m', '15m', '1h', '4h'], index=3, key="bot_tf_select")
            with c_at2:
                at_amt = st.number_input("Trade Amount", min_value=0.001, value=0.01, step=0.001, key="bot_amt_input")
            
            enable_auto = st.checkbox("Enable Auto-Execution", value=is_running, key="bot_enable_toggle")
            
            if enable_auto and not is_running:
                 # Pass params to bot instance
                 bot.auto_trader_timeframe = at_tf
                 bot.auto_trader_amount = at_amt
                 
                 bot.auto_trader.start() 
                 bot.start() # Also start main bot loop if separate
                 
                 st.toast(f"Auto-Trading Started ({at_tf}, Amt: {at_amt})")
                 st.rerun()
            elif not enable_auto and is_running:
                 bot.auto_trader.stop()
                 bot.stop()
                 st.toast("Auto-Trading Stopped")
                 st.rerun()
            
            if is_running:
                st.markdown(f"<div style='text-align: center; color: #00ff9d; font-weight: bold; margin-top: 5px;'>● Running on {at_tf} | Size: {at_amt}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align: center; color: #64748b; margin-top: 5px;'>Inactive</div>", unsafe_allow_html=True)
            
        st.divider()
        
        # Manual Trade Mini-Panel
        st.markdown("**Quick Trade**")
        with st.form("quick_trade_form"):
            q_col1, q_col2 = st.columns(2)
            with q_col1:
                q_side = st.selectbox("Side", ["buy", "sell"], label_visibility="collapsed")
            with q_col2:
                q_amount = st.number_input("Amount", min_value=0.0, step=0.001, format="%.4f")
            
            auto_close = st.checkbox("Enable Auto-Close (TP/SL)", value=True, help="Automatically manage this trade with Stop Loss and Take Profit")
            q_submit = st.form_submit_button("Execute Order", use_container_width=True)
            
            if q_submit:
                if q_amount <= 0:
                    st.error("Invalid Amount")
                else:
                    try:
                        if auto_close:
                            with st.spinner("Calculating Risk Parameters..."):
                                # Fetch Price & ATR for Smart SL/TP
                                ticker = bot.data_manager.fetch_ticker(symbol)
                                price = ticker.get('last', ticker.get('close', 0))
                                
                                # Estimate ATR if not available
                                atr = price * 0.02 
                                try:
                                    df = bot.data_manager.fetch_ohlcv(symbol, timeframe, limit=50)
                                    if not df.empty:
                                        import pandas_ta as ta
                                        df.ta.atr(length=14, append=True)
                                        atr = df['ATRr_14'].iloc[-1] if 'ATRr_14' in df else (df['high'] - df['low']).mean()
                                except:
                                    pass
                                
                                # Use Place method which attaches SL/TP
                                res = bot.execution.place(symbol, q_side, q_amount, price, atr, bot.risk_manager)
                        else:
                            res = bot.execution.execute_robust(symbol, q_side, q_amount, strategy='market')
                        
                        st.success(f"Order Sent! {res}")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        err_msg = str(e)
                        # Handle Tenacity RetryError to show actual cause
                        if "RetryError" in type(e).__name__:
                            try:
                                if hasattr(e, 'last_attempt'):
                                    attempt = e.last_attempt
                                    if attempt and attempt.exception():
                                        err_msg = str(attempt.exception())
                            except:
                                pass
                        st.error(f"Failed: {err_msg}")
        
        st.divider()
        if st.button("🚨 Flatten All Positions", type="primary", use_container_width=True):
             try:
                 bot.execution.close_all()
                 st.success("All positions closed.")
                 time.sleep(1)
                 st.rerun()
             except Exception as e:
                 err_msg = str(e)
                 # Handle Tenacity RetryError to show actual cause
                 if "RetryError" in type(e).__name__:
                     try:
                         if hasattr(e, 'last_attempt'):
                             attempt = e.last_attempt
                             if attempt and attempt.exception():
                                 err_msg = str(attempt.exception())
                     except:
                         pass
                 st.error(f"Flatten Failed: {err_msg}")

    # --- BOTTOM SECTION (Trade History) ---
    st.divider()
    
    # Use tabs for positions and history
    tab_pos, tab_hist = st.tabs(["Active Positions", "Trade History"])
    
    with tab_pos:
        if hasattr(bot, 'open_positions') and bot.open_positions:
            # Custom Rendering for Active Positions
            st.markdown(f"**Open Positions ({len(bot.open_positions)})**")
            
            # Header
            h1, h2, h3, h4, h5 = st.columns([2, 1, 1, 1, 1])
            h1.markdown("*Symbol*")
            h2.markdown("*Side*")
            h3.markdown("*Size*")
            h4.markdown("*PnL*")
            h5.markdown("*Action*")
            st.divider()
            
            # Rows
            for i, pos in enumerate(bot.open_positions):
                c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
                
                symbol_display = pos.get('symbol', 'Unknown')
                side_display = pos.get('side', 'buy').upper()
                amt_display = pos.get('amount', 0)
                pnl_val = pos.get('pnl', 0)
                
                with c1: st.markdown(f"**{symbol_display}**")
                with c2: 
                    color = "green" if side_display == "BUY" else "red"
                    st.markdown(f":{color}[{side_display}]")
                with c3: st.markdown(f"{amt_display}")
                with c4:
                    pnl_color = "green" if pnl_val >= 0 else "red"
                    st.markdown(f":{pnl_color}[{pnl_val:.2f}%]")
                with c5:
                    if st.button("Close", key=f"close_pos_{i}_{symbol_display}"):
                        try:
                            # Execute Close
                            close_side = 'sell' if side_display in ['BUY', 'LONG'] else 'buy'
                            bot.execution.execute_robust(symbol_display, close_side, amt_display, strategy='manual_close')
                            
                            # Remove from list (Optimistic UI update)
                            bot.open_positions.pop(i)
                            if hasattr(bot, 'save_positions'):
                                bot.save_positions()
                                
                            st.toast(f"Closed {symbol_display}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            err_msg = str(e)
                            # Handle Tenacity RetryError to show actual cause
                            if "RetryError" in type(e).__name__:
                                try:
                                    if hasattr(e, 'last_attempt'):
                                        attempt = e.last_attempt
                                        if attempt and attempt.exception():
                                            err_msg = str(attempt.exception())
                                except:
                                    pass
                            st.error(f"Close Failed: {err_msg}")
        else:
            st.info("No active positions.")
            
    with tab_hist:
        # Load trade history from log file
        log_file = "trade_log.json"
        history_data = []
        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    history_data = json.load(f)
            except:
                pass
        
        if history_data:
            # Create DataFrame with specific columns
            # Ensure we map the data correctly to: Time, Side, Symbol, Qty, Entry, Exit, PnL, Reason
            
            # Normalize data structure if needed
            flat_data = []
            for t in history_data:
                # Handle different formats if log structure varies
                entry = {
                    "Time": t.get("timestamp", t.get("time", "")),
                    "Side": t.get("side", "").upper(),
                    "Symbol": t.get("symbol", ""),
                    "Qty": t.get("amount", 0),
                    "Entry": t.get("price", t.get("entry_price", 0)),
                    "Exit": t.get("exit_price", "-"),
                    "PnL": t.get("pnl", "-"),
                    "Reason": t.get("strategy", t.get("reason", "Manual"))
                }
                flat_data.append(entry)
                
            df_hist = pd.DataFrame(flat_data)
            
            # Display
            st.dataframe(df_hist, use_container_width=True)
            
            c_h1, c_h2, c_h3 = st.columns([1, 1, 4])
            with c_h1:
                if st.button("Clear History"):
                    with open(log_file, "w") as f:
                        json.dump([], f)
                    st.rerun()
            with c_h2:
                csv = df_hist.to_csv(index=False)
                st.download_button("Export CSV", csv, "trade_history.csv", "text/csv")
        else:
            st.info("No trade history available.")
            
    # --- ASSISTANT SECTION (Moved to bottom) ---
    st.divider()
    neon_header("Capa-X Assistant", level=3)
    user_query = st.text_input("Command Interface", placeholder="Ask Capa-X...")
    if user_query and 'nlp_engine' in st.session_state:
        response = st.session_state.nlp_engine.process_query(user_query, st.session_state.user_manager)
        st.markdown(f"**> {response}**")


# 4. AI MARKET ANALYZER
elif page_nav == "AI Market Analyzer":
    neon_header("🧠 AI Market Analyzer")
    bot = get_bot(exchange)
    
    c_ai_ctrl, c_ai_view = st.columns([1, 3])
    
    with c_ai_ctrl:
        st.subheader("Configuration")
        
        # Symbol & Timeframe Selection
        ai_sym = st.selectbox("Target Asset", [st.session_state.symbol, "BTC/USDT", "ETH/USDT", "SOL/USDT", "TON/USDT", "BNB/USDT", "XRP/USDT"], key="ai_sym")
        ai_tf = st.selectbox("Timeframe", ["5m", "15m", "1h", "4h", "1d"], index=2, key="ai_tf")
        
        if st.button("🚀 Run AI Analysis", type="primary", use_container_width=True):
            st.session_state.ai_analysis_trigger = True
            
    with c_ai_view:
        if st.session_state.get('ai_analysis_trigger'):
            with st.spinner(f"Processing {ai_sym} market data..."):
                # 1. Fetch Data
                df = bot.data_manager.fetch_ohlcv(ai_sym, ai_tf, limit=200)
                
                if df is not None and not df.empty:
                    # 2. Run Brain Analysis
                    analysis = bot.brain.analyze_market(df)
                    
                    st.session_state.ai_analysis_result = {
                        "symbol": ai_sym,
                        "analysis": analysis,
                        "last_price": df['close'].iloc[-1],
                        "data": df
                    }
                    st.session_state.ai_analysis_trigger = False
                else:
                    st.error("Failed to fetch market data.")
                    
        if 'ai_analysis_result' in st.session_state:
            res = st.session_state.ai_analysis_result
            analysis = res['analysis']
            df = res['data']
            
            # Header Metrics
            m1, m2, m3 = st.columns(3)
            with m1:
                metric_card("Current Price", f"${res['last_price']:,.2f}", None, "#ffffff")
            with m2:
                score = analysis.get('score', 0)
                color = "#00ff9d" if score > 0 else "#ff3b3b"
                metric_card("AI Signal Strength", f"{score:.2f}", None, color)
            with m3:
                regime = analysis.get('regime', {})
                r_name = regime.get('type', 'Unknown')
                metric_card("Market Regime", r_name, None, "#00f2ff")
                
            st.divider()
            
            # Recommendation
            rec = "NEUTRAL"
            if score > 0.2: rec = "BULLISH"
            if score > 0.6: rec = "STRONG BUY"
            if score < -0.2: rec = "BEARISH"
            if score < -0.6: rec = "STRONG SELL"
            
            r_color = "green" if score > 0 else "red"
            st.markdown(f"## AI Recommendation: :{r_color}[{rec}]")
            
            # Technicals
            st.markdown("### Technical Features")
            feats = analysis.get('features', {})
            kf1, kf2, kf3 = st.columns(3)
            with kf1:
                metric_card("RSI", f"{feats.get('rsi', 0):.2f}")
            with kf2:
                metric_card("ATR", f"{feats.get('atr', 0):.4f}")
            with kf3:
                metric_card("ADX", f"{feats.get('adx', 0):.2f}")

            # Chart
            import plotly.graph_objects as go
            fig = go.Figure(data=[go.Candlestick(x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'])])
            fig.update_layout(title=f"{res['symbol']} Price Action", template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("👈 Select parameters and click 'Run AI Analysis' to generate insights.")

# 2. STRATEGY INTELLIGENCE (Formerly Strategy Manager)
elif page_nav == "Strategy Intelligence":
    neon_header("🧠 Strategy Command Center")
    bot = get_bot(exchange)
    
    # ... (Reuse Logic from Strategy Manager) ...
    
    # --- Strategy Control Header ---
    c_strat, c_tf, c_mode = st.columns([2, 1, 1])
    
    with c_strat:
        current_strat = bot.active_strategy_name
        strategy_names = list(bot.strategies.keys())
        idx = strategy_names.index(current_strat) if current_strat in strategy_names else 0
        selected_strat = st.selectbox("Active Strategy", strategy_names, index=idx, key="strat_select_intel")
        
        if selected_strat != current_strat:
            bot.active_strategy_name = selected_strat
            bot.active_strategy = bot.strategies[selected_strat]
            st.toast(f"Switched to {selected_strat}", icon="🧠")
            time.sleep(0.5)
            st.rerun()
            
    with c_tf:
        timeframes = ['30s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
        tf_idx = timeframes.index(bot.timeframe) if bot.timeframe in timeframes else 6
        new_tf = st.selectbox("Timeframe", timeframes, index=tf_idx, key="strat_tf_intel")
        if new_tf != bot.timeframe:
            bot.timeframe = new_tf
            st.session_state.timeframe = new_tf
            st.rerun()
            
    with c_mode:
        st.markdown('<div style="font-size: 12px; color: #888; margin-bottom: 5px;">Trading Mode</div>', unsafe_allow_html=True)
        is_web3 = 'web3_wallet' in st.session_state and st.session_state.web3_wallet.is_connected()
        is_cex = st.session_state.get('exchange_connected', False)
        curr_mode = st.session_state.get('trading_mode', 'Demo')
        
        mode_idx = 0 if curr_mode == 'Live' else 1
        new_mode_intel = st.radio("Mode_Intel", ["Live", "Demo"], index=mode_idx, label_visibility="collapsed", horizontal=True, key="strat_mode_toggle_intel")
        
        if new_mode_intel == 'Live' and curr_mode != 'Live':
            if not (is_web3 or is_cex):
                 st.toast("⚠️ Connect Wallet for Live Mode", icon="⚠️")
            else:
                 internal = 'DEX' if is_web3 and not is_cex else 'CEX_Direct'
                 bot.set_trading_mode(internal)
                 bot.risk_manager.set_mode(internal)
                 st.session_state.trading_mode = 'Live'
                 
                 # Quick Sync
                 if is_web3:
                     w3_bal = st.session_state.web3_wallet.get_balance()
                     st.session_state.web3_balance = w3_bal
                     # Estimate USD
                     chain_id = st.session_state.web3_wallet.chain_id
                     usd_price = 0.0
                     # Try fetch real price
                     try:
                         sym = st.session_state.web3_wallet.CHAINS.get(chain_id, {}).get('symbol', 'ETH')
                         p = bot.data_manager.get_current_price(f"{sym}/USDT")
                         if p: usd_price = p
                     except:
                         pass
                     bot.risk_manager.update_live_balance(w3_bal * usd_price)
                 st.rerun()
        elif new_mode_intel == 'Demo' and curr_mode != 'Demo':
            bot.set_trading_mode('Demo')
            bot.risk_manager.set_mode('Demo')
            st.session_state.trading_mode = 'Demo'
            st.rerun()
        
    st.divider()
    
    # --- Configuration Panel ---
    with st.expander("⚙️ Strategy Configuration", expanded=True):
        st.info(f"**{bot.active_strategy.name}**: {bot.active_strategy.__doc__ or 'No description available.'}")
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.number_input("Risk per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, key="strat_risk_input")
        with sc2:
            st.number_input("Max Open Positions", min_value=1, max_value=10, value=3, key="strat_max_pos_input")
        with sc3:
            st.toggle("Use AI Confirmation", value=True, key="strat_ai_toggle")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- Auto-Pilot Redesign ---
    neon_header("🤖 Auto-Pilot Control System", level=2)
    
    if 'auto_trader' not in st.session_state:
        st.session_state.auto_trader = AutoTrader(bot)
    at = st.session_state.auto_trader
    
    # --- Integration: User Inputs for Auto-Bot ---
    with st.container(border=True):
        st.markdown("**Bot Configuration**")
        c_bc1, c_bc2, c_bc3 = st.columns(3)
        with c_bc1:
            # Sync Timeframe
            tf_opts = ['1m', '5m', '15m', '1h', '4h', '1d']
            curr_tf = bot.timeframe if bot.timeframe in tf_opts else '1h'
            new_tf_bot = st.selectbox("Bot Timeframe", tf_opts, index=tf_opts.index(curr_tf), key="bot_tf_override")
            if new_tf_bot != bot.timeframe:
                bot.timeframe = new_tf_bot
                st.toast(f"Bot Timeframe set to {new_tf_bot}")
                
        with c_bc2:
            # Trade Amount
            curr_amt = getattr(bot, 'trade_amount_override', 0.0)
            new_amt = st.number_input("Trade Amount (USDT)", min_value=0.0, value=float(curr_amt), step=10.0, help="Fixed USDT amount per trade. Set 0 for dynamic sizing.", key="bot_amt_override")
            if new_amt != curr_amt:
                bot.trade_amount_override = new_amt
                
        with c_bc3:
            # Master Enable
            is_enabled = at.is_running
            if st.toggle("Enable Auto-Trading", value=is_enabled, key="bot_master_toggle"):
                if not at.is_running:
                    at.start()
                    st.rerun()
            else:
                if at.is_running:
                    at.stop()
                    st.rerun()

    # Status Board
    status_color = "#00ff9d" if at.is_running else "#ff3b3b"
    status_text = "SYSTEM ACTIVE" if at.is_running else "SYSTEM STOPPED"
    
    mode_text = st.session_state.get('trading_mode', 'Demo').upper()
    mode_color = "#ff0000" if mode_text == "LIVE" else "#00ff9d"
    
    st.markdown(f'<div style="border: 1px solid {status_color}; border-radius: 12px; padding: 25px; background: linear-gradient(90deg, rgba(0,0,0,0.4) 0%, rgba(20,25,35,0.8) 100%); box-shadow: 0 0 20px {status_color}20; display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;"><div><div style="font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Operational Status</div><div style="font-size: 24px; font-weight: bold; color: {status_color}; text-shadow: 0 0 10px {status_color}80;">{status_text}</div><div style="font-size: 12px; color: #666; margin-top: 5px;">Uptime: 00:00:00</div></div><div style="text-align: right;"><div style="font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Execution Mode</div><div style="font-size: 24px; font-weight: bold; color: {mode_color}; text-shadow: 0 0 10px {mode_color}80;">{mode_text}</div><div style="font-size: 12px; color: #666; margin-top: 5px;">{bot.exchange_id.upper()} • {bot.symbol}</div></div></div>', unsafe_allow_html=True)
    
    # Control Buttons
    col_run, col_log = st.columns([1, 2])
    
    with col_run:
        if at.is_running:
            if st.button("⏹ TERMINATE", type="primary", use_container_width=True, key="stop_auto_btn"):
                at.stop()
                st.rerun()
            st.markdown(f"<div style='text-align: center; color: #888; margin-top: 10px; font-size: 12px;'>Press to stop all automated activities. Open positions will be managed by Risk Manager.</div>", unsafe_allow_html=True)
        else:
            if st.button("🚀 ENGAGE AUTO-PILOT", use_container_width=True, key="start_auto_btn"):
                at.start()
                st.rerun()
            st.markdown(f"<div style='text-align: center; color: #888; margin-top: 10px; font-size: 12px;'>Press to activate automated trading strategy. Ensure parameters are correct.</div>", unsafe_allow_html=True)

    with col_log:
        st.markdown("**System Terminal**")
        log_ph = st.empty()
        
        # Simulated Log (Replace with real log buffer if available)
        log_lines = [
            f"[{time.strftime('%H:%M:%S')}] System initialized.",
            f"[{time.strftime('%H:%M:%S')}] Strategy: {bot.active_strategy.name}",
            f"[{time.strftime('%H:%M:%S')}] Mode: {mode_text}",
            f"[{time.strftime('%H:%M:%S')}] Waiting for market data..."
        ]
        
        if at.is_running:
            log_lines.append(f"[{time.strftime('%H:%M:%S')}] Analyzing {bot.symbol} ({bot.timeframe})...")
            log_lines.append(f"[{time.strftime('%H:%M:%S')}] AI Confidence: {np.random.randint(60, 99)}%")
            
        log_html = "<div style='font-family: monospace; font-size: 12px; color: #00ff9d; background: #000; padding: 10px; border-radius: 5px; height: 150px; overflow-y: auto;'>"
        for line in log_lines:
            log_html += f"<div>{line}</div>"
        log_html += "</div>"
        
        log_ph.markdown(log_html, unsafe_allow_html=True)

# 3. MANUAL TRADING
elif page_nav == "Manual Trading":
    neon_header("🛠️ Pro Trading Terminal")
    bot = get_bot(exchange)
    
    # --- Styles for the Terminal ---
    st.markdown('<style>.big-metric { font-size: 24px; font-weight: bold; color: #00f2ff; } .price-metric { font-size: 24px; font-weight: bold; color: #00ff9d; } .terminal-label { font-size: 12px; color: #888; margin-bottom: 2px; } .stButton>button { width: 100%; border-radius: 4px; } .buy-btn>button { background-color: #00bd55; color: white; border: none; height: 45px; font-size: 16px; font-weight: bold; } .sell-btn>button { background-color: #ff3b3b; color: white; border: none; height: 45px; font-size: 16px; font-weight: bold; } .preset-btn>button { padding: 0px; font-size: 10px; height: 25px; }</style>', unsafe_allow_html=True)
    
    # --- Top Metrics Row ---
    c_m1, c_m2, c_m3 = st.columns([1, 1, 2])
    
    with c_m1:
        st.markdown('<div class="terminal-label">Balance</div>', unsafe_allow_html=True)
        
        # --- Trading Mode Selector (Added for User Convenience) ---
        mode_cols = st.columns([1, 1])
        with mode_cols[0]:
             # Check connection status
             is_web3 = 'web3_wallet' in st.session_state and st.session_state.web3_wallet.is_connected()
             is_cex = st.session_state.get('exchange_connected', False)
             
             # Default to Live if connected and previously set, otherwise Demo
             current_mode_idx = 0 if st.session_state.get('trading_mode') == 'Live' else 1
             
             new_mode = st.radio("Mode", ["Live", "Demo"], index=current_mode_idx, label_visibility="collapsed", horizontal=True, key="manual_mode_toggle")
             
             if new_mode == "Live":
                 if not (is_web3 or is_cex):
                     st.warning("Connect Wallet First")
                     # Force back to Demo visually if possible, or just don't switch internal mode
                 else:
                     internal_mode = 'DEX' if is_web3 and not is_cex else 'CEX_Direct'
                     bot.set_trading_mode(internal_mode)
                     bot.risk_manager.set_mode(internal_mode)
                     st.session_state.trading_mode = 'Live'
                     
                     # Auto-Sync on Switch
                     if is_web3:
                         w3_bal = st.session_state.web3_wallet.get_balance()
                         st.session_state.web3_balance = w3_bal
                         # Estimate USD
                         chain_id = st.session_state.web3_wallet.chain_id
                         usd_price = 1.0
                         if str(chain_id) in ['ton', 'ton-mainnet']: usd_price = 5.40
                         elif str(chain_id) in ['solana', 'solana-mainnet']: usd_price = 145.20
                         elif str(chain_id) in ['1', 'ethereum']: usd_price = 2600.0
                         
                         capital_usd = w3_bal * usd_price
                         bot.risk_manager.update_live_balance(capital_usd)
                         
             else:
                 bot.set_trading_mode('Demo')
                 bot.risk_manager.set_mode('Demo')
                 st.session_state.trading_mode = 'Demo'

        # --- Auto-Sync Web3 Balance (Continuous) ---
        # Robust Check: Allow sync if address is present, even if is_connected() is flaky
        wallet_obj = st.session_state.get('web3_wallet')
        has_wallet = wallet_obj is not None and wallet_obj.address
        is_live = st.session_state.get('trading_mode') == 'Live'
        is_web3_mode = has_wallet # Define local flag
        
        capital_usd = 0.0 # Initialize safely
        
        if is_live and has_wallet:
             # Ensure address is clean
             if wallet_obj.address != wallet_obj.address.strip():
                 wallet_obj.address = wallet_obj.address.strip()
             
             # Always fetch balance from wallet
             w3_bal = wallet_obj.get_balance()
             st.session_state.web3_balance = w3_bal
             
             # Estimate USD Value
             chain_id = str(wallet_obj.chain_id)
             usd_price = 1.0
             if chain_id in ['ton', 'ton-mainnet']: usd_price = 5.40
             elif chain_id in ['solana', 'solana-mainnet']: usd_price = 145.20
             elif chain_id in ['1', 'ethereum']: usd_price = 2600.0
             elif chain_id in ['56', 'bsc']: usd_price = 600.0
             
             capital_usd = w3_bal * usd_price
             
             # Update Bot Capital if different
             if abs(bot.risk_manager.current_capital - capital_usd) > 0.001:
                 bot.risk_manager.update_live_balance(capital_usd)
                 if 'balance_synced' not in st.session_state:
                     st.session_state.balance_synced = True
                     st.rerun()

        # --- CEX Balance Sync (Added for Live Trading) ---
        elif st.session_state.get('trading_mode') == 'Live' and not is_web3_mode:
             # Periodically sync CEX balance
             if 'last_cex_sync' not in st.session_state or (time.time() - st.session_state.last_cex_sync > 15):
                 bot.sync_live_balance()
                 st.session_state.last_cex_sync = time.time()
                 st.rerun()
        
        bal = bot.risk_manager.current_capital
        
        # Display Logic
        if st.session_state.get('trading_mode') == 'Live' and bal == 0.0:
            st.markdown(f'<div class="big-metric" style="color: #ff3b3b;">$0.00 (Syncing...)</div>', unsafe_allow_html=True)
            if st.button("Force Sync", key="force_sync_btn_man"):
                 bot.risk_manager.update_live_balance(capital_usd) # Use calculated value
                 st.rerun()
        else:
            st.markdown(f'<div class="big-metric">${bal:,.2f}</div>', unsafe_allow_html=True)
        
    with c_m2:
        # Fetch Price
        symbol = st.session_state.get('symbol', 'BTC/USDT')
        ticker = get_cached_ticker(bot, symbol)
        price = ticker.get('last', 0.0) if ticker else 0.0
        
        st.markdown(f'<div class="terminal-label">{symbol} Price</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price-metric">${price:,.2f}</div>', unsafe_allow_html=True)

    # --- Auto-Trading Pilot (Manual Page Integration) ---
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🤖 Auto-Trading Pilot (Real-Time)", expanded=True):
        if 'auto_trader' not in st.session_state:
            st.session_state.auto_trader = AutoTrader(bot)
        at_man = st.session_state.auto_trader
        
        c_at1, c_at2 = st.columns([1, 2])
        with c_at1:
            st.markdown("### Control")
            if at_man.is_running:
                st.success("✅ SYSTEM ACTIVE")
                if st.button("⏹ Stop Auto-Trade", type="primary", key="man_stop_auto", use_container_width=True):
                    at_man.stop()
                    st.rerun()
            else:
                 st.warning("⏸ SYSTEM IDLE")
                 if st.button("🚀 Start Auto-Trade", key="man_start_auto", use_container_width=True):
                     # Update symbols to current selection
                     at_man.symbols = [st.session_state.get('symbol', 'BTC/USDT')]
                     
                     # Ensure bot has web3 wallet attached if in Live mode
                     if st.session_state.get('trading_mode') == 'Live' and 'web3_wallet' in st.session_state:
                          bot.web3_wallet = st.session_state.web3_wallet
                     at_man.start()
                     st.rerun()
                    
        with c_at2:
            st.markdown("### Configuration")
            cur_mode = st.session_state.get('trading_mode', 'Demo')
            mode_color = "red" if cur_mode == "Live" else "green"
            st.markdown(f"**Execution Mode:** <span style='color:{mode_color}; font-weight:bold'>{cur_mode}</span>", unsafe_allow_html=True)
            
            if cur_mode == "Live":
                 if 'web3_wallet' in st.session_state and st.session_state.web3_wallet.is_connected():
                     st.caption(f"Using Wallet: {st.session_state.web3_wallet.address[:6]}...{st.session_state.web3_wallet.address[-4:]}")
                 else:
                     st.error("⚠️ Wallet NOT Connected! Auto-Trade will fail in Live Mode.")
            
            st.caption(f"Strategy: {bot.active_strategy.name}")
            
            if at_man.is_running:
                 st.progress(100, text="Scanning market for opportunities...")

    # --- Main Trading Grid ---
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Initialize Session State for Inputs if not present
    if 'term_sl' not in st.session_state: st.session_state.term_sl = 0.0
    if 'term_tp' not in st.session_state: st.session_state.term_tp = 0.0
    if 'term_qty' not in st.session_state: st.session_state.term_qty = 0.0
    if 'term_sl_mode' not in st.session_state: st.session_state.term_sl_mode = 'Price' # Price or %
    
    with st.container(border=True):
        # ROW 1: Symbol & Amount
        c_r1_1, c_r1_2 = st.columns(2)
        with c_r1_1:
            st.markdown('<div class="terminal-label">Symbol</div>', unsafe_allow_html=True)
            # Simple text input or selectbox, sticking to simple for now
            new_sym = st.text_input("Symbol", value=st.session_state.symbol, label_visibility="collapsed")
            if new_sym != st.session_state.symbol:
                st.session_state.symbol = new_sym
                st.rerun()
                
        with c_r1_2:
            st.markdown('<div class="terminal-label">Amount (USDT)</div>', unsafe_allow_html=True)
            amount_val = st.number_input("Amount", min_value=0.0, step=10.0, label_visibility="collapsed", key="input_amount_usdt")
            
        # ROW 2: SL / TP
        c_r2_1, c_r2_2, c_r2_3, c_r2_4 = st.columns([1.5, 1.5, 1, 1])
        
        is_pct_mode = st.session_state.get('term_sl_mode') == '% Mode'
        sl_label = "Stop Loss (%)" if is_pct_mode else "Stop Loss (Price)"
        tp_label = "Take Profit (%)" if is_pct_mode else "Take Profit (Price)"
        
        with c_r2_1:
            st.markdown(f'<div class="terminal-label">{sl_label}</div>', unsafe_allow_html=True)
            sl_val = st.number_input("SL", value=st.session_state.term_sl, format="%.2f", label_visibility="collapsed", key="input_sl")
            
            # SL Presets
            c_sl1, c_sl2, c_sl3 = st.columns(3)
            if c_sl1.button("SL 1%", key="btn_sl_1"):
                st.session_state.term_sl = 1.0 if is_pct_mode else price * 0.99
                st.rerun()
            if c_sl2.button("SL 1.5%", key="btn_sl_15"):
                st.session_state.term_sl = 1.5 if is_pct_mode else price * 0.985
                st.rerun()
            if c_sl3.button("SL 2%", key="btn_sl_2"):
                st.session_state.term_sl = 2.0 if is_pct_mode else price * 0.98
                st.rerun()

        with c_r2_2:
            st.markdown(f'<div class="terminal-label">{tp_label}</div>', unsafe_allow_html=True)
            tp_val = st.number_input("TP", value=st.session_state.term_tp, format="%.2f", label_visibility="collapsed", key="input_tp")
            
            # TP Presets
            c_tp1, c_tp2, c_tp3 = st.columns(3)
            
            if c_tp1.button("TP 1%", key="btn_tp_1"):
                st.session_state.term_tp = 1.0 if is_pct_mode else price * 1.01
                st.rerun()
            if c_tp2.button("TP 3%", key="btn_tp_3"):
                st.session_state.term_tp = 3.0 if is_pct_mode else price * 1.03
                st.rerun()
            if c_tp3.button("TP 5%", key="btn_tp_5"):
                st.session_state.term_tp = 5.0 if is_pct_mode else price * 1.05
                st.rerun()

        with c_r2_3:
            st.markdown('<div class="terminal-label">Preset Side</div>', unsafe_allow_html=True)
            preset_side = st.selectbox("Side", ["Long (BUY)", "Short (SELL)"], label_visibility="collapsed")
            
        with c_r2_4:
            st.markdown('<div class="terminal-label">SL/TP Mode</div>', unsafe_allow_html=True)
            mode_sel = st.selectbox("Mode", ["Price Mode", "% Mode"], label_visibility="collapsed")
            if mode_sel != st.session_state.get('term_sl_mode'):
                st.session_state.term_sl_mode = mode_sel
                st.session_state.term_sl = 0.0
                st.session_state.term_tp = 0.0
                st.rerun()
            
        # ROW 3: Advanced & Actions
        c_r3_1, c_r3_2, c_r3_3, c_r3_4 = st.columns([1, 1, 1.5, 1.5])
        
        with c_r3_1:
            st.markdown('<div class="terminal-label">Trailing Stop (%)</div>', unsafe_allow_html=True)
            use_trailing = st.checkbox("", value=True, label_visibility="collapsed")
            trailing_pct = st.number_input("Trailing", value=5.0, step=0.5, label_visibility="collapsed")
            
        with c_r3_2:
             st.markdown('<div class="terminal-label">Breakeven</div>', unsafe_allow_html=True)
             use_be = st.checkbox("Move SL to entry", value=True)
             
        with c_r3_3:
            st.markdown('<div class="terminal-label">Action</div>', unsafe_allow_html=True)
            if st.button("↑ Buy / Long", use_container_width=True, type="primary"):
                 if amount_val > 0:
                     qty = amount_val / price if price > 0 else 0
                     
                     exec_sl = sl_val
                     exec_tp = tp_val
                     if is_pct_mode:
                         if exec_sl > 0: exec_sl = price * (1 - (exec_sl / 100))
                         if exec_tp > 0: exec_tp = price * (1 + (exec_tp / 100))
                     
                     try:
                         bot.execution.execute_robust(
                             symbol=st.session_state.symbol,
                             side='buy',
                             amount=qty,
                             price=price,
                             sl=exec_sl,
                             tp=exec_tp,
                             strategy='market'
                         )
                         st.success(f"Bought {qty:.4f} {st.session_state.symbol}")
                         time.sleep(1)
                         st.rerun()
                     except Exception as e:
                        err_msg = str(e)
                        # Handle Tenacity RetryError to show actual cause
                        if "RetryError" in type(e).__name__:
                            try:
                                if hasattr(e, 'last_attempt'):
                                    attempt = e.last_attempt
                                    if attempt and attempt.exception():
                                        err_msg = str(attempt.exception())
                            except:
                                pass
                        st.error(f"Execution Failed: {err_msg}")
                 else:
                     st.error("Invalid Amount")

        with c_r3_4:
            st.markdown('<div class="terminal-label">Action</div>', unsafe_allow_html=True)
            if st.button("↓ Sell / Short", use_container_width=True, type="primary"):
                 if amount_val > 0:
                     qty = amount_val / price if price > 0 else 0
                     
                     exec_sl = sl_val
                     exec_tp = tp_val
                     if is_pct_mode:
                         # Sell: SL above, TP below
                         if exec_sl > 0: exec_sl = price * (1 + (exec_sl / 100))
                         if exec_tp > 0: exec_tp = price * (1 - (exec_tp / 100))
                     
                     try:
                         bot.execution.execute_robust(
                             symbol=st.session_state.symbol,
                             side='sell',
                             amount=qty,
                             price=price,
                             sl=exec_sl,
                             tp=exec_tp,
                             strategy='market'
                         )
                         st.success(f"Sold {qty:.4f} {st.session_state.symbol}")
                         time.sleep(1)
                         st.rerun()
                     except Exception as e:
                        err_msg = str(e)
                        # Handle Tenacity RetryError to show actual cause
                        if "RetryError" in type(e).__name__:
                            try:
                                if hasattr(e, 'last_attempt'):
                                    attempt = e.last_attempt
                                    if attempt and attempt.exception():
                                        err_msg = str(attempt.exception())
                            except:
                                pass
                        st.error(f"Execution Failed: {err_msg}")
                 else:
                     st.error("Invalid Amount")

        # ROW 4: Controls
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        c_r4_1, c_r4_2, c_r4_3 = st.columns([2, 1, 1])
        
        with c_r4_1:
            c_sub1, c_sub2 = st.columns([1, 2])
            with c_sub1:
                if st.button("↺ Reset Demo"):
                     # Reset logic
                     new_bal = st.session_state.get('demo_reset_val', 1000.0)
                     bot.risk_manager.demo_balance = new_bal
                     bot.risk_manager.metrics['Demo']['peak'] = new_bal
                     st.success("Demo Reset!")
                     st.rerun()
            with c_sub2:
                st.number_input("Start Balance", value=1000.0, key="demo_reset_val", label_visibility="collapsed")
                
        with c_r4_3:
            if st.button("✖ Flatten Positions", type="secondary"):
                try:
                    bot.execution.close_all()
                    st.success("All positions closed.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    err_msg = str(e)
                    # Handle Tenacity RetryError to show actual cause
                    if "RetryError" in type(e).__name__:
                        try:
                            if hasattr(e, 'last_attempt'):
                                attempt = e.last_attempt
                                if attempt and attempt.exception():
                                    err_msg = str(attempt.exception())
                        except:
                            pass
                    st.error(f"Error flattening positions: {err_msg}")

    # --- Active Positions Table ---
    st.subheader("Active Positions")
    if bot.risk_manager.open_positions:
        # Header
        h1, h2, h3, h4, h5, h6, h7 = st.columns([1.5, 0.8, 1, 1, 1, 1, 1.2])
        h1.markdown("**Symbol**")
        h2.markdown("**Side**")
        h3.markdown("**Size**")
        h4.markdown("**Entry**")
        h5.markdown("**PnL**")
        h6.markdown("**Auto-Close**") # SL/TP Status
        h7.markdown("**Action**")
        
        st.divider()
        
        # Iterate Positions
        for i, p in enumerate(bot.risk_manager.open_positions):
            symbol = p.get('symbol', 'UNKNOWN')
            side = p.get('side', p.get('type', 'buy')).upper()
            amount = float(p.get('amount', p.get('position_size', 0)))
            entry_price = float(p.get('entry_price', p.get('entry', 0)))
            
            # Current Price
            ticker = get_cached_ticker(bot, symbol)
            current_p = ticker.get('last', entry_price) if ticker else entry_price
            
            # Calc PnL
            if side in ['BUY', 'LONG']:
                pnl_val = (current_p - entry_price) * amount
                pnl_pct = ((current_p - entry_price) / entry_price) * 100
            else:
                pnl_val = (entry_price - current_p) * amount
                pnl_pct = ((entry_price - current_p) / entry_price) * 100
            
            pnl_color = "green" if pnl_val >= 0 else "red"
            
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 0.8, 1, 1, 1, 1, 1.2])
            
            with c1: st.markdown(f"**{symbol}**")
            with c2: st.markdown(f"<span style='color: {'#00ff9d' if side in ['BUY', 'LONG'] else '#ff3b3b'}'>{side}</span>", unsafe_allow_html=True)
            with c3: st.write(f"{amount:.4f}")
            with c4: st.write(f"${entry_price:.2f}")
            with c5: st.markdown(f"<span style='color: {pnl_color}'>${pnl_val:.2f} ({pnl_pct:.2f}%)</span>", unsafe_allow_html=True)
            
            # Auto-Close (SL/TP)
            sl = p.get('sl', p.get('stop_loss', 0))
            tp = p.get('tp', p.get('take_profit', 0))
            
            with c6:
                with st.popover("Edit SL/TP"):
                    new_sl = st.number_input(f"Stop Loss ({symbol})", value=float(sl), key=f"sl_{i}")
                    new_tp = st.number_input(f"Take Profit ({symbol})", value=float(tp), key=f"tp_{i}")
                    if st.button("Update", key=f"upd_{i}"):
                        p['sl'] = new_sl
                        p['stop_loss'] = new_sl
                        p['tp'] = new_tp
                        p['take_profit'] = new_tp
                        bot.save_positions()
                        st.toast(f"Updated SL/TP for {symbol}")
                        st.rerun()
                
                # Status Indicator
                if sl > 0 or tp > 0:
                    st.caption(f"SL: {sl} | TP: {tp}")
                else:
                    st.caption("No Limits")

            # Manual Close Action
            with c7:
                if st.button("Close", key=f"close_{i}", type="primary"):
                    success = bot.execution.close_position(p)
                    if success:
                        st.success(f"Closed {symbol}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed")
            
            st.markdown("---")

    else:
        st.info("No active positions.")

    # --- Trade History (Existing) ---
    st.divider()
    st.subheader("Trade History")
    log_file = "trade_log.json"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                history = json.load(f)
            except:
                history = []
        
        if history:
            # Reverse to show newest first
            history = history[::-1]
            
            # Flatten/Normalize
            flat_data = []
            for t in history:
                # Handle different formats if log structure varies
                entry = {
                    "Time": t.get("timestamp", t.get("time", "")),
                    "Side": t.get("side", "").upper(),
                    "Symbol": t.get("symbol", ""),
                    "Qty": t.get("amount", 0),
                    "Entry": t.get("price", t.get("entry_price", 0)),
                    "Exit": t.get("exit_price", "-"),
                    "PnL": t.get("pnl", "-"),
                    "Reason": t.get("strategy", t.get("reason", "Manual"))
                }
                flat_data.append(entry)
            
            df_hist = pd.DataFrame(flat_data)
            st.dataframe(df_hist, use_container_width=True)
            
            c_h1, c_h2 = st.columns([1, 4])
            with c_h1:
                if st.button("Clear History"):
                    with open(log_file, "w") as f: json.dump([], f)
                    st.rerun()
            with c_h2:
                csv = df_hist.to_csv(index=False)
                st.download_button("Export CSV", csv, "trade_history.csv", "text/csv")
        else:
            st.info("No trade history.")
    else:
        st.info("No trade log found.")



# 4. WALLET & EXECUTION (Formerly Wallet & Funds)
elif page_nav == "Wallet & Execution":
    neon_header("👛 Wallet & Assets")
    bot = get_bot(exchange)

    # --- Exchange Manager Section ---
    with st.expander("Exchange Connection Manager", expanded=True):
        st.markdown("### Exchange Manager")
        
        # Connection Method
        st.markdown("**Connection Method**")
        conn_method = st.radio("Connection Method", ["API (Automatic Trading)", "Manual (Signal Only)"], index=0, horizontal=False, label_visibility="collapsed")
        
        # Active Exchange
        st.markdown("**Active Exchange**")
        exchanges = ['binance', 'coinbase', 'kraken', 'kucoin', 'bybit', 'okx']
        current_ex = st.session_state.get('exchange', 'binance')
        selected_ex = st.selectbox("Active Exchange", exchanges, index=exchanges.index(current_ex) if current_ex in exchanges else 0, label_visibility="collapsed")
        
        if selected_ex != st.session_state.exchange:
            st.session_state.exchange = selected_ex
            st.rerun()
            
        # API Credentials
        with st.expander("API Credentials"):
            c_api1, c_api2 = st.columns(2)
            with c_api1:
                api_key = st.text_input("API Key", type="password")
            with c_api2:
                api_secret = st.text_input("API Secret", type="password")
            
            if st.button("Save Credentials", type="primary"):
                if api_key and api_secret:
                    st.session_state.auth_manager.save_api_keys(st.session_state.username, selected_ex, api_key, api_secret)
                    bot.data_manager.update_credentials(api_key, api_secret)
                    st.success(f"Credentials for {selected_ex} saved securely.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Please enter both API Key and Secret.")
    
    # Execution Control (Merged from Dashboard)
    is_cex_connected = st.session_state.get('exchange_connected', False)
    is_web3_connected = st.session_state.web3_wallet.is_connected() if 'web3_wallet' in st.session_state else False
    is_connected = is_cex_connected or is_web3_connected
    
    # Enable Live Mode Selection (with warning)
    radio_index = 0 if is_connected else 1
    # Check if we should preserve user selection if they selected Live but are not connected?
    # No, keep it simple.
    
    ui_mode = st.radio("Active Mode", ["Live", "Simulation"], index=radio_index, horizontal=True)
    
    if ui_mode == 'Live' and not is_connected:
        st.warning("⚠️ Live Mode requires API Credentials or Web3 Wallet. Please connect.")
    
    if ui_mode == 'Live':
        internal_mode = 'DEX' if is_web3_connected and not is_cex_connected else 'CEX_Direct'
    else:
        internal_mode = 'Demo'

    try:
        bot.set_trading_mode(internal_mode)
        bot.risk_manager.set_mode(internal_mode) # Ensure Risk Manager knows the mode
        st.session_state.trading_mode = ui_mode
    except:
        pass

    if ui_mode == 'Live':
        st.error("⚠️ REAL FUNDS AT RISK")
    else:
        st.success("🛡️ DEMO / PAPER TRADING")
        
    st.divider()
    
    # Wallet Sync
    if st.button("🔄 Sync Balance", use_container_width=True):
        with st.spinner("Syncing..."):
            try:
                # 1. Sync CEX
                if is_cex_connected:
                    bot.sync_live_balance()
                
                # 2. Sync Web3
                if is_web3_connected:
                    w3_bal = st.session_state.web3_wallet.get_balance()
                    st.session_state.web3_balance = w3_bal
                    
                    # Estimate USD
                    chain_id = st.session_state.web3_wallet.chain_id
                    usd_price = 0.0
                    
                    # Map Chain to Symbol
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
                    
                    symbol = symbol_map.get(str(chain_id), 'ETH')
                    
                    # Try fetching live price
                    try:
                        price = get_cached_price(bot, f"{symbol}/USDT")
                        if price:
                            usd_price = price
                        else:
                            # Fallback Prices (Approximate)
                            fallbacks = {
                                'BTC': 95000.0, 'ETH': 2700.0, 'SOL': 150.0, 'BNB': 600.0,
                                'TON': 5.5, 'TRX': 0.16, 'LTC': 70.0, 'DOGE': 0.12, 'ATOM': 6.0,
                                'MATIC': 0.40, 'AVAX': 25.0, 'FTM': 0.60, 'OP': 1.50
                            }
                            usd_price = fallbacks.get(symbol, 0.0)
                    except:
                        pass
                    
                    capital_usd = w3_bal * usd_price
                    bot.risk_manager.update_live_balance(capital_usd)
                    st.success(f"Synced Web3 Balance: ${capital_usd:,.2f}")

                st.session_state[f"wallet_cache_{exchange}_v10"] = bot.wallet_balances
                st.rerun()
            except Exception as e:
                st.error(f"Sync failed: {e}")

    # Metrics
    total_usdt = bot.risk_manager.current_capital
    metric_card("Total Equity", f"${total_usdt:,.2f}", color="#00f2ff")
    
    if hasattr(bot, 'wallet_balances') and bot.wallet_balances:
        # Display Gas Fees if available
        if hasattr(bot, 'latest_gas_fees') and bot.latest_gas_fees:
            gf = bot.latest_gas_fees
            st.info(f"⛽ Gas Fees ({gf.get('type','Standard')}): {gf.get('estimated_cost_gwei',0)} {gf.get('unit','Gwei')}")
            
        df = pd.DataFrame(bot.wallet_balances)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No assets found.")
        if is_cex_connected:
             st.caption("Tip: If you have funds, ensure your API Key has 'Spot' or 'Unified' permissions.")

    # --- ASSET MANAGEMENT ---
    st.divider()
    st.subheader("Asset Management")
    
    # Initialize DeFi Manager
    if 'defi_manager' not in st.session_state or not hasattr(st.session_state.defi_manager, 'get_deposit_address'):
        pk = os.getenv("WALLET_PRIVATE_KEY")
        st.session_state.defi_manager = DeFiManager()
        if pk:
            try:
                st.session_state.defi_manager.load_private_key(pk)
            except Exception:
                pass

    # Sidebar Key Management
    st.sidebar.markdown("---")
    st.sidebar.caption("Session-only key. Never persisted.")
    st.sidebar.subheader("🔐 Enter Private Key (Session Only)")
    pk_input = st.sidebar.text_input("Private Key (0x...)", type="password", placeholder="0x...")
    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        if st.sidebar.button("Save & Connect"):
            try:
                addr = st.session_state.defi_manager.load_private_key(pk_input)
                st.sidebar.success(f"Connected: {addr}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Invalid key: {e}")
    with col_b:
        if st.sidebar.button("Clear Key"):
            st.session_state.defi_manager.clear_private_key()
            st.sidebar.info("Session key cleared.")
            st.rerun()

    # Network Selection
    chains = list(DeFiManager.CHAINS.keys())
    current_chain = st.session_state.defi_manager.current_chain if hasattr(st.session_state.defi_manager, 'current_chain') else 'ethereum'
    selected_chain = st.selectbox("Active Network", chains, index=chains.index(current_chain) if current_chain in chains else 0)
    if selected_chain != current_chain:
        st.session_state.defi_manager.connect_to_chain(selected_chain)

    # Helper for Network Client
    class DashboardNetworkClient:
        def __init__(self, w3, chain_id, name):
            self.w3 = w3
            self.chain_id = chain_id
            self.name = name
    
    _chain_cfg = st.session_state.defi_manager.CHAINS.get(st.session_state.defi_manager.current_chain, {})
    nc = DashboardNetworkClient(
        st.session_state.defi_manager.w3, 
        _chain_cfg.get('id', 1), 
        st.session_state.defi_manager.current_chain.upper()
    )

    tab_trans, tab_dep, tab_bal = st.tabs(["📤 Transfer / Withdraw", "📥 Deposit", "📊 Balances"])
    
    with tab_trans:
        st.markdown("#### Transfer Assets to External Wallet")
        
        # Unified Withdrawal Interface (CEX & Web3)
        mode = st.session_state.get('trading_mode', 'Demo')
        is_cex = mode in ['CEX_Direct', 'CEX_Proxy'] or (mode == 'Live' and st.session_state.get('exchange_connected'))
        
        if is_cex:
            st.info(f"📤 Withdraw from {bot.exchange_id.upper()} (CEX)")
            with st.form("cex_withdraw_form"):
                cw1, cw2 = st.columns(2)
                with cw1:
                    wd_asset = st.selectbox("Asset", ["USDT", "BTC", "ETH", "SOL", "BNB", "USDC", "XRP"])
                    wd_net = st.text_input("Network (e.g. TRC20, ERC20)", value="TRC20")
                with cw2:
                    wd_addr = st.text_input("Recipient Address")
                    wd_amt = st.number_input("Amount", min_value=0.0, step=1.0)
                
                submitted = st.form_submit_button("Initiate CEX Withdrawal")
                if submitted:
                    with st.spinner("Processing CEX Withdrawal..."):
                        res = bot.withdraw_crypto(wd_asset, wd_amt, wd_addr, network=wd_net)
                        if res.get('status') == 'success':
                            st.success(f"✅ Withdrawal Initiated: {res.get('message')}")
                            if 'tx_id' in res:
                                st.code(res['tx_id'], language="text")
                        else:
                            st.error(f"❌ Failed: {res.get('message')}")

        else:
            # Web3 / DeFi Withdrawal
            st.info(f"📤 Withdraw from Web3 Wallet ({st.session_state.defi_manager.current_chain.upper()})")
            
            if not st.session_state.defi_manager.address:
                st.warning("⚠️ Private Key not loaded. Transfers disabled.")
            else:
                with st.expander("Native Transfer (e.g. ETH, BNB, SOL)"):
                    to = st.text_input("Recipient Address (0x...)", key="native_to")
                    amt = st.number_input("Amount (native token)", min_value=0.0, step=0.0001, key="native_amt")
                    if st.session_state.defi_manager.current_chain != 'ton':
                        gas_params = st.session_state.defi_manager.estimate_gas_params(nc)
                        if "gasPrice" in gas_params:
                            st.caption(f"Legacy gas price: {st.session_state.defi_manager.w3.from_wei(gas_params['gasPrice'], 'gwei')} gwei")
                        else:
                            st.caption(f"MaxFeePerGas: {st.session_state.defi_manager.w3.from_wei(gas_params['maxFeePerGas'], 'gwei')} gwei")
                    
                    if st.button("Send Native Transfer"):
                        # Use bot wrapper if available for consistency, else direct
                        if hasattr(bot, 'withdraw_crypto') and bot.trading_mode == 'DEX':
                             # Map symbol based on chain? 
                             # Simpler to use defi_manager directly here for granular control
                             res = st.session_state.defi_manager.transfer_native(nc, to, amt)
                             (st.success if res.startswith("✅") else st.error)(res)
                        else:
                             res = st.session_state.defi_manager.transfer_native(nc, to, amt)
                             (st.success if res.startswith("✅") else st.error)(res)

                token_label = "Jetton Address" if st.session_state.defi_manager.current_chain == 'ton' else "Token Contract (0x...)"
                section_label = "Jetton Transfer" if st.session_state.defi_manager.current_chain == 'ton' else "ERC-20 Transfer"
                
                with st.expander(section_label):
                    token = st.text_input(token_label, key="erc20_token")
                    to2 = st.text_input("Recipient Address", key="erc20_to")
                    amt2 = st.number_input("Amount (tokens)", min_value=0.0, step=0.0001, key="erc20_amt")
                    
                    if token:
                        try:
                            bal_token = st.session_state.defi_manager.erc20_balance(nc, token)
                            st.caption(f"Your token balance: {bal_token}")
                        except Exception as e:
                            st.caption(f"Balance check error: {e}")
                            
                    if st.button(f"Send {section_label}"):
                        res2 = st.session_state.defi_manager.transfer_erc20(nc, token, to2, amt2)
                        (st.success if res2.startswith("✅") else st.error)(res2)

    with tab_dep:
        st.markdown("#### Deposit Crypto")
        addr = st.session_state.defi_manager.get_deposit_address()
        st.text_input("Your Deposit Address", value=addr, disabled=True)
        if addr and not addr.startswith("⚠️"):
            img = generate_qr_image(addr)
            if img:
                buf = BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), width=200)
        else:
            st.warning(addr)

    with tab_bal:
        st.header("📊 Balances")
        if not st.session_state.defi_manager.address:
            st.info("Load a private key to view balances.")
        else:
            native_bal = st.session_state.defi_manager.native_balance(nc)
            st.metric(label=f"{nc.name} Native Balance", value=f"{native_bal:.6f}")
            st.subheader("Jetton Balances" if st.session_state.defi_manager.current_chain == 'ton' else "ERC-20 Token Balances")
            placeholder_text = "EQ...\nEQ..." if st.session_state.defi_manager.current_chain == 'ton' else "0xToken...\n0xToken2..."
            token_list = st.text_area("Enter token addresses (one per line)", value="", placeholder=placeholder_text)
            if st.button("Check Token Balances"):
                if token_list.strip():
                    for line in token_list.strip().splitlines():
                        addr = line.strip()
                        try:
                            bal = st.session_state.defi_manager.erc20_balance(nc, addr)
                            st.write(f"{addr}: {bal}")
                        except Exception as e:
                            st.write(f"{addr}: error {e}")
                else:
                    st.info("Add token addresses to check balances.")

# 4. WALLET & EXECUTION
elif page_nav == "Wallet & Execution":
    neon_header("Wallet & Execution", level=2)
    
    tab_wallets, tab_cex, tab_funds = st.tabs(["🔐 Web3 Wallets", "🏦 Exchange Keys", "💰 Add Funds"])
    
    # --- WEB3 WALLETS ---
    with tab_wallets:
        st.markdown("### Manage Private Keys")
        st.info("Keys are encrypted securely using AES-256. They never leave your device.")
        
        # List Existing Wallets
        wallets = st.session_state.auth_manager.get_user_wallets(st.session_state.username)
        if wallets:
            st.write("Saved Wallets:")
            for w in wallets:
                with st.expander(f"{w['address'][:8]}...{w['address'][-6:]} ({w.get('chain_id', 'Unknown')})"):
                    st.text(f"Full Address: {w['address']}")
                    if st.button("Connect This Wallet", key=f"btn_conn_{w['address']}"):
                        # Load and Connect
                        pk = st.session_state.auth_manager.get_private_key(st.session_state.username, w['address'])
                        if pk:
                            st.session_state.web3_wallet.connect(pk, chain_id=w.get('chain_id', '1'))
                            st.success(f"Connected to {w['address']}")
                            st.rerun()
                        else:
                            st.error("Failed to decrypt key.")
        else:
            st.info("No wallets saved yet.")
            
        st.divider()
        st.markdown("#### Import New Wallet")
        with st.form("import_wallet_form"):
            new_pk = st.text_input("Private Key", type="password", placeholder="0x... or Base58...")
            chain_options = ['1', '56', '137', 'solana', 'ton', 'bitcoin']
            chain_labels = ['Ethereum', 'BNB Chain', 'Polygon', 'Solana', 'TON', 'Bitcoin']
            chain_idx = st.selectbox("Network", options=chain_options, format_func=lambda x: chain_labels[chain_options.index(x)])
            
            submitted = st.form_submit_button("Import & Encrypt")
            if submitted:
                if len(new_pk) < 10:
                    st.error("Invalid Private Key")
                else:
                    # Verify by connecting first
                    temp_wallet = Web3Wallet()
                    if temp_wallet.connect(new_pk, chain_id=chain_idx):
                        addr = temp_wallet.address
                        if st.session_state.auth_manager.save_private_key(st.session_state.username, addr, new_pk, chain_idx):
                            st.success(f"Wallet {addr} imported successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to save wallet.")
                    else:
                        st.error("Could not derive address from key. Check format.")

    # --- EXCHANGE KEYS ---
    with tab_cex:
        st.markdown("### Exchange API Keys")
        st.info("API Keys are encrypted locally. Enable 'Spot Trading' permission.")
        
        exchanges = ['binance', 'coinbase', 'kraken', 'kucoin', 'bybit']
        selected_ex = st.selectbox("Select Exchange", exchanges)
        
        # Check if exists
        curr_key, curr_secret = st.session_state.auth_manager.get_api_keys(st.session_state.username, selected_ex)
        if curr_key:
            st.success(f"✅ Credentials found for {selected_ex.title()}")
            if st.button("Delete Credentials"):
                st.session_state.auth_manager.delete_api_keys(st.session_state.username, selected_ex)
                st.rerun()
        
        with st.form("cex_keys_form"):
            api_key = st.text_input("API Key", type="password")
            api_secret = st.text_input("API Secret", type="password")
            
            if st.form_submit_button("Save Credentials"):
                if st.session_state.auth_manager.save_api_keys(st.session_state.username, selected_ex, api_key, api_secret):
                    st.success("Credentials Encrypted & Saved!")
                    
                    # Auto-connect
                    bot = get_bot(selected_ex)
                    bot.data_manager.update_credentials(api_key, api_secret)
                    st.session_state.exchange_connected = True
                    st.rerun()
                else:
                    st.error("Failed to save.")

    # --- ADD FUNDS ---
    with tab_funds:
        st.markdown("### 📥 Deposit Funds")
        
        fund_source = st.radio("Select Source", ["Web3 Wallet (Self-Custody)", "Exchange Account"], horizontal=True)
        
        if fund_source == "Web3 Wallet (Self-Custody)":
            if st.session_state.web3_wallet.connected:
                addr = st.session_state.web3_wallet.address
                st.markdown(f"#### Deposit Address ({st.session_state.web3_wallet.chain_id})")
                st.code(addr)
                
                # QR Code
                img = generate_qr_image(addr)
                if img:
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), width=250)
                
                st.info("Send funds to this address to start trading.")
            else:
                st.warning("Please connect a wallet in the 'Web3 Wallets' tab first.")
                
        else:
            st.markdown("#### Exchange Deposit")
            st.info("To add funds to your Exchange account, please visit the exchange directly.")
            st.markdown(f"**Current Exchange:** {st.session_state.exchange.title()}")
            st.markdown("[Open Binance](https://www.binance.com/en/my/wallet/account/main/deposit)")
            st.markdown("[Open Coinbase](https://www.coinbase.com/)")


# 5. PERFORMANCE ANALYTICS
elif page_nav == "Performance Analytics":
    neon_header("Performance Analytics", level=2)
    if st.session_state.logged_in:
        metrics = st.session_state.user_manager.get_performance_metrics()
        c1, c2, c3 = st.columns(3)
        with c1: metric_card("Total PnL", f"${metrics.get('total_pnl', 0):.2f}")
        with c2: metric_card("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
        with c3: metric_card("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
        
        st.divider()
        st.subheader("Trade History")
        # Trade History Table from Local DB
        try:
            bot = get_bot(st.session_state.exchange)
            if hasattr(bot, 'storage'):
                trades_df = bot.storage.get_trades(limit=50)
                if not trades_df.empty:
                    st.dataframe(trades_df, use_container_width=True)
                else:
                    st.info("No trades recorded locally yet.")
            else:
                st.warning("Storage manager not initialized.")
        except Exception as e:
            st.error(f"Failed to load trade history: {e}")

# 5. SYSTEM TARGETS
elif page_nav == "System Targets":
    neon_header("System Targets", level=2)
    target_min = TRADING_CONFIG['objectives']['target_apr_min'] * 100
    target_max = TRADING_CONFIG['objectives']['target_apr_max'] * 100
    metric_card("Target APR", f"{target_min:.0f}% - {target_max:.0f}%", color="#bd00ff")

# 6. WEB3 INTEGRATION
elif page_nav == "Web3 Integration":
    neon_header("Web3 Wallet")
    
    # --- Wallet Tools Section ---
    with st.expander("🛠️ Wallet Tools (Generator & Scanner)", expanded=False):
        st.markdown("### 🔐 Wallet Generator & Scanner")
        
        tab_gen, tab_scan = st.tabs(["Generate Wallet", "Multi-Chain Scanner"])
        
        with tab_gen:
            c_gen1, c_gen2 = st.columns([1, 1])
            with c_gen1:
                st.info("Generate a new multi-chain EVM wallet securely locally.")
                if st.button("Generate New Wallet", type="primary", use_container_width=True):
                    new_wallet = st.session_state.web3_wallet.generate_wallet()
                    st.session_state.generated_wallet = new_wallet
                    st.success("Wallet Generated!")
            
            if 'generated_wallet' in st.session_state:
                gw = st.session_state.generated_wallet
                st.divider()
                st.markdown("#### 📜 Wallet Details")
                st.text_input("Public Address", value=gw['address'], key="gen_addr_disp")
                
                # Private Key Visibility Toggle
                if st.checkbox("Show Private Key", key="show_pk_gen"):
                    st.text_input("Private Key", value=gw['private_key'], key="gen_pk_disp")
                    st.warning("⚠️ SAVE THIS KEY NOW! It is not stored anywhere else.")
                
                # QR Code
                st.markdown("#### 📱 QR Code")
                qr_bytes = st.session_state.web3_wallet.generate_qr_code(gw['address'])
                if qr_bytes:
                    # Convert bytes to base64 for display
                    b64_qr = base64.b64encode(qr_bytes).decode()
                    st.markdown(f'<img src="data:image/png;base64,{b64_qr}" alt="Wallet QR" style="border-radius: 10px; border: 2px solid #00f2ff;">', unsafe_allow_html=True)

        with tab_scan:
            st.markdown("#### 🔍 Multi-Chain Balance Scanner")
            scan_addr = st.text_input("Enter Address to Scan", value=st.session_state.web3_wallet.address if st.session_state.web3_wallet.address else "")
            
            if st.button("Scan All Chains"):
                if not scan_addr:
                    st.error("Please enter an address.")
                else:
                    with st.spinner("Scanning blockchains..."):
                        results = st.session_state.web3_wallet.scan_all_balances(scan_addr)
                        st.session_state.scan_results = results
            
            if 'scan_results' in st.session_state:
                st.divider()
                st.markdown("##### Native Balances")
                
                # Format as grid
                res = st.session_state.scan_results
                cols = st.columns(4)
                idx = 0
                for chain, bal in res.items():
                    with cols[idx % 4]:
                        st.metric(chain, bal)
                    idx += 1
                
                st.divider()
                # TRC-20 Check
                st.markdown("##### Tron Network (TRC-20)")
                c_tron1, c_tron2 = st.columns([3, 1])
                with c_tron1:
                    tron_addr = st.text_input("Tron Address (T...)", placeholder="Enter Tron address for TRC-20 scan")
                with c_tron2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Check TRC-20"):
                         if tron_addr.startswith("T"):
                             with st.spinner("Checking Tron Network..."):
                                 trc_bal = st.session_state.web3_wallet.get_trc20_balance(tron_addr)
                                 st.success(f"USDT Balance: {trc_bal}")
                         else:
                             st.warning("Invalid Tron Address")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Telegram Ecosystem
    st.markdown("### 💎 Telegram Ecosystem")
    st.info("🚀 Recommended for TON Users")
    
    if st.button("CONNECT TELEGRAM WALLET", use_container_width=True, type="primary"):
        st.session_state.show_ton_modal = True
        
    if st.session_state.get('show_ton_modal', False):
        # Direct Address Input for TON
        st.markdown("#### Connect Manually")
        ton_addr = st.text_input("Enter TON Wallet Address", placeholder="EQD...")
        
        c_ton1, c_ton2 = st.columns(2)
        with c_ton1:
             if st.button("Connect Address", key="btn_connect_ton_addr", use_container_width=True):
                 if ton_addr:
                     st.session_state.web3_wallet.connect(ton_addr, 'ton', 'Telegram Wallet')
                     st.success("Connected to Telegram Wallet")
                     st.rerun()
                 else:
                     st.warning("Please enter an address.")
                     
        with c_ton2:
            if st.button("Simulate Connection", key="btn_sim_ton", use_container_width=True):
                st.session_state.web3_wallet.connect("EQD4...SimulatedTONAddress", 'ton', 'Telegram Wallet')
                st.success("Connected to Telegram Wallet")
                st.rerun()
        
        st.divider()
        st.caption("Or scan with Tonkeeper (Integration Coming Soon)")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Exchange Connection Section
    st.markdown('<div style="background: linear-gradient(90deg, #10b981, #059669); padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 20px;"><span style="font-weight: bold; color: white;">🔗 Exchange Connection (API Keys)</span></div>', unsafe_allow_html=True)
    
    with st.expander("🔑 Manage Exchange API Keys", expanded=False):
        with st.form("api_key_form"):
            c_ex, c_ak, c_as = st.columns([1, 2, 2])
            with c_ex:
                ex_select = st.selectbox("Exchange", ["binance", "coinbase", "kraken", "kucoin", "bybit", "okx"])
            with c_ak:
                api_key_input = st.text_input("API Key", type="password")
            with c_as:
                api_secret_input = st.text_input("API Secret", type="password")
            
            if st.form_submit_button("Save API Keys"):
                if st.session_state.get('logged_in') and st.session_state.get('username'):
                    success = st.session_state.auth_manager.save_api_keys(st.session_state.username, ex_select, api_key_input, api_secret_input)
                    if success:
                        st.success(f"✅ API Keys for {ex_select} saved securely.")
                        # Auto-inject if current bot exchange matches
                        if st.session_state.get('exchange') == ex_select:
                             bot = get_bot(ex_select)
                             bot.initialize_credentials(st.session_state.username)
                    else:
                        st.error("Failed to save keys. User not found.")
                else:
                    st.error("Please login to save keys.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Connect Wallet Section
    st.markdown('<div style="background: linear-gradient(90deg, #00f2ff, #2563eb); padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 20px;"><span style="font-weight: bold; color: white;">📍 Connect Wallet</span></div>', unsafe_allow_html=True)
    
    # Ensure Tron name is updated (Hot-fix)
    if st.session_state.web3_wallet.CHAINS.get('tron', {}).get('name') == 'Tron':
        st.session_state.web3_wallet.CHAINS['tron']['name'] = 'Tron Network (TRC-20)'
    
    if st.session_state.web3_wallet.is_connected():
         chain_info = st.session_state.web3_wallet.CHAINS.get(st.session_state.web3_wallet.chain_id, {})
         chain_name = chain_info.get('name', 'Unknown Chain')
         st.success(f"✅ Connected: {st.session_state.web3_wallet.address} ({chain_name})")
         
         # Show Balance (Cached)
         if 'web3_balance' not in st.session_state:
             st.session_state.web3_balance = st.session_state.web3_wallet.get_balance()
             
         balance = st.session_state.web3_balance
         symbol = chain_info.get('symbol', 'ETH')
         metric_card("Wallet Balance", f"{balance:.4f} {symbol}")
         
         # --- Sync with Trading Bot (Auto-Inject Balance) ---
         # Use new Portfolio Value Logic
         capital_usd = 0.0
         try:
             capital_usd = st.session_state.web3_wallet.get_portfolio_value_usd()
         except:
             pass
             
         # Fallback estimation if portfolio calc returned 0 but we have native balance
         if capital_usd == 0 and balance > 0:
             bot = get_bot(st.session_state.get('exchange', 'binance'))
             usd_price = 1.0 
             try:
                 ticker = f"{symbol}/USDT"
                 live_price = get_cached_price(bot, ticker)
                 if live_price and live_price > 0:
                     usd_price = live_price
                 else:
                     usd_price = 0.0
             except:
                 usd_price = 0.0
             capital_usd = balance * usd_price

         # Always get bot instance for subsequent sections
         bot = get_bot(st.session_state.get('exchange', 'binance'))
         
         if capital_usd > 0:
             bot.risk_manager.update_live_balance(capital_usd)
             st.caption(f"✅ Trading Capital Synced: ${capital_usd:,.2f}")
         # ---------------------------------------------------
        
         # --- Deposit / Add Funds Section ---
         st.markdown("### 💰 Add Funds")
        
         # 1. Fiat / NGN Option
         with st.container():
             st.markdown("#### 🇳🇬 Fiat (NGN) / Bank Transfer")
            
             # Check Fiat Balance
             ngn_bal = 0.0
             if hasattr(bot, 'fiat'):
                 ngn_bal = bot.fiat.fiat_balance
             elif hasattr(bot, 'storage'):
                 ngn_bal = float(bot.storage.get_setting("fiat_balance_ngn", 0.0))
            
             c_f1, c_f2 = st.columns([1, 2])
             with c_f1:
                 metric_card("NGN Balance", f"₦{ngn_bal:,.2f}", color="#00ff9d")
             with c_f2:
                 st.info("Deposit NGN via Bank Transfer or Card, then Swap to USDT for trading.")
                 st.markdown("**Navigate to 'Fiat Gateway (NGN)' in the sidebar to Deposit or Verify Transaction.**")

         st.divider()

         # 2. Crypto Option
         with st.expander("📥 Crypto Deposit (Web3 Address)", expanded=True):
              st.markdown("### Deposit Address")
              st.markdown("Send funds to this address to top up your bot wallet:")
              st.code(st.session_state.web3_wallet.address, language="text")
             
              c_info = st.session_state.web3_wallet.CHAINS.get(st.session_state.web3_wallet.chain_id, {})
              net_name = c_info.get('name', 'Unknown Network')
              sym = c_info.get('symbol', 'ETH')
             
              st.info(f"**Network:** {net_name}\\n\\nEnsure you are sending **{sym}** (or supported tokens) on the **{net_name}** blockchain.")
             
              if st.session_state.web3_wallet.chain_id == 'ton':
                  st.warning("⚠️ For TON: No Memo is required for this non-custodial wallet.")

         c_w1, c_w2 = st.columns(2)
         with c_w1:
             if st.button("Refresh Balance", use_container_width=True):
                 st.session_state.web3_balance = st.session_state.web3_wallet.get_balance()
                 st.rerun()
         with c_w2:
             if st.button("Disconnect", use_container_width=True):
                 st.session_state.web3_wallet.disconnect()
                 if 'web3_balance' in st.session_state:
                     del st.session_state.web3_balance
                 st.rerun()
    else:
        # Connection Modal State
        if 'connect_modal' not in st.session_state:
            st.session_state.connect_modal = None

        if st.session_state.connect_modal:
            target_wallet = st.session_state.connect_modal
            st.info(f"Connecting to {target_wallet}...")
            
            with st.form("wallet_connect_form"):
                st.write(f"Enter your {target_wallet} details:")
                
                # Determine default chain based on wallet
                default_chain = '1'
                if 'Phantom' in target_wallet: default_chain = 'solana'
                elif 'TON' in target_wallet: default_chain = 'ton'
                elif 'Keplr' in target_wallet: default_chain = 'cosmos'
                elif 'Trust' in target_wallet: default_chain = '56' # BNB
                elif 'Bitcoin' in target_wallet: default_chain = 'bitcoin'
                elif 'Litecoin' in target_wallet: default_chain = 'litecoin'
                elif 'Dogecoin' in target_wallet: default_chain = 'dogecoin'
                elif 'Tron' in target_wallet: default_chain = 'tron'
                
                # Allow chain selection for some
                if target_wallet in ['MetaMask', 'Coinbase', 'Trust Wallet', 'OKX Wallet', 'WalletConnect', 'Other / Custom']:
                    chain_options = {k: v['name'] for k, v in st.session_state.web3_wallet.CHAINS.items()}
                    # Sort by name
                    sorted_chains = sorted(chain_options.items(), key=lambda x: x[1])
                    selected_chain_id = st.selectbox("Select Network", [x[0] for x in sorted_chains], format_func=lambda x: chain_options[x], index=[x[0] for x in sorted_chains].index(default_chain) if default_chain in [x[0] for x in sorted_chains] else 0)
                else:
                    selected_chain_id = default_chain
                    st.caption(f"Network: {st.session_state.web3_wallet.CHAINS.get(default_chain, {}).get('name', default_chain)}")

                # Custom UI Component for Private Key Entry (User Requested Style)
                st.markdown("""
                <div class="wallet-panel" style="background-color: #111827; padding: 1.5rem; border-radius: 0.5rem; border: 1px solid #374151; margin-bottom: 5px;">
                   <h3 style="font-size: 1.125rem; font-weight: 700; color: #4ade80; margin: 0 0 10px 0;">🔐 Manual Private Key Entry</h3> 
                   <p style="font-size: 0.875rem; color: #d1d5db; margin-bottom: 5px;">Enter your private key securely below. It is used locally for signing only.</p>
                </div>
                """, unsafe_allow_html=True)

                addr_input = st.text_input("Private Key", type="password", label_visibility="collapsed", placeholder="0x... (Private Key)", key="pk_input_field")
                
                st.markdown("""
                <p style="font-size: 0.75rem; color: #ef4444; margin-top: 5px; margin-bottom: 15px;">
                 ⚠️ Never share your private key. It will only be used locally for signing transactions.
                </p>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("Save & Connect", type="primary", use_container_width=True):
                        if addr_input:
                            success = st.session_state.web3_wallet.connect(addr_input, selected_chain_id, target_wallet)
                            if success:
                                st.session_state.web3_balance = st.session_state.web3_wallet.get_balance()
                                st.session_state.connect_modal = None
                                st.rerun()
                            else:
                                st.error("Connection Failed. Invalid Address/Key.")
                        else:
                            st.warning("Input required.")
                with c2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.connect_modal = None
                        st.rerun()

                st.markdown("""
                <p style="font-size: 0.75rem; color: #f87171; margin-top: 0.5rem;"> 
                   ⚠️ Never share your private key. It will only be used locally for signing transactions. 
                </p>
                """, unsafe_allow_html=True)

        else:
            # Wallet Grid
            w_col1, w_col2 = st.columns(2)
            
            with w_col1:
                if st.button("🦊 MetaMask", use_container_width=True):
                    st.session_state.connect_modal = "MetaMask"
                    st.rerun()
                if st.button("🔵 Coinbase", use_container_width=True):
                    st.session_state.connect_modal = "Coinbase"
                    st.rerun()
                if st.button("👻 Phantom (SOL)", use_container_width=True):
                    st.session_state.connect_modal = "Phantom"
                    st.rerun()
                if st.button("💎 TON Wallet", use_container_width=True):
                    st.session_state.connect_modal = "TON Wallet"
                    st.rerun()
                if st.button("🔴 TronLink (TRX)", use_container_width=True):
                    st.session_state.connect_modal = "TronLink (TRX)"
                    st.rerun()
                if st.button("🔗 WalletConnect", use_container_width=True):
                    st.session_state.connect_modal = "WalletConnect"
                    st.rerun()
                
            with w_col2:
                if st.button("🛡️ Trust Wallet", use_container_width=True):
                    st.session_state.connect_modal = "Trust Wallet"
                    st.rerun()
                if st.button("⚫ OKX Wallet", use_container_width=True):
                    st.session_state.connect_modal = "OKX Wallet"
                    st.rerun()
                if st.button("🪐 Keplr (Cosmos)", use_container_width=True):
                    st.session_state.connect_modal = "Keplr"
                    st.rerun()
                if st.button("🌐 Browser Wallet", use_container_width=True):
                    st.session_state.connect_modal = "Browser Wallet"
                    st.rerun()
                if st.button("🔒 Hardware (Ledger)", use_container_width=True):
                    st.session_state.connect_modal = "Hardware Wallet"
                    st.rerun()
                
            if st.button("➕ Other / Custom", use_container_width=True):
                st.session_state.connect_modal = "Other / Custom"
                st.rerun()

# --- DEFI STAKING MODULE ---
elif page_nav == "DeFi Staking":
    neon_header("💎 DeFi Staking Pools")
    
    st.markdown("""
    <div style='background: rgba(0, 242, 255, 0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(0, 242, 255, 0.2); margin-bottom: 20px;'>
        <h4 style='margin:0; color: #00f2ff;'>ERC20 Staking Manager</h4>
        <p style='margin:5px 0 0 0; font-size: 0.9rem; color: #a0aec0;'>Deploy and manage your own staking pools. Users stake tokens to earn rewards over time.</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab_deploy, tab_interact = st.tabs(["🚀 Deploy New Pool", "🎛️ Manage & Interact"])
    
    with tab_deploy:
        st.subheader("Deploy Staking Contract")
        
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            stake_token = st.text_input("Staking Token Address (ERC20)", placeholder="0x...")
        with c_d2:
            reward_token = st.text_input("Reward Token Address (ERC20)", placeholder="0x...")
            
        reward_rate = st.number_input("Initial Reward Rate (Tokens/Second)", min_value=0.0, value=1.0, step=0.1)
        
        if st.button("Deploy Contract", type="primary"):
            if not stake_token or not reward_token:
                st.warning("Please enter both token addresses.")
            else:
                with st.spinner("Compiling & Deploying..."):
                    # Simulation for UI demo
                    time.sleep(2)
                    st.info("ℹ️ Real contract deployment requires an active signer and gas. This is a preview.")
                    # st.success("✅ Contract Deployed Successfully!")
                    # st.balloons()
                    
                    # mock_addr = "0x" + os.urandom(20).hex()
                    # st.code(mock_addr, language="text")
                    # st.caption("Copy this address to manage the pool in the next tab.")
                    
                    # Store in session for convenience
                    # st.session_state.last_deployed_pool = mock_addr
                    
    with tab_interact:
        st.subheader("Pool Interaction")
        
        pool_addr = st.text_input("Staking Pool Contract Address", value=st.session_state.get('last_deployed_pool', ''), placeholder="0x...")
        
        if pool_addr:
            # Connect if needed
            if 'defi_mgr' not in st.session_state:
                st.session_state.defi_mgr = DeFiManager()
                st.session_state.defi_mgr.connect_to_chain('ethereum') # Default

            # Fetch Stats
            stats = st.session_state.defi_mgr.get_pool_stats(pool_addr)
            
            st.markdown("### 📊 Pool Statistics")
            c_s1, c_s2, c_s3 = st.columns(3)
            c_s1.metric("Total Staked", f"{stats.get('total_staked', 0):,.2f}")
            c_s2.metric("APY", f"{stats.get('apy', 0):.2f}%")
            c_s3.metric("My Stake", f"{stats.get('my_stake', 0):,.2f}")
            
            st.divider()
            
            c_i1, c_i2, c_i3 = st.columns(3)
            
            with c_i1:
                st.markdown("#### Stake")
                stake_amt = st.number_input("Amount", key="stake_amt")
                stake_token_addr = st.text_input("Stake Token (ERC20)", key="stake_token_addr", placeholder="0x...")
                if st.button("Stake Tokens"):
                    # Force Reload if method missing
                    if 'defi_mgr' not in st.session_state or not hasattr(st.session_state.defi_mgr, 'stake_in_pool'):
                        st.session_state.defi_mgr = DeFiManager()
                        st.session_state.defi_mgr.connect_to_chain('ethereum')
                        
                    res = st.session_state.defi_mgr.stake_in_pool(pool_addr, stake_token_addr, float(stake_amt))
                    if res.get('status') == 'success':
                        st.success(f"Tx: {res.get('tx_hash')}")
                    else:
                        st.error(res.get('error','Failed'))
            
            with c_i2:
                st.markdown("#### Withdraw")
                withdraw_amt = st.number_input("Amount", key="withdraw_amt")
                stake_token_addr2 = st.text_input("Stake Token (ERC20)", key="stake_token_addr2", placeholder="0x...")
                if st.button("Withdraw Stake"):
                     # Force Reload if method missing
                     if 'defi_mgr' not in st.session_state or not hasattr(st.session_state.defi_mgr, 'withdraw_from_pool'):
                         st.session_state.defi_mgr = DeFiManager()
                         st.session_state.defi_mgr.connect_to_chain('ethereum')
                         
                     res = st.session_state.defi_mgr.withdraw_from_pool(pool_addr, float(withdraw_amt), stake_token_addr2)
                     if res.get('status') == 'success':
                         st.success(f"Tx: {res.get('tx_hash')}")
                     else:
                         st.error(res.get('error','Failed'))
                     
            with c_i3:
                st.markdown("#### Rewards")
                if st.button("Claim Rewards", type="primary"):
                    # Force Reload if method missing
                    if 'defi_mgr' not in st.session_state or not hasattr(st.session_state.defi_mgr, 'claim_rewards'):
                        st.session_state.defi_mgr = DeFiManager()
                        st.session_state.defi_mgr.connect_to_chain('ethereum')
                        
                    try:
                        tx = st.session_state.defi_mgr.claim_rewards(pool_addr)
                        if tx.get('status') == 'success':
                            st.success(f"Tx: {tx.get('tx_hash')}")
                        else:
                            st.error(tx.get('error','Failed'))
                    except Exception as e:
                        st.error(str(e))

# 5. FIAT GATEWAY (NGN)
elif page_nav == "Fiat Gateway (NGN)":
    neon_header("Fiat Gateway (NGN)", level=2)
    bot = get_bot(exchange)
    
    # Ensure FiatManager is available
    if not hasattr(bot, 'fiat'):
        from core.fiat.fiat_manager import FiatManager
        bot.fiat = FiatManager(bot)
    
    fiat_mgr = bot.fiat
    
    # --- Active Provider Selection ---
    col_prov1, col_prov2 = st.columns([3, 1])
    with col_prov1:
        st.metric("NGN Balance", f"₦{fiat_mgr.fiat_balance:,.2f}")
    with col_prov2:
        current_prov = fiat_mgr.provider
        # Enforce Flutterwave only
        selected_prov = st.selectbox("Active Provider", ["flutterwave"], index=0, key="active_prov_sel", disabled=True)
        
        if selected_prov != current_prov and selected_prov == 'flutterwave':
            username = st.session_state.get('username')
            fiat_mgr.initialize_adapter(username, provider_override=selected_prov)
            st.success(f"Switched to {selected_prov}")
            time.sleep(0.5)
            st.rerun()

    # --- Compliance Info ---
    if hasattr(fiat_mgr, 'compliance'):
        # Just use generic tier 1 for now or username
        username = st.session_state.get('username', 'user')
        tier = fiat_mgr.compliance.get_user_tier(username)
        tier_info = fiat_mgr.compliance.TIERS[tier]
        
        # Display Compliance Status in a nice card
        st.markdown("---")
        c_k1, c_k2, c_k3 = st.columns(3)
        c_k1.info(f"🛡️ **KYC Tier: {tier}**")
        c_k2.metric("Daily Limit", f"₦{tier_info['daily_limit']:,.2f}")
        c_k3.metric("Single Tx Limit", f"₦{tier_info['single_limit']:,.2f}")
        
        with st.expander("View Requirements"):
             st.write(f"**Current Requirement:** {tier_info['req']}")
             st.write("To upgrade your tier, please contact support with your ID documents.")

    # --- Configuration Section ---
    with st.expander("⚙️ Payment Provider Keys", expanded=False):
        st.info("Update API Keys for the selected provider.")
        
        pk_input = st.text_input("Public Key", type="password", key="fiat_pk")
        sk_input = st.text_input("Secret Key", type="password", key="fiat_sk")
        enc_input = st.text_input("Encryption Key (Optional)", type="password", key="fiat_enc")
        
        if st.button("Save Keys"):
            username = st.session_state.get('username')
            if username:
                success = bot.auth_manager.save_api_keys(username, selected_prov, pk_input, sk_input, encryption_key=enc_input)
                if success:
                    st.success(f"Keys for {selected_prov} saved securely!")
                    # Reload adapter
                    fiat_mgr.initialize_adapter(username, provider_override=selected_prov)
                else:
                    st.error("Failed to save keys.")
            else:
                st.error("You must be logged in to save keys.")
    
    tab_dep, tab_wd, tab_swap, tab_hist = st.tabs(["Deposit (Inbound)", "Withdraw (Outbound)", "Swap (NGN <-> Crypto)", "Transaction History"])
    
    with tab_dep:
        st.subheader("Fund Your Account")
        with st.form("deposit_form"):
            amount = st.number_input("Amount (NGN)", min_value=100.0, step=100.0, value=5000.0)
            email = st.text_input("Email Address", placeholder="user@example.com", value=st.session_state.get('username', '') + "@example.com" if st.session_state.get('username') else "")
            submit_dep = st.form_submit_button("Initiate Deposit")
            
            if submit_dep:
                if amount < 100:
                    st.error("Minimum deposit is ₦100")
                elif not email:
                    st.error("Email is required")
                else:
                    with st.spinner("Creating Payment Link..."):
                        res = fiat_mgr.initiate_deposit(amount, email)
                        if res.get('status') == 'success':
                            st.success("Deposit Initiated!")
                            st.markdown(f"**Reference:** `{res.get('reference')}`")
                            st.markdown(f"### [Click here to Pay]({res.get('authorization_url')})")
                            st.info("After payment, click the button below to verify.")
                            
                            # Store reference in session state to persist button
                            st.session_state['last_deposit_ref'] = res.get('reference')
                        else:
                            st.error(f"Error: {res.get('message')}")
        
        # Verify Button (Outside Form)
        dep_ref = st.text_input("Transaction Reference", value=st.session_state.get('last_deposit_ref', ''))
        if st.button("Verify Payment Status"):
            if dep_ref:
                with st.spinner("Verifying with Provider..."):
                    v_res = fiat_mgr.verify_deposit(dep_ref)
                    if v_res.get('status') == 'success':
                        st.balloons()
                        st.success(f"Payment Confirmed! Balance Updated: ₦{v_res.get('new_balance'):,.2f}")
                        if 'last_deposit_ref' in st.session_state:
                             del st.session_state['last_deposit_ref']
                    elif v_res.get('status') == 'pending':
                         st.warning("Payment is still pending. Please complete the payment in the browser tab.")
                    else:
                        st.error(f"Verification Failed: {v_res.get('message')}")
            else:
                st.warning("Enter a reference to verify.")

    with tab_wd:
        st.subheader("Withdraw to Bank / Flutterwave")
        st.caption("Transfer funds to any Nigerian Bank Account or Flutterwave Wallet (via Bank Code)")
        
        # Fetch Banks
        banks = get_cached_banks(fiat_mgr)
        bank_options = {f"{b['name']} ({b['code']})": b['code'] for b in banks}
        
        # 1. Manual Withdrawal / Error Recovery UI (Rendered FIRST if active)
        if 'wd_error_state' in st.session_state:
            err = st.session_state['wd_error_state']
            # Only show if recent (within 5 mins)
            if time.time() - err['ts'] < 300:
                st.error(f"API Error: {err['msg']}")
                st.warning("⚠️ API Withdrawal Failed. You can record this manually if you process it yourself.")
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    if st.button("📝 Record Manual Withdrawal (Force Deduct)"):
                        amount = err['amount']
                        fiat_mgr.fiat_balance -= amount
                        if hasattr(bot, 'storage'):
                            bot.storage.save_setting("fiat_balance_ngn", fiat_mgr.fiat_balance)
                            bot.storage.save_fiat_transaction(
                                f"manual_{int(time.time())}", 'withdrawal', amount, 'NGN', 'success', 
                                details={"note": "Manual processing due to API failure", "error": err['msg']}
                            )
                        st.success(f"Balance updated! Please transfer ₦{amount:,.2f} manually via your Banking App.")
                        del st.session_state['wd_error_state']
                        time.sleep(2)
                        st.rerun()
                
                with col_m2:
                    if st.button("Cancel / Clear"):
                        del st.session_state['wd_error_state']
                        st.rerun()
                
                st.divider() # Separator
            else:
                del st.session_state['wd_error_state']
        
        # 2. Withdrawal Form
        with st.form("withdraw_form"):
            wd_amount = st.number_input("Amount (NGN)", min_value=100.0, step=100.0, value=1000.0)
            
            if bank_options:
                selected_bank_label = st.selectbox("Select Bank", list(bank_options.keys()))
                bank_code = bank_options[selected_bank_label]
            else:
                bank_code = st.text_input("Bank Code (e.g., 057 for GTBank)")
                
            account_number = st.text_input("Account Number")
            account_name = st.text_input("Account Name (Optional - to skip auto-resolve)", help="Enter exact account name if auto-resolution fails.")
            
            submit_wd = st.form_submit_button("Initiate Withdrawal")
            
        if submit_wd:
            if wd_amount > fiat_mgr.fiat_balance:
                st.error("Insufficient Funds")
            elif not bank_code or not account_number:
                st.error("Bank details required")
            else:
                with st.spinner("Processing Withdrawal..."):
                    res = fiat_mgr.initiate_withdrawal(wd_amount, bank_code, account_number, account_name=account_name if account_name else None)
                    
                    if res.get('status') == 'success' or res.get('status') == 'pending':
                        st.success("Withdrawal Queued!")
                        st.markdown(f"**Reference:** `{res.get('reference')}`")
                        st.info(f"Status: {res.get('status_msg', 'Processing')}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        # Save error state to session and rerun to show UI
                        st.session_state['wd_error_state'] = {
                            "amount": wd_amount,
                            "msg": res.get('message'),
                            "ts": time.time()
                        }
                        st.rerun()
    
    with tab_swap:
        st.subheader("Swap (NGN <-> Crypto)")
        st.info("Instant conversion between your NGN Balance and USDT (CEX/DEX)")
        
        swap_mode = st.radio("Mode", ["Buy USDT (Spend NGN)", "Sell USDT (Receive NGN)"], horizontal=True)
        
        if swap_mode == "Buy USDT (Spend NGN)":
            ngn_in = st.number_input("Amount to Spend (NGN)", min_value=1000.0, step=500.0)
            
            # Fetch Quote
            quote = fiat_mgr.swap_manager.get_quote('NGN', 'USDT', ngn_in)
            if quote['status'] == 'success':
                st.metric("Estimated Received (USDT)", f"{quote['amount_out_net']:.2f}", help=f"Rate: {quote['rate']:.2f} | Fee: {quote['fee']:.2f}")
                
                if st.button("Confirm Buy USDT"):
                    with st.spinner("Executing Swap..."):
                        res = fiat_mgr.execute_swap('NGN', 'USDT', ngn_in)
                        
                        if res['status'] == 'success':
                            # Credit USDT (Real Wallet Only - No Mock)
                            st.success(f"Swapped ₦{ngn_in:,.2f} for {res['amount_out']:.2f} USDT!")
                            st.info("USDT credited to your Exchange Wallet.")
                            
                            # Update Real Balance (Bot's Live Trading Balance)
                            if hasattr(bot, 'risk_manager'):
                                current_bal = bot.risk_manager.live_balance
                                new_bal = current_bal + res['amount_out']
                                bot.risk_manager.update_live_balance(new_bal)
                                st.success(f"Live Trading Balance Updated: ${new_bal:,.2f}")
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Swap Failed: {res.get('message')}")
            else:
                st.error("Failed to fetch quote")
                    
        else: # Sell USDT
            usdt_in = st.number_input("Amount to Sell (USDT)", min_value=1.0, step=1.0)
            
            # Fetch Quote
            quote = fiat_mgr.swap_manager.get_quote('USDT', 'NGN', usdt_in)
            
            if quote['status'] == 'success':
                st.metric("Estimated Received (NGN)", f"₦{quote['amount_out_net']:,.2f}", help=f"Rate: {quote['rate']:.2f} | Fee: {quote['fee']:.2f}")
            
                if st.button("Confirm Sell USDT"):
                     # Check USDT Balance (Real Wallet Only)
                     # For now, we assume if they are selling, they have checked their exchange balance.
                     # We remove the Paper Wallet check.
                     
                     with st.spinner("Executing Swap..."):
                         # Execute Swap (Credits NGN automatically)
                         res = fiat_mgr.execute_swap('USDT', 'NGN', usdt_in)
                         
                         if res['status'] == 'success':
                             st.success(f"Swapped {usdt_in:.2f} USDT for ₦{res['amount_out']:,.2f}!")
                             time.sleep(1)
                             st.rerun()
                         else:
                             st.error(f"Swap Failed: {res.get('message')}")

        st.divider()
        st.subheader("Refund USDT Credit to NGN")
        current_credit = 0.0
        if hasattr(bot, 'storage'):
            try:
                current_credit = float(bot.storage.get_setting("virtual_usdt_credit_usd", 0.0) or 0.0)
            except Exception:
                pass
        st.caption(f"USDT Credit (stored): {current_credit:.2f}")
        col_rf1, col_rf2 = st.columns([1, 1])
        with col_rf1:
            refund_amt = st.number_input("Amount to Refund (USDT)", min_value=0.0, value=current_credit, step=0.5)
        with col_rf2:
            if st.button("Refund to NGN"):
                with st.spinner("Processing refund..."):
                    res = fiat_mgr.refund_usdt_credit_to_ngn(refund_amt)
                    if res.get('status') == 'success':
                        st.success(f"Refunded {res['amount_usd']:.2f} USDT -> ₦{res['ngn_amount']:,.2f}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Refund Failed: {res.get('message')}")

    with tab_hist:
        st.subheader("Recent Transactions")
        if hasattr(bot, 'storage'):
            txs = bot.storage.get_recent_fiat_transactions(limit=20)
            if txs:
                df_tx = pd.DataFrame(txs)
                st.dataframe(df_tx, use_container_width=True)
            else:
                st.info("No transactions found.")
        else:
            st.warning("Storage Manager not connected.")

# 7. OTHER LABS
elif page_nav in ["Arbitrage Scanner", "Copy Trading", "DeFi Bridge", "Quantum Lab", "Risk Manager", "Active Positions"]:
    neon_header(f"{page_nav}", level=2)
    if page_nav == "Arbitrage Scanner":
        bot = get_bot(exchange)
        # Use bot's arbitrage instance
        scanner = bot.arbitrage
        
        symbol_sel = st.text_input("Symbol", value=st.session_state.get('symbol', 'BTC/USDT'))
        col_a1, col_a2 = st.columns([1,1])
        with col_a1:
            start_live = st.toggle("Live Mode", value=st.session_state.get('arb_live', False))
            st.session_state.arb_live = start_live
        with col_a2:
            if st.button("Scan Now"):
                st.session_state.arb_last = time.time()
                st.rerun()
        
        holder = st.empty()
        prices_df = scanner.get_prices_df(symbol_sel)
        if not prices_df.empty:
            holder.dataframe(prices_df, use_container_width=True)
            
        opps = scanner.scan_opportunities(symbol_sel)
        if opps:
            st.markdown("### Top Opportunities")
            st.table(pd.DataFrame(opps))
        else:
            st.info("No arbitrage opportunities found currently.")
            
        if st.session_state.get('arb_live'):
            time.sleep(5)
            st.rerun()
    elif page_nav == "Copy Trading":
        # Initialize bot for session access (Required for Copy Trading execution)
        bot = get_bot(exchange)
        st.session_state.bot = bot
        
        if 'copy_mod' not in st.session_state:
            from core.copy_trading import CopyTradingModule
            st.session_state.copy_mod = CopyTradingModule()
        st.session_state.copy_mod.render_ui()
    elif page_nav == "DeFi Bridge":
        # Force reload if method missing (Fix for AttributeError during hot-reload)
        if 'defi_mgr' not in st.session_state or not hasattr(st.session_state.defi_mgr, 'bridge_assets'):
            st.session_state.defi_mgr = DeFiManager()
            st.session_state.defi_mgr.connect_to_chain(st.session_state.get('evm_chain', 'ethereum'))
            
        chains = list(DeFiManager.CHAINS.keys())
        src = st.selectbox("Source Chain", chains, index=chains.index(st.session_state.defi_mgr.current_chain) if st.session_state.defi_mgr.current_chain in chains else 0)
        tgt = st.selectbox("Target Chain", chains, index=chains.index('bsc') if 'bsc' in chains else 0)
        amt = st.number_input("Amount", min_value=0.0, value=10.0)
        if st.button("Bridge Assets", type="primary"):
            st.session_state.defi_mgr.connect_to_chain(src)
            res = st.session_state.defi_mgr.bridge_assets(tgt, amt)
            st.success(f"{res.get('status', 'pending')} | tx: {res.get('tx_hash', '')}")
    elif page_nav == "Quantum Lab":
        if 'quantum_engine' not in st.session_state:
            from core.quantum import QuantumEngine
            st.session_state.quantum_engine = QuantumEngine()
        qe = st.session_state.quantum_engine
        bot = get_bot(exchange)
        df = get_cached_ohlcv(bot, st.session_state.get('symbol','BTC/USDT'), st.session_state.get('timeframe','1h'))
        regime = qe.detect_regime_quantum(df) if isinstance(df, pd.DataFrame) else "Normal"
        st.metric("Regime", regime)
        if isinstance(df, pd.DataFrame) and not df.empty:
            last_price = df['close'].iloc[-1]
            vol = df['close'].pct_change().std() if len(df) > 30 else 0.02
            x, pdf = qe.calculate_probability_wave(last_price, float(vol), time_horizon=10)
            chart_df = pd.DataFrame({"price": x, "prob": pdf})
            st.line_chart(chart_df.set_index("price"))
        live_q = st.toggle("Live Mode", value=st.session_state.get('quantum_live', False))
        st.session_state.quantum_live = live_q
        if live_q:
            time.sleep(10)
            st.rerun()
    elif page_nav == "Risk Manager":
        bot = get_bot(exchange)
        rm = bot.risk_manager
        win_rate = st.slider("Win Rate (%)", 0, 100, int(rm.metrics['Demo'].get('win_streak',0)*5))
        avg_win = st.number_input("Avg Win ($)", value=50.0)
        avg_loss = st.number_input("Avg Loss ($)", value=-30.0)
        start_eq = st.number_input("Starting Equity ($)", value=rm.current_capital)
        if st.button("Run Monte Carlo"):
            m = rm.monte_carlo_simulator.run_simulation(win_rate/100.0, avg_win, avg_loss, start_eq)
            st.metric("Risk of Ruin (%)", f"{m['risk_of_ruin_pct']:.2f}")
            st.metric("Median Equity", f"{m['median_expected_equity']:.2f}")
            st.metric("Worst Case", f"{m['worst_case_equity']:.2f}")
            sims = pd.DataFrame(m['simulations'].T)
            st.line_chart(sims)

else:
    st.error("Module not found.")
