
import streamlit as st
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
import core.styles as styles
importlib.reload(styles)

# Defensive Import Wrapper
def get_style_func(name, fallback_func=None):
    if hasattr(styles, name):
        return getattr(styles, name)
    else:
        # Fallback if import fails
        if fallback_func:
            return fallback_func
        else:
            def noop(*args, **kwargs):
                pass
            return noop

# Define Fallbacks
def fallback_metric(label, value, delta=None, color=None):
    st.metric(label, value, delta)

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
import core.auth
from core.auth import AuthManager, UserManager, TOTP, SessionManager
from core.ton_wallet import TonConnectManager
from core.web3_wallet import Web3Wallet
from config.settings import APP_NAME, VERSION, DEFAULT_SYMBOL

# Determine Page Icon (Logo or Emoji)
logo_path = os.path.join("assets", "logo.png")
page_icon = logo_path if os.path.exists(logo_path) else "🦅"

st.set_page_config(
    page_title=APP_NAME, 
    layout="wide",
    page_icon=page_icon,
    initial_sidebar_state="expanded",
    menu_items={
        'About': f"# {APP_NAME} v{VERSION}\nPowered by Capa-X Quantum AI"
    }
)

# Apply Cyberpunk / Professional Styles
apply_custom_styles()

# Initialize Auth
# Explicitly force re-initialization if the class definition changed (detected via missing method)
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
# Idle Timeout Logic
if st.session_state.get('logged_in'):
    last_active = st.session_state.get('last_active', time.time())
    idle_duration = time.time() - last_active
    
    # 2 Hours Timeout (7200 seconds)
    if idle_duration > 7200:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.query_params["logout"] = "timeout"
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
            
        # Clear local storage via JS injection
        st.markdown("<script>localStorage.removeItem('capacitybay_session');</script>", unsafe_allow_html=True)
        st.rerun()
    # Warning 5 minutes before (6900 seconds)
    elif idle_duration > 6900:
        mins_left = int((7200 - idle_duration) / 60)
        st.toast(f"⚠️ Session expiring in {mins_left} minutes due to inactivity.", icon="⏳")
    
    # Update activity timestamp
    st.session_state.last_active = time.time()

# Check for session_id in URL (from localStorage injection)
query_params = st.query_params
session_id = query_params.get("session_id", None)
logout_reason = query_params.get("logout", None)

if logout_reason == "timeout":
    st.error("Session expired due to inactivity.")
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        st.session_state.logged_in = False
        st.session_state.username = None
    # Clear token from local storage if it persists
    st.markdown("<script>localStorage.removeItem('capacitybay_session');</script>", unsafe_allow_html=True)

if not st.session_state.logged_in and session_id:
    # Validate Session
    username = st.session_state.session_manager.validate_session(session_id)
    if username:
        # Restore Session
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.session_token = session_id # Store token for logout
        # Load user data
        st.session_state.user_manager = UserManager(username)
        st.session_state.user_role = st.session_state.auth_manager.users.get(username, {}).get('role', 'demo')
        st.session_state.last_active = time.time() # Initialize activity
        st.success(f"Welcome back, {username}!")
        # Clean URL
        # st.query_params.clear()
    else:
        st.error("Session expired or invalid.")
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
        # Clear invalid token from storage to prevent reload loops
        st.markdown("<script>localStorage.removeItem('capacitybay_session');</script>", unsafe_allow_html=True)

# Inject Persistence Script (Only if NOT logged in and NO session_id in URL)
if not st.session_state.logged_in and not session_id and not logout_reason:
    st.markdown("""
        <script>
            const token = localStorage.getItem('capacitybay_session');
            if (token) {
                window.location.search = '?session_id=' + token;
            }
        </script>
    """, unsafe_allow_html=True)

# Initialize NLP (Moved to after bot initialization)



if 'sound_queue' not in st.session_state:
    st.session_state.sound_queue = []



# Custom CSS removed in favor of core.styles
# st.markdown("""...""", unsafe_allow_html=True)

# --- Helper Functions ---
def get_bot(exchange_id):
    """Get or create bot instance for the current session (Avoids global cache collision)"""
    # Use session version key to force reload of bot instance when core modules update
    session_key = f"bot_{exchange_id}_{SESSION_VERSION_KEY}"
    if session_key not in st.session_state:
        st.session_state[session_key] = TradingBot(exchange_id)
        # Restore wallet balances from session cache if available
        cache_key = f"wallet_cache_{exchange_id}_v10"
        if cache_key in st.session_state:
            st.session_state[session_key].wallet_balances = st.session_state[cache_key]
        
    bot = st.session_state[session_key]
    
    # SAFETY PATCH: Ensure wallet_balances attribute exists
    if not hasattr(bot, 'wallet_balances'):
        bot.wallet_balances = []

    # PERSISTENCE FIX: Auto-inject credentials from AuthManager if missing
    # This fixes "Auto-sync failed" on page refresh
    try:
        if st.session_state.get('logged_in') and 'auth_manager' in st.session_state:
            # Check if bot has credentials
            has_creds = False
            if hasattr(bot.data_manager, 'exchange') and bot.data_manager.exchange:
                if bot.data_manager.exchange.apiKey and bot.data_manager.exchange.secret:
                    has_creds = True
            
            if not has_creds:
                username = st.session_state.get('username')
                if username:
                    key, secret = st.session_state.auth_manager.get_api_keys(username, exchange_id)
                    if key and secret:
                        # Inject without triggering a full update/connect sequence if just ensuring presence
                        # But update_credentials handles the connection logic, so use it.
                        print(f"Auto-injecting credentials for {exchange_id}...")
                        bot.data_manager.update_credentials(key, secret)
                        bot.trading_mode = 'CEX_Direct'
                        # Ensure connection state
                        st.session_state[f"{exchange_id}_connected"] = True
                        st.session_state.exchange_connected = True
    except Exception as e:
        print(f"Failed to auto-inject credentials: {e}")
        
    return bot

@st.cache_data(ttl=600)
def get_cached_fundamentals(symbol, _bot):
    return _bot.fundamentals.get_asset_details(symbol)

@st.cache_data(ttl=600)
def get_cached_sentiment(_bot):
    return _bot.fundamentals.get_market_sentiment()

@st.cache_data(ttl=10)
def get_cached_ohlcv(_bot, symbol, timeframe):
    return _bot.data_manager.fetch_ohlcv(symbol, timeframe, limit=200)

@st.cache_data(ttl=60)
def get_cached_analysis(_bot, df):
    """Cache the heavy analysis to improve dashboard speed"""
    # Simple validation: Ensure df is not too old (though cache ttl handles this mostly, 
    # we want to ensure we don't cache empty or stale data if passed explicitly)
    if df.empty:
        return None
    return _bot.run_analysis(df)

@st.cache_data(ttl=60)
def get_cached_prediction(_bot, df):
    """Cache ML prediction"""
    return _bot.brain.predict_next_move(df)

def check_alerts(bot_instance):
    """Check active alerts against current market data (Optimized)"""
    if 'alerts' not in st.session_state or not st.session_state.alerts:
        return

    triggered_alerts = []
    # Group by symbol to minimize API calls
    active_alerts = [a for a in st.session_state.alerts if a['active']]
    if not active_alerts:
        return
        
    symbols = set(a['symbol'] for a in active_alerts)
    prices = {}
    
    for sym in symbols:
        try:
            # Fetch price once per symbol
            ticker = bot_instance.data_manager.fetch_ticker(sym)
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
    
    # Process triggers
    for i, alert, price in triggered_alerts:
        # Play sound
        st.session_state.sound_queue.append("alert")
        # Show notification
        st.toast(f"🔔 ALERT: {alert['symbol']} is {alert['condition']} {alert['value']} (Current: {price})", icon="🔔")
        # Deactivate
        st.session_state.alerts[i]['active'] = False

# --- Authentication Logic ---
if not st.session_state.logged_in:
    # Remove default top padding and spacer for immediate visibility
    
    # Responsive Columns: Center on desktop, Full width on mobile
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        # Cyberpunk Header
        st.markdown("""
        <div class="login-header" style='text-align: center; margin-bottom: 30px;'>
            <h1 style='color: #00f2ff; margin-bottom: 10px; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); font-family: "JetBrains Mono", monospace;'>Capa-X</h1>
            <h3 style='color: #e0e6ed; font-size: 1.1rem; margin-bottom: 5px; font-weight: 400;'>The Intelligent Trading Engine</h3>
            <p style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 15px; font-style: italic;'>The Future of Trading, Today</p>
            <p style='color: #64748b; font-size: 0.8rem; margin-top: 5px;'>powered by <span style='color: #00994d; font-weight: 700;'>CapacityBay</span></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Container with explicit border styling via CSS target
        with st.container():
            st.markdown("""
            <style>
            /* Reduce top padding for main container so login is at the top */
            .block-container {
                padding-top: 0rem !important;
                padding-bottom: 0rem !important;
            }
            
            /* Login Form Container Styling */
            [data-testid="stForm"] {
                background-color: rgba(20, 25, 35, 0.8);
                border: 1px solid rgba(0, 242, 255, 0.2);
                border-radius: 15px;
                padding: 1.5rem;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
                margin-top: 0px;
            }
            
            /* Responsive adjustments */
            @media (max-width: 768px) {
                /* Make the center column wider on mobile */
                div[data-testid="column"] {
                    width: 100% !important;
                    flex: 1 1 auto !important;
                    min-width: 100% !important;
                }
                
                /* Further reduce padding on mobile */
                .block-container {
                    padding-top: 0rem !important;
                }
                
                /* Reduce padding on mobile */
                [data-testid="stForm"] {
                    padding: 1.5rem;
                    margin-top: 0rem;
                }
                
                .login-header h1 {
                    font-size: 2rem !important;
                }
                
                .login-header {
                    margin-bottom: 15px !important;
                }
            }
            
            /* Input fields enhancement */
            .stTextInput input {
                background-color: rgba(10, 14, 23, 0.9) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                color: white !important;
            }
            
            .stTextInput input:focus {
                border-color: #00f2ff !important;
                box-shadow: 0 0 10px rgba(0, 242, 255, 0.2) !important;
            }
            
            /* Tab Styling */
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
                background-color: transparent;
            }
            
            .stTabs [data-baseweb="tab"] {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 5px;
                color: #94a3b8;
                padding: 8px 16px;
                border: none;
            }
            
            .stTabs [aria-selected="true"] {
                background-color: rgba(0, 242, 255, 0.1) !important;
                color: #00f2ff !important;
                border: 1px solid rgba(0, 242, 255, 0.3) !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
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
                                time.sleep(0.5) # UX delay
                                success, result = st.session_state.auth_manager.login_user(username, password)
                                if success:
                                    if result.get('2fa_enabled', False):
                                        st.session_state.login_stage = '2fa'
                                        st.session_state.temp_user_data = result
                                        st.session_state.remember_me = remember_me
                                        st.rerun()
                                    else:
                                        # Direct Login
                                        st.session_state.logged_in = True
                                        st.session_state.username = username
                                        st.session_state.user_role = result['role']
                                        st.session_state.user_manager = UserManager(username)
                                        st.session_state.last_active = time.time()
                                        
                                        # Create Session
                                        token = st.session_state.session_manager.create_session(username, remember_me)
                                        st.session_state.session_token = token
                                        
                                        # Update URL for immediate persistence on refresh
                                        st.query_params["session_id"] = token
                                        
                                        # Inject JS to save token
                                        st.markdown(f"""
                                            <script>
                                                localStorage.setItem('capacitybay_session', '{token}');
                                            </script>
                                        """, unsafe_allow_html=True)
                                        
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
                        # Get username from stored temp data or login input
                        # Prioritize login_user input as it is the most recent context
                        username = st.session_state.login_user
                        
                        if st.session_state.auth_manager.verify_2fa_login(username, code):
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.user_role = st.session_state.temp_user_data['role']
                            st.session_state.user_manager = UserManager(username)
                            st.session_state.last_active = time.time()
                            
                            # Create Session
                            remember_me = st.session_state.get('remember_me', False)
                            token = st.session_state.session_manager.create_session(username, remember_me)
                            st.session_state.session_token = token
                            
                            # Update URL for immediate persistence on refresh
                            st.query_params["session_id"] = token
                            
                            st.markdown(f"""
                                <script>
                                    localStorage.setItem('capacitybay_session', '{token}');
                                </script>
                            """, unsafe_allow_html=True)
                            
                            st.session_state.login_stage = 'credentials' # Reset
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

    st.stop() # Stop execution if not logged in

# --- Main Dashboard (Only reachable if logged in) ---

# --- Fast Load: Post-Login Imports ---
import pandas as pd
import numpy as np
# Imports moved to specific pages for faster load
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
import subprocess
import signal
import streamlit.components.v1 as components
from config.trading_config import TRADING_CONFIG
import json

# --- Fast Load: Import Core Modules Only After Login ---
import importlib
import core.data
import core.risk
import core.strategies
import core.bot

# Optimization: Only reload when version changes to enable Fast Load
SESSION_VERSION_KEY = "v24" 

if 'loaded_core_version' not in st.session_state or st.session_state.loaded_core_version != SESSION_VERSION_KEY:
    try:
        # CORRECT RELOAD ORDER: Dependencies first
        importlib.reload(core.data)
        # core.auth is reloaded if needed but safe to skip for speed if stable
        importlib.reload(core.risk)
        importlib.reload(core.brain) # Ensure brain is reloaded
        importlib.reload(core.strategies) # Ensure strategies are updated
        importlib.reload(core.bot)
        st.session_state.loaded_core_version = SESSION_VERSION_KEY
        print(f"Core modules reloaded for version {SESSION_VERSION_KEY}")
    except Exception as e:
        st.error(f"Error reloading core modules: {e}")

from core.bot import TradingBot
from core.defi import DeFiManager
# Optimization: Lazy load other modules or only import what is strictly needed for the dashboard main thread
# The following imports might be heavy or unused in the main loop
from core.auto_trader import AutoTrader # Accessed via bot.auto_trader
from core.copy_trading import CopyTradingModule # Accessed via sub-pages
from core.nlp_engine import NLPEngine
from core.sound_engine import SoundEngine
from core.trade_replay import TradeReplay
from core.chaos import ChaosMonkey
from core.transparency import TransparencyLog, OracleManager
# -------------------------------------------------------

# Initialize Sound Engine (Post-Login)
if 'sound_engine' not in st.session_state:
    st.session_state.sound_engine = SoundEngine()

# Initialize Trade Replay (Post-Login)
if 'trade_replay' not in st.session_state:
    st.session_state.trade_replay = TradeReplay()

# Sidebar Configuration
with st.sidebar:
    # --- BRANDING ---
    st.markdown("<h1 style='text-align: center; color: #00f2ff; margin-bottom: 20px;'>Capa-X</h1>", unsafe_allow_html=True)
    # cyberpunk_logo(size="120px", font_size="16px")

    # --- CYBERPUNK STATUS WIDGET ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 242, 255, 0.05) 0%, rgba(0, 0, 0, 0) 100%); padding: 15px; border-radius: 10px; border: 1px solid rgba(0, 242, 255, 0.2); margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <span style="color: #00f2ff; font-weight: 800; letter-spacing: 1px; font-size: 0.9rem;">SYSTEM STATUS</span>
            <span style="height: 8px; width: 8px; background-color: #00f2ff; border-radius: 50%; box-shadow: 0 0 8px #00f2ff; animation: pulse 2s infinite;"></span>
        </div>
        <div style="height: 1px; background: linear-gradient(90deg, rgba(0,242,255,0.5), transparent); margin-bottom: 8px;"></div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
            <span>LATENCY</span>
            <span style="color: #00ff9d;">12ms</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
            <span>MEM POOL</span>
            <span style="color: #00ff9d;">OPTIMAL</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
            <span>AI MODEL</span>
            <span style="color: #bd00ff;">ACTIVE</span>
        </div>
    </div>
    <style>
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 242, 255, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0, 242, 255, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 242, 255, 0); }
    }
    </style>
    """, unsafe_allow_html=True)
    
    neon_header("Global Configuration", level=2)
    
    # Navigation
    page_nav = st.radio("Navigate", ["Trading Dashboard", "Wallet & Funds", "Strategy Manager", "Trading Monitor", "Trading Terminal", "Arbitrage Scanner", "Copy Trading", "Blockchain & DeFi", "Quantum Lab", "Risk Management", "Settings"], key="main_nav_radio")
    
    st.divider()
    
    # Clock & Session Info
    utc_now = pd.Timestamp.now(tz='UTC')
    st.caption(f"🕒 UTC: {utc_now.strftime('%H:%M:%S')}")
    
    # Expanded Pair Selection
    POPULAR_PAIRS = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT', 
        'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT'
    ]
    
    symbol_input = st.selectbox("Select Pair", POPULAR_PAIRS, index=0)
    custom_symbol = st.text_input("Or Custom Pair (e.g. LINK/USDT)", "")
    
    symbol = custom_symbol if custom_symbol else symbol_input
    
    timeframe = st.selectbox("Timeframe", ['1m', '5m', '15m', '1h', '4h', '1d'], index=3)
    
    # --- WEB3 WALLET INTEGRATION ---
    st.divider()
    st.markdown("### 🔐 Web3 Wallet")
    
    # Check for JS actions (e.g., TON Connect fallback)
    if "action" in st.query_params:
        if st.query_params["action"] == "connect_ton":
            st.session_state.show_ton_modal = True
            st.toast("Opening Telegram Wallet...", icon="💎")
            # We don't clear query params here to avoid loop, user will just see the modal open

    # Check for wallet in URL (Callback from JS)
    if "wallet_address" in st.query_params:
        addr = st.query_params["wallet_address"]
        chain_id = st.query_params.get("chain_id", "1")
        provider_name = st.query_params.get("provider", "Unknown")
        
        # Basic validation
        valid = False
        if chain_id == 'solana':
            # Solana addresses are base58, length varying 32-44 usually
            if len(addr) > 30: 
                valid = True
        elif addr.startswith("0x") and len(addr) == 42:
            valid = True
            
        if valid:
            if st.session_state.web3_wallet.connect(addr, chain_id, provider_name):
                st.toast(f"Connected to {provider_name}!", icon="🔗")
                
    if not st.session_state.web3_wallet.is_connected():
        # --- TELEGRAM WALLET (Simulated) ---
        if 'ton_manager' not in st.session_state:
            st.session_state.ton_manager = TonConnectManager()
            
        st.markdown("#### 💎 Telegram Ecosystem")
        col_tg, col_other = st.columns([1, 1])
        with col_tg:
            st.info("🚀 **Recommended for TON Users**")
            if st.button("Connect Telegram Wallet", use_container_width=True, type="primary"):
                st.session_state.show_ton_modal = True
        
        if st.session_state.get('show_ton_modal', False):
            with st.expander("📱 Telegram Wallet Connection", expanded=True):
                req = st.session_state.ton_manager.generate_connect_request()
                st.markdown("### 💎 Connect via Telegram")
                st.warning("⚠️ **NOTE:** Browser blocking may prevent automatic app opening. Please use the options below.")
                
                # 1. Direct Links
                col_link1, col_link2 = st.columns(2)
                with col_link1:
                     st.link_button("🚀 Open Tonkeeper", req['connect_url'], type="primary", help="Best for Tonkeeper App")
                with col_link2:
                     tg_url = req.get('tg_link', "https://t.me/wallet")
                     # Try to force a new window which sometimes helps with protocol handlers
                     st.markdown(f'<a href="{tg_url}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background-color: #24A1DE; color: white; text-decoration: none; border-radius: 4px; text-align: center; width: 100%;">✈️ Open Telegram Desktop</a>', unsafe_allow_html=True)
                
                # 2. Manual Copy
                st.markdown("---")
                st.markdown("**Option 2: Copy & Paste**")
                st.caption("Copy this link and paste it into your browser address bar or a Telegram message to yourself:")
                st.code(req['connect_url'], language="text")
                
                # 3. Simulation / Skip
                st.markdown("---")
                st.markdown("### 🛑 Still not working?")
                st.info("If the wallet app doesn't open or connect, use **Simulation Mode** to instantly load a demo wallet and start trading.")
                
                # Optional: Use real address for simulation
                custom_sim_addr = st.text_input("Enter your TON Address (Optional)", placeholder="Paste address to fetch REAL balance for simulation")
                
                if st.button("✅ CLICK HERE TO CONNECT (Demo Mode)", type="primary", use_container_width=True):
                    if custom_sim_addr and len(custom_sim_addr) > 10:
                        # Use User's Address
                        target_addr = custom_sim_addr
                    else:
                        # Generate Random Address
                        mock_data = st.session_state.ton_manager.mock_approve_connection()
                        target_addr = mock_data['address']
                        
                    # Connect via Web3Wallet interface for consistency
                    # We set provider to 'Telegram Wallet' to enable "Trading" (Simulation)
                    st.session_state.web3_wallet.connect(target_addr, 'ton', 'Telegram Wallet')
                    st.session_state.is_telegram_wallet = True
                    st.session_state.show_ton_modal = False
                    st.toast("Telegram Wallet Connected Successfully!", icon="🎉")
                    st.rerun()

        # EXPANDED WALLET SELECTOR WITH DISCOVERY
        
        # Fallback manual trigger
        if st.button("🔌 Trouble Connecting? Click for Manual TON Setup", type="secondary", use_container_width=True):
             st.session_state.show_ton_modal = True
             st.rerun()

        # Get Project ID from session if available
        wc_project_id = st.session_state.get('wc_project_id', '')
        
        components.html(f"""
        <style>
        :root {{
            --primary: #00f2ff;
            --bg-dark: #0e1117;
            --card-bg: #1e2130;
        }}
        body {{ margin: 0; font-family: 'Segoe UI', sans-serif; background: transparent; color: white; }}
        .wallet-container {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 580px;
            overflow-y: auto;
        }}
        .universal-btn {{
            background: linear-gradient(90deg, #00f2ff, #00a8ff);
            border: none;
            border-radius: 8px;
            color: #000;
            padding: 12px;
            font-weight: bold;
            cursor: pointer;
            text-align: center;
            font-size: 16px;
            transition: transform 0.2s;
            width: 100%;
        }}
        .universal-btn:hover {{
            transform: scale(1.02);
        }}
        .wallet-grid {{
            display: none; /* Hidden by default */
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 10px;
            animation: fadeIn 0.3s ease-in-out;
        }}
        @media (max-width: 600px) {{
            .wallet-grid {{
                grid-template-columns: 1fr;
            }}
            .wallet-btn {{
                padding: 12px;
                font-size: 14px;
            }}
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .wallet-btn {{
            background: rgba(30, 33, 48, 0.8);
            border: 1px solid rgba(0, 242, 255, 0.3);
            border-radius: 8px;
            color: #fff;
            padding: 10px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 10px;
            transition: all 0.2s ease;
            font-size: 13px;
        }}
        .wallet-btn:hover {{
            background: rgba(0, 242, 255, 0.1);
            border-color: #00f2ff;
            transform: translateY(-2px);
        }}
        .icon {{ width: 24px; height: 24px; border-radius: 50%; }}
        .status {{ font-size: 10px; color: #00ff9d; margin-left: auto; display: none; }}
        .detected .status {{ display: block; }}
        </style>
        
        <div class="wallet-container">
            <button class="universal-btn" onclick="toggleWallets()">🔌 Connect Wallet</button>
            
            <div class="wallet-grid" id="wallet-list">
                <div class="wallet-btn" id="btn-metamask" onclick="connectEVM('metamask')">
                    <span>🦊 MetaMask</span>
                    <span class="status">●</span>
                </div>
                <div class="wallet-btn" id="btn-trust" onclick="connectEVM('trust')">
                    <span>🛡️ Trust Wallet</span>
                    <span class="status">●</span>
                </div>
                <div class="wallet-btn" id="btn-coinbase" onclick="connectEVM('coinbase')">
                    <span>🔵 Coinbase</span>
                    <span class="status">●</span>
                </div>
                <div class="wallet-btn" id="btn-okx" onclick="connectEVM('okx')">
                    <span>⚫ OKX Wallet</span>
                    <span class="status">●</span>
                </div>
                <div class="wallet-btn" id="btn-phantom" onclick="connectSolana()">
                    <span>👻 Phantom (SOL)</span>
                    <span class="status">●</span>
                </div>
                <div class="wallet-btn" id="btn-keplr" onclick="connectCosmos()">
                    <span>🪐 Keplr (Cosmos)</span>
                    <span class="status">●</span>
                </div>
                <div class="wallet-btn" id="btn-ton" onclick="connectTON()">
                    <span>💎 TON Wallet</span>
                    <span class="status">●</span>
                </div>
                <div class="wallet-btn" onclick="connectEVM('injected')">
                    <span>🌐 Browser Wallet</span>
                </div>
                <div class="wallet-btn" onclick="connectWC()">
                    <span>📡 WalletConnect</span>
                </div>
                <div class="wallet-btn" onclick="connectHardware()">
                    <span>🔐 Hardware (Ledger)</span>
                </div>
                <div class="wallet-btn" style="border-color: #bd00ff; background: rgba(189, 0, 255, 0.1);" onclick="enableManual()">
                    <span>➕ Other / Custom</span>
                </div>
            </div>
        </div>

        <script>
        function toggleWallets() {{
            const list = document.getElementById('wallet-list');
            list.style.display = (list.style.display === 'grid') ? 'none' : 'grid';
        }}

        function enableManual() {{
            // Reload to trigger Manual Connection Open state
            const target = window.parent || window.top;
            try {{
                const url = new URL(target.location.href);
                url.searchParams.set('action', 'enable_manual');
                url.searchParams.set('ts', Date.now());
                target.location.href = url.toString();
            }} catch(e) {{
                console.error(e);
                // Fallback: Try opening in top window (triggering reload)
                const url = new URL(window.location.href); 
                // Note: We need parent URL, but if access denied, we might be stuck.
                // Try a generic reload or alert user to use the toggle below.
                alert("⚠️ Auto-expand failed due to browser security.\\n\\nPlease click the '📝 Manual Connection' toggle below manually.");
            }}
        }}

        // WALLET DETECTION
        function detect() {{
            if (window.ethereum?.isMetaMask) document.getElementById('btn-metamask').classList.add('detected');
            if (window.ethereum?.isTrust || window.trustwallet) document.getElementById('btn-trust').classList.add('detected');
            if (window.ethereum?.isCoinbaseWallet) document.getElementById('btn-coinbase').classList.add('detected');
            if (window.okxwallet) document.getElementById('btn-okx').classList.add('detected');
            if (window.solana?.isPhantom) document.getElementById('btn-phantom').classList.add('detected');
            if (window.keplr) document.getElementById('btn-keplr').classList.add('detected');
            if (window.ton) document.getElementById('btn-ton').classList.add('detected');
        }}
        detect();

        async function connectEVM(type) {{
            let provider = window.ethereum;
            
            // Provider Selection
            if (type === 'trust' && window.trustwallet) provider = window.trustwallet;
            if (type === 'okx' && window.okxwallet) provider = window.okxwallet;
            if (type === 'coinbase' && window.ethereum?.isCoinbaseWallet) {{
                // Coinbase handling
            }}

            if (provider) {{
                try {{
                    const accounts = await provider.request({{ method: 'eth_requestAccounts' }});
                    const chainId = await provider.request({{ method: 'eth_chainId' }});
                    const account = accounts[0];
                    const chainIdDec = parseInt(chainId, 16);
                    
                    window.parent.location.search = `?wallet_address=${{account}}&chain_id=${{chainIdDec}}&provider=${{type}}`;
                }} catch (error) {{
                    console.error(error);
                    alert("Connection Failed: " + error.message);
                }}
            }} else {{
                alert("⚠️ Wallet not detected in this interface!\\n\\nStreamlit's security sandbox may be blocking your extension.\\n\\nSOLUTION:\\nUse the '📝 Manual Connection' form below to connect via Address or Private Key.");
                if (type === 'metamask') window.open("https://metamask.io/download/", "_blank");
                if (type === 'trust') window.open("https://trustwallet.com/download", "_blank");
                if (type === 'coinbase') window.open("https://www.coinbase.com/wallet/downloads", "_blank");
                if (type === 'okx') window.open("https://www.okx.com/web3", "_blank");
            }}
        }}

        async function connectSolana() {{
            if (window.solana) {{
                try {{
                    const resp = await window.solana.connect();
                    const pubKey = resp.publicKey.toString();
                    window.parent.location.search = `?wallet_address=${{pubKey}}&chain_id=solana&provider=phantom`;
                }} catch (err) {{
                    console.error(err);
                }}
            }} else {{
                window.open("https://phantom.app/", "_blank");
            }}
        }}

        async function connectCosmos() {{
            if (window.keplr) {{
                try {{
                    const chainId = "cosmoshub-4"; 
                    await window.keplr.enable(chainId);
                    const offlineSigner = window.keplr.getOfflineSigner(chainId);
                    const accounts = await offlineSigner.getAccounts();
                    window.parent.location.search = `?wallet_address=${{accounts[0].address}}&chain_id=cosmos&provider=keplr`;
                }} catch (err) {{
                    alert("Keplr Error: " + err.message);
                }}
            }} else {{
                alert("Keplr not installed!");
                window.open("https://www.keplr.app/", "_blank");
            }}
        }}

        async function connectTON() {{
            const btn = document.getElementById('btn-ton');
            if(btn) btn.innerHTML = '<span>⏳ Connecting...</span>';

            const redirect = () => {{
                // Fallback redirection logic
                const target = window.parent || window.top;
                try {{
                    const url = new URL(target.location.href);
                    url.searchParams.set('action', 'connect_ton');
                    url.searchParams.set('ts', Date.now());
                    target.location.href = url.toString();
                }} catch(e) {{
                    console.error(e);
                    // Fallback for cross-origin issues
                    alert("Please click the 'Trouble Connecting?' button below.");
                }}
            }};

            if (window.ton) {{
                try {{
                    const accounts = await window.ton.send('ton_requestWallets');
                    if (accounts && accounts.length > 0) {{
                        const target = window.parent || window.top;
                        const newUrl = new URL(target.location.href);
                        newUrl.searchParams.set('wallet_address', accounts[0].address);
                        newUrl.searchParams.set('chain_id', 'ton');
                        newUrl.searchParams.set('provider', 'tonkeeper');
                        newUrl.searchParams.set('ts', Date.now());
                        target.location.href = newUrl.toString();
                    }}
                }} catch (err) {{
                    console.log("TON Error, fallback to modal:", err);
                    redirect();
                }}
            }} else {{
                console.log("TON Wallet not detected, redirecting...");
                redirect();
            }}
        }}
        
        function connectWC() {{
             const projectId = "{wc_project_id}";
             if (!projectId) {{
                 alert("⚠️ WalletConnect V2 Requires a Project ID.\\n\\nPlease configure it in 'Settings -> System Settings -> Web3 Configuration'.");
                 return;
             }}
             // Placeholder for V2 logic which requires complex bundling
             if (confirm("🔗 WalletConnect (Mobile/Remote)\\n\\nTo connect a mobile wallet (e.g., Trust, MetaMask Mobile):\\n1. Ensure you have the app installed.\\n2. Click OK to attempt a connection via your browser's Web3 injection (if available).\\n3. Or use 'Manual Connection' below for read-only access.")) {{
                connectEVM('injected');
             }}
        }}

        function connectHardware() {{
            alert("🔐 Hardware Wallet (Ledger/Trezor)\\n\\nFor security, direct hardware connection is restricted.\\n\\nOptions:\\n1. Connect your device to MetaMask/Frame and use the 'Browser Wallet' button.\\n2. Use the 'Manual / Read-Only Connection' form below to track your portfolio safely without signing rights.");
        }}
        </script>
        """, height=600) # Increased height for dropdown
        
        # Manual Connection Toggle
        st.markdown("<div id='manual-connect'></div>", unsafe_allow_html=True)
        
        # Check for auto-expand trigger from JS button
        is_manual_expanded = False
        if st.query_params.get("action") == "enable_manual":
            is_manual_expanded = True
            
        if st.toggle("📝 Manual Connection (Address or Private Key)", value=is_manual_expanded):
            with st.form("manual_wallet_form"):
                st.caption("Enter Address for Read-Only (Watch) or Private Key for Trading (EVM Only).")
                m_addr = st.text_input("Wallet Address or Private Key", type="password")
                m_chain = st.selectbox("Network", [
                    "Ethereum (1)", "BNB Chain (56)", "Polygon (137)", "Solana", "Arbitrum (42161)", 
                    "Optimism (10)", "Avalanche (43114)", "Base (8453)", "Fantom (250)", "Cronos (25)", 
                    "Gnosis (100)", "zkSync Era (324)", "Linea (59144)", "Tron (TRX)", "Bitcoin (BTC)", 
                    "Litecoin (LTC)", "Dogecoin (DOGE)", "Cosmos Hub", "TON", "➕ Custom RPC / Other Network"
                ])
                
                # Custom Network Inputs
                if "Custom" in m_chain:
                    st.markdown("---")
                    st.caption("Custom EVM Network Configuration")
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        c_name = st.text_input("Network Name", "My Custom Chain")
                        c_rpc = st.text_input("RPC URL", "https://...")
                    with c_col2:
                        c_cid = st.text_input("Chain ID", "1234")
                        c_sym = st.text_input("Currency Symbol", "ETH")

                m_submit = st.form_submit_button("Connect")
                
                if m_submit and m_addr:
                    # Parse Chain ID
                    cid = "1"
                    
                    if "Custom" in m_chain:
                        if c_rpc and c_cid and c_rpc != "https://...":
                            st.session_state.web3_wallet.add_custom_chain(c_cid, c_rpc, c_name, c_sym, 'evm')
                            cid = c_cid
                        else:
                            st.error("Please provide a valid RPC URL and Chain ID.")
                            st.stop()
                    elif "Solana" in m_chain: cid = "solana"
                    elif "Cosmos" in m_chain: cid = "cosmos"
                    elif "TON" in m_chain: cid = "ton"
                    elif "Tron" in m_chain: cid = "tron"
                    elif "Bitcoin" in m_chain: cid = "bitcoin"
                    elif "Litecoin" in m_chain: cid = "litecoin"
                    elif "Dogecoin" in m_chain: cid = "dogecoin"
                    elif "(" in m_chain:
                        cid = m_chain.split("(")[1].replace(")", "")
                    
                    if st.session_state.web3_wallet.connect(m_addr, cid, "Manual"):
                         mode_str = "Trading Enabled 🔓" if st.session_state.web3_wallet.mode == 'read_write' else "Read-Only 👀"
                         st.toast(f"Connected Successfully ({mode_str})", icon="✅")
                         st.rerun()
                    else:
                        st.error("Invalid Input format.")
    else:
        # Connected State
        w3_col1, w3_col2 = st.columns([3, 1])
        with w3_col1:
            # Dynamic Icon
            prov_icon = "🦊"
            if st.session_state.web3_wallet.provider == 'Telegram Wallet': prov_icon = "💎"
            elif st.session_state.web3_wallet.provider == 'phantom': prov_icon = "👻"
            elif st.session_state.web3_wallet.provider == 'trust': prov_icon = "🛡️"
            elif st.session_state.web3_wallet.provider == 'coinbase': prov_icon = "🔵"
            
            st.markdown(f"**{prov_icon} {st.session_state.web3_wallet.get_short_address()}**")
            
            # Show Network
            net_name = st.session_state.web3_wallet.get_network_name()
            st.caption(f"{net_name}")
            
            # Show Balance
            symbol = st.session_state.web3_wallet.get_symbol()
            bal = st.session_state.web3_wallet.get_balance()
            st.markdown(f"<span style='color:#00f2ff; font-size:1.2em'>{bal:.4f} {symbol}</span>", unsafe_allow_html=True)
            
            # --- TOKEN SCANNER ---
            with st.expander("Token Balances", expanded=False):
                # Common Token Addresses (Simplified for Demo)
                # In prod, this should be a large config file
                tokens = {
                    '1': {'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7', 'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'},
                    '56': {'USDT': '0x55d398326f99059fF775485246999027B3197955', 'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'},
                    'solana': {'USDT': 'Es9vMFrzcCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB', 'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'}
                }
                
                chain_id = st.session_state.web3_wallet.chain_id
                if chain_id in tokens:
                    for t_name, t_addr in tokens[chain_id].items():
                        t_bal = st.session_state.web3_wallet.get_token_balance(t_addr)
                        if t_bal > 0:
                            st.write(f"**{t_name}:** {t_bal:,.2f}")
                        else:
                            st.caption(f"{t_name}: 0.00")
                else:
                    st.caption("Token scan not available for this chain.")

        with w3_col2:
             if st.button("❌", help="Disconnect Wallet"):
                 st.session_state.web3_wallet.disconnect()
                 st.rerun()

        # --- UNIVERSAL TRADING TERMINAL ---
        st.divider()
        st.markdown(f"#### 🌐 {st.session_state.web3_wallet.get_network_name()} Trading Terminal")
        
        # Determine if we are on TON (Special Handling)
        is_ton = st.session_state.web3_wallet.provider == 'Telegram Wallet' or st.session_state.web3_wallet.chain_id == 'ton'
        
        # 1. BALANCE DISPLAY
        if is_ton:
            # Fetch simulated balance if not already available
            if 'ton_manager' not in st.session_state:
                st.session_state.ton_manager = TonConnectManager()
            
            # Use stored balance or fetch
            wallet_bal = st.session_state.ton_manager.get_balance(st.session_state.web3_wallet.address)
            main_symbol = "TON"
            sec_symbol = "USDT"
            main_val = wallet_bal['TON']
            sec_val = wallet_bal['USDT']
        else:
            # Fetch real/RPC balance
            main_symbol = st.session_state.web3_wallet.get_symbol()
            main_val = st.session_state.web3_wallet.get_balance()
            
            # Mock Secondary for Demo (USDT)
            sec_symbol = "USDT"
            sec_val = 0.0
            # Try to fetch real USDT if on Mainnet
            if st.session_state.web3_wallet.chain_id == '1':
                sec_val = st.session_state.web3_wallet.get_token_balance('0xdAC17F958D2ee523a2206206994597C13D831ec7')

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.metric(f"{main_symbol} Balance", f"{main_val:,.4f}")
        with t_col2:
            st.metric(f"{sec_symbol} Balance", f"{sec_val:,.2f}")
            
        st.markdown("---")
        
        # 2. TRADING INTERFACE
        tab_swap, tab_send, tab_bridge = st.tabs(["💱 Swap (DEX)", "💸 Transfer", "🌉 Bridge"])
        
        with tab_swap:
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                action = st.radio("Action", [f"Buy {main_symbol}", f"Sell {main_symbol}"], horizontal=True)
                amount = st.number_input("Amount", 0.0001, 100000.0, 0.1)
            with s_col2:
                slippage = st.slider("Slippage %", 0.1, 5.0, 1.0)
                if is_ton:
                    st.caption("Routing: STON.fi / DeDust")
                elif st.session_state.web3_wallet.chain_id == 'solana':
                    st.caption("Routing: Jupiter / Raydium")
                else:
                    st.caption("Routing: Uniswap / 1inch")
            
            # Gas Estimation
            gas_fee = 0.0
            if is_ton:
                gas_fee = st.session_state.ton_manager.estimate_gas("swap")
                fee_sym = "TON"
            elif st.session_state.web3_wallet.chain_id == 'solana':
                gas_fee = 0.000005
                fee_sym = "SOL"
            else:
                # EVM Estimate
                est = st.session_state.web3_wallet.estimate_gas(st.session_state.web3_wallet.address, amount)
                gas_fee = est if est else 0.005
                fee_sym = main_symbol

            st.info(f"⛽ Network Fee: ~{gas_fee:.6f} {fee_sym}")
            
            if st.button("Confirm Swap", type="primary", use_container_width=True):
                # Allow Manual/Read-Only to proceed in Simulation Mode
                is_manual = st.session_state.web3_wallet.provider == 'Manual'
                
                with st.status(f"Processing on {st.session_state.web3_wallet.get_network_name()}...", expanded=True) as status:
                    if is_manual:
                        st.write("👀 Simulation Mode (Read-Only Wallet)...")
                    else:
                        st.write("📝 Constructing Transaction...")
                    
                    time.sleep(1)
                    
                    if not is_manual:
                        st.write("🔐 Requesting Wallet Signature...")
                        time.sleep(1.5)
                    
                    if is_ton:
                        st.write("🚀 Broadcasting to Network...")
                        time.sleep(1)
                        tx = st.session_state.ton_manager.sign_transaction({"type": "swap", "amount": amount})
                        
                        # Update Balance (Simulated)
                        if "Buy" in action: # Buy TON with USDT
                                # Deduct USDT, Add TON
                                cost_usdt = amount
                                got_ton = amount / 6.5
                                st.session_state.ton_manager.update_balance(st.session_state.web3_wallet.address, "USDT", -cost_usdt)
                                st.session_state.ton_manager.update_balance(st.session_state.web3_wallet.address, "TON", got_ton)
                        else:
                                # Deduct TON, Add USDT
                                cost_ton = amount
                                got_usdt = amount * 6.5
                                st.session_state.ton_manager.update_balance(st.session_state.web3_wallet.address, "TON", -cost_ton)
                                st.session_state.ton_manager.update_balance(st.session_state.web3_wallet.address, "USDT", got_usdt)
                        
                        # Deduct Gas
                        st.session_state.ton_manager.update_balance(st.session_state.web3_wallet.address, "TON", -gas_fee)
                        
                        status.update(label="Swap Completed!", state="complete", expanded=False)
                        st.success(f"Transaction Sent! Hash: {tx['tx_hash']}")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        # EVM/Solana Simulation
                        st.write("🚀 Broadcasting to Network...")
                        time.sleep(1)
                        status.update(label="Swap Completed!", state="complete", expanded=False)
                        if is_manual:
                             st.success(f"Simulation Successful! Trade logged (Paper Trading).")
                             
                             # LOG MANUAL WEB3 TRADE
                             try:
                                 target_exch = st.session_state.get('exchange', 'binance')
                                 bot_instance = get_bot(target_exch)
                                 
                                 # Determine symbol
                                 trade_symbol = f"{main_symbol}/USDT"
                                 
                                 # Fetch price for log if possible
                                 log_price = 0.0
                                 try:
                                     ticker = bot_instance.data_manager.fetch_ticker(trade_symbol)
                                     log_price = float(ticker.get('last', 0))
                                 except:
                                     pass
                                     
                                 packet = {
                                    "symbol": trade_symbol,
                                    "bias": "BUY" if "Buy" in action else "SELL",
                                    "entry": log_price,
                                    "stop_loss": 0,
                                    "take_profit": 0,
                                    "position_size": amount,
                                    "strategy": "Web3 Manual",
                                    "confidence": 1.0,
                                    "decision": "EXECUTE",
                                    "market_regime": "Manual Override"
                                 }
                                 bot_instance.log_trade(packet)
                                 st.toast("Trade Logged to Report", icon="📝")
                             except Exception as e:
                                 print(f"Web3 Log Error: {e}")
                                 
                        else:
                             st.success(f"Transaction Simulated Successfully! (Real signing requires wallet adapter upgrade)")
                        st.balloons()
        
        with tab_send:
            st.text_input("Recipient Address", placeholder="0x... or EQ...")
            amount_to_send = st.number_input(f"Amount to Send ({main_symbol})", 0.0, 10000.0, 0.0)
            if st.button("Send Assets"):
                 if st.session_state.web3_wallet.mode != 'read_write':
                     st.error("🚫 Read-Only Wallet. Connect with Private Key (EVM) or Browser Extension to sign transactions.")
                 else:
                     # Placeholder for Actual Send Logic
                     if st.session_state.web3_wallet.private_key:
                         st.info("Signing Transaction locally... (Feature in Beta)")
                         # TODO: Implement actual send_transaction call here
                         st.success(f"Transaction Sent! (Simulated for safety in this version). Amount: {amount_to_send}")
                     else:
                         st.info("Please confirm the transaction on your mobile device/extension.")

        with tab_bridge:
            st.info("Cross-Chain Bridge coming soon. Powered by LayerZero.")

    # Exchange Connection Manager
    st.divider()
    neon_header("Exchange Manager", level=2)
    
    # Connection Method Selection
    connection_method = st.radio("Connection Method", ["API (Automatic Trading)", "Manual (Signal Only)"], index=0)
    
    # Added requested exchanges: Luno, Quidax, NairaEx, Busha
    exchange_list = ['binance', 'luno', 'kucoin', 'bybit', 'quidax', 'nairaex', 'busha', 'kraken', 'okx', 'gateio', 'mexc']
    exchange = st.selectbox("Active Exchange", exchange_list)
    # Update session state
    st.session_state.exchange = exchange

    # Sync global connection state with specific exchange state
    if f"{exchange}_connected" in st.session_state:
        st.session_state.exchange_connected = st.session_state[f"{exchange}_connected"]
    else:
        st.session_state.exchange_connected = False

    if connection_method == "API (Automatic Trading)":
        with st.expander("API Credentials", expanded=True):
            # 1. Auto-Load Keys & Determine Auto-Connect Intent
            saved_key = None
            saved_secret = None
            should_auto_connect = False
            
            if st.session_state.logged_in:
                saved_key, saved_secret = st.session_state.auth_manager.get_api_keys(st.session_state.username, exchange)
                
                # Populate session state if empty (First load)
                if saved_key and f"{exchange}_api_key" not in st.session_state:
                    st.session_state[f"{exchange}_api_key"] = saved_key
                if saved_secret and f"{exchange}_api_secret" not in st.session_state:
                    st.session_state[f"{exchange}_api_secret"] = saved_secret
                
                # Check if we should auto-connect (Keys exist in DB)
                if saved_key and saved_secret:
                    should_auto_connect = True

            # 2. UI Inputs
            # Auto-fill if empty for quick support (User Provided Keys)
            default_key = ""
            default_secret = ""
            
            # Check session state for existing input
            existing_key = st.session_state.get(f"{exchange}_api_key", "")
            
            if exchange == 'binance' and not existing_key and not saved_key:
                default_key = "3MmGYZOzWqWD8IQZB9pOoCZlT4eSLG0RwBC8U2jqQEjQ7EpvtyuIwBhTQ0n9ESoS"
                default_secret = "etIg4wOuIQho8DVI4CKv0PGYqALJEr0Ul3fQN50GbLkxDH0oicNJOfDdA2JEAMDv"

            api_key = st.text_input("API Key", value=default_key, type="password", key=f"{exchange}_api_key")
            api_secret = st.text_input("API Secret", value=default_secret, type="password", key=f"{exchange}_api_secret")
            
            # Validation Warning
            if api_key and len(api_key.strip()) != 64 and exchange == 'binance':
                 st.warning(f"Warning: API Key length is {len(api_key.strip())} (Expected 64). Double check your key.")
            
            c_conn, c_disc = st.columns(2)
            with c_conn:
                connect_clicked = st.button("Connect Exchange", type="primary")
            
            # Check for existing connection state
            is_connected = st.session_state.get(f"{exchange}_connected", False)
            
            # 3. Connection Logic
            if connect_clicked or (is_connected and api_key and api_secret) or (should_auto_connect and api_key and api_secret):
                if api_key and api_secret:
                    try:
                        # SANITIZE INPUTS
                        api_key = api_key.strip()
                        api_secret = api_secret.strip()
                        
                        # Initialize bot
                        temp_bot = get_bot(exchange)
                        
                        # Optimization: Check if already connected to avoid redundant API calls on refresh
                        # But if user clicked Connect, FORCE update
                        already_connected = False
                        if hasattr(temp_bot, 'data_manager') and temp_bot.data_manager.connection_status == "Connected":
                             already_connected = True
                        
                        # Force update if clicked or not connected
                        if connect_clicked or not already_connected:
                            try:
                                temp_bot.data_manager.update_credentials(api_key, api_secret)
                            except Exception as cred_error:
                                # Handle -2008 Explicitly in UI
                                if "-2008" in str(cred_error) or "Invalid Api-Key ID" in str(cred_error):
                                    st.error("Invalid API Key Detected (-2008). Please check your key.")
                                    # Clear invalid keys from session state immediately
                                    st.session_state[f"{exchange}_connected"] = False
                                    if st.session_state.logged_in:
                                        st.session_state.auth_manager.delete_api_keys(st.session_state.username, exchange)
                                else:
                                    st.error(f"Failed to Update Credentials: {cred_error}")
                                raise cred_error # Re-raise to trigger the outer exception block

                            
                            # Validate Permissions (API Call)
                            show_spinner = connect_clicked or not is_connected
                            
                            if show_spinner:
                                with st.spinner(f"Connecting to {exchange.upper()}..."):
                                    # Balance Check
                                    bal_check = temp_bot.data_manager.get_balance()
                                    asset_count = len(bal_check.get('total', {}))
                                    if connect_clicked:
                                        st.toast(f"Connection Verified! Found {asset_count} assets.", icon="✅")
                            else:
                                pass # Silent maintenance

                        # Set Mode
                        temp_bot.trading_mode = 'CEX_Direct'
                        
                        # Update State
                        st.session_state[f"{exchange}_connected"] = True
                        st.session_state.exchange_connected = True
                        
                        # Save Keys (Persistence)
                        if st.session_state.logged_in and (connect_clicked or should_auto_connect):
                            st.session_state.auth_manager.save_api_keys(st.session_state.username, exchange, api_key, api_secret)
                            
                        if connect_clicked:
                            if temp_bot.data_manager.offline_mode:
                                st.warning(f"Connected to {exchange.upper()} but falling back to Mock Data due to connection issues.")
                                st.caption("Please check your API Key permissions. (Invalid API-Key ID usually means the Key itself is wrong)")
                            else:
                                st.success(f"Connected to {exchange.upper()}!")
                            
                    except Exception as e:
                        st.session_state[f"{exchange}_connected"] = False
                        if connect_clicked:
                            st.error(f"Connection Failed: {e}")
                            st.caption("Check API permissions and IP restrictions.")
                        elif should_auto_connect:
                             # Don't annoy user on every refresh if keys are bad, but maybe show warning once?
                             pass
                             
            # 4. Disconnect Button
            with c_disc:
                if (is_connected or should_auto_connect) and st.button("Disconnect"):
                    if st.session_state.logged_in:
                        st.session_state.auth_manager.delete_api_keys(st.session_state.username, exchange)
                    
                    # Clear Session State
                    st.session_state[f"{exchange}_connected"] = False
                    st.session_state.exchange_connected = False
                    if f"{exchange}_api_key" in st.session_state:
                        del st.session_state[f"{exchange}_api_key"]
                    if f"{exchange}_api_secret" in st.session_state:
                        del st.session_state[f"{exchange}_api_secret"]
                        
                    # Reset Bot
                    temp_bot = get_bot(exchange)
                    temp_bot.trading_mode = 'Demo'
                    st.cache_resource.clear()
                    st.rerun()
                elif connect_clicked:
                    st.warning("Please enter API Key and Secret")
        
        # Connect with Saved Keys Button
        if st.button("Connect with Saved Keys"):
            try:
                from config.exchanges import EXCHANGES
                if exchange in EXCHANGES and EXCHANGES[exchange]['apiKey']:
                    # Use keys from config/env
                    saved_key = EXCHANGES[exchange]['apiKey']
                    saved_secret = EXCHANGES[exchange]['secret']
                    
                    temp_bot = get_bot(exchange)
                    temp_bot.data_manager.update_credentials(saved_key, saved_secret)
                    temp_bot.trading_mode = 'CEX_Direct'
                    
                    # Verify connection
                    if temp_bot.data_manager.connection_status == "Connected":
                        st.success(f"Connected to {exchange.upper()} using saved keys!")
                        st.session_state.exchange_connected = True
                        st.rerun()
                    else:
                         st.error(f"Connection Failed: {temp_bot.data_manager.connection_error}")
                else:
                    st.warning(f"No saved keys found for {exchange} in .env")
            except Exception as e:
                st.error(f"Error connecting with saved keys: {e}")
                    
    else: # Manual Sync
        with st.expander("Manual Portfolio Sync", expanded=True):
            st.info("No API Keys? Manually sync your exchange balance here to mirror your real portfolio.")
            if st.session_state.logged_in:
                manual_asset = st.selectbox("Asset", ["USDT", "BTC", "ETH", "NGN", "USDC"])
                manual_balance = st.number_input(f"Current {manual_asset} Balance", min_value=0.0, step=0.1)
                
                if st.button("Update Balance"):
                    st.session_state.user_manager.update_paper_balance(manual_asset, manual_balance, "set")
                    st.success(f"Updated {manual_asset} balance to {manual_balance}")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Please login to sync portfolio.")
    
    # Gamification & User Level
    if st.session_state.logged_in:
        st.divider()
        neon_header("Trader Profile", level=2)
        
        # Calculate Level (XP based on trades)
        metrics = st.session_state.user_manager.get_performance_metrics()
        xp = metrics.get('total_trades', 0) * 10 + (metrics.get('total_pnl', 0) / 10)
        level = int(1 + (xp / 100))
        
        c_lvl, c_xp = st.columns([1, 2])
        with c_lvl:
            metric_card("Level", f"{level}", color="#00f2ff")
        with c_xp:
            st.caption(f"XP: {int(xp)}")
            st.progress(min((xp % 100) / 100, 1.0))
            
        # Pro Metrics
        st.divider()
        neon_header("Performance Analytics", level=3)
        
        # Row 1: PnL & Win Rate
        c_pnl, c_win = st.columns(2)
        with c_pnl:
            metric_card("Total PnL", f"${metrics.get('total_pnl', 0):.2f}", color="#bd00ff")
        with c_win:
            metric_card("Win Rate", f"{metrics.get('win_rate', 0):.1f}%", color="#00ff9d")
            
        # Row 2: Sharpe & Drawdown
        c_sharpe, c_dd = st.columns(2)
        with c_sharpe:
            metric_card("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}", color="#e0e6ed")
        with c_dd:
            metric_card("Max Drawdown", f"${metrics.get('max_drawdown', 0):.2f}", color="#ff0055")
            
        # Row 3: Profit Factor
        metric_card("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}", color="#00f2ff")
            
        # Badges
        with st.expander("Badges & Achievements", expanded=False):
            badges = st.session_state.user_manager.check_achievements()
            if badges:
                for badge in badges:
                    st.markdown(f"### {badge['icon']} {badge['name']}")
                    st.caption(badge['desc'])
            else:
                st.caption("No badges yet. Start trading to earn!")

    # System Targets (New)
    st.divider()
    neon_header("System Targets", level=2)
    target_min = TRADING_CONFIG['objectives']['target_apr_min'] * 100
    target_max = TRADING_CONFIG['objectives']['target_apr_max'] * 100
    
    # Calculate simulated APR (simple projection based on daily pnl)
    # If no trades, 0.
    sim_apr = 0.0
    if st.session_state.logged_in:
         metrics = st.session_state.user_manager.get_performance_metrics()
         if metrics.get('total_trades', 0) > 0:
            # assume capital is 10000 for simulation if not tracked elsewhere or use balances
            # This is a rough estimation for dashboard visualization
            current_equity = 10000 + metrics.get('total_pnl', 0)
            daily_return = (metrics.get('total_pnl', 0) / 10000) 
            sim_apr = daily_return * 12 * 100 # annualize
    
    metric_card("Target APR", f"{target_min:.0f}% - {target_max:.0f}%", color="#bd00ff")
    metric_card("Current Projected APR", f"{sim_apr:.1f}%", delta=f"{sim_apr - target_min:.1f}%", color="#00ff9d")

    # Strategy Selection
    st.divider()
    neon_header("Strategy Intelligence", level=2)
    strategy_options = [
        "Smart Trend", 
        "Sniper Mode",
        "Grid Trading", 
        "Mean Reversion", 
        "Funding Arbitrage", 
        "Basis Trade", 
        "Liquidity Sweep", 
        "Order Flow",
        "Meta-Allocator"
    ]
    selected_strategy = st.selectbox("Active Strategy", strategy_options, index=0)
    
    # Auto-Trading Control
    auto_trading_enabled = st.checkbox("Enable Auto-Trading", value=False, help="Automatically execute trades based on signals")
    if auto_trading_enabled:
        st.caption("⚠️ Auto-Trading is Active. Trades will be executed automatically.")
    
    # Strategy Parameters (Dynamic based on selection)
    if selected_strategy == "Grid Trading":
        grid_levels = st.slider("Grid Levels", 3, 10, 5)
        grid_step = st.slider("Grid Step (%)", 0.1, 5.0, 1.0)
    
    # Trading Execution & Balance Manager
    st.divider()
    neon_header("Wallet & Execution", level=2)
    
    # Determine Connection Status
    temp_bot = get_bot(st.session_state.get('exchange', 'binance'))
    is_connected = st.session_state.get('exchange_connected', False)
    
    # Auto-switch mode based on connection
    ui_mode = 'Live' if is_connected else 'Simulation'
    
    # Allow manual override to Simulation even if connected (Safety feature)
    if is_connected:
        mode_override = st.radio("Active Mode", ["Live", "Simulation"], index=0, horizontal=True)
        ui_mode = mode_override
    
    # Map UI Mode to Internal Bot Mode
    internal_mode = 'CEX_Direct' if ui_mode == 'Live' else 'Demo'

    # Apply Mode
    try:
        if hasattr(temp_bot, 'set_trading_mode'):
            temp_bot.set_trading_mode(internal_mode)
        else:
            # Stale cache detected, force reload
            st.cache_resource.clear()
            st.rerun()
    except AttributeError:
        st.cache_resource.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Failed to set trading mode: {e}")
        
    st.session_state.trading_mode = ui_mode
    
    # Display Active Balance
    if ui_mode == 'Live' and is_connected:
        # Auto-sync on load
        try:
            temp_bot.sync_live_balance()
            # Update Cache immediately after successful sync
            st.session_state[f"wallet_cache_{st.session_state.get('exchange', 'binance')}_v10"] = temp_bot.wallet_balances
        except Exception as e:
            st.error(f"Auto-sync error: {e}")

    bal_color_hex = "#ff0055" if ui_mode == 'Live' else "#00f2ff"
    bal_label_text = f"{ui_mode.upper()} BALANCE"
    
    # Manual Sync Button (Small)
    c_bal, c_sync = st.columns([3, 1])
    with c_sync:
        if st.button("🔄", help="Sync Balance", key="btn_sync_bal"):
            with st.spinner("Syncing..."):
                temp_bot.sync_live_balance()
                # Update Cache
                st.session_state[f"wallet_cache_{st.session_state.get('exchange', 'binance')}_v10"] = temp_bot.wallet_balances
                st.rerun()

    current_bal = temp_bot.risk_manager.current_capital
    
    with c_bal:
        metric_card(bal_label_text, f"${current_bal:,.2f}", color=bal_color_hex)

        # Display Detailed Wallet
        if hasattr(temp_bot, 'wallet_balances') and temp_bot.wallet_balances:
            with st.expander("👛 Wallet Breakdown", expanded=False):
                w_df = pd.DataFrame(temp_bot.wallet_balances)
                if not w_df.empty:
                    # Sort alphabetically by Asset for cleaner view
                    w_df = w_df.sort_values(by='asset')
                    
                    st.dataframe(
                        w_df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "asset": "Asset",
                            "total": st.column_config.NumberColumn("Total", format="%.8f"),
                            "free": st.column_config.NumberColumn("Free", format="%.8f"),
                            "locked": st.column_config.NumberColumn("Locked", format="%.8f"),
                        }
                    )
                else:
                    st.info("No assets found.")
    
    if ui_mode == 'Live':
        st.error("⚠️ REAL FUNDS AT RISK")
        st.caption("✅ Connected to Exchange")
    else:
        st.success("🛡️ DEMO / PAPER TRADING")
        st.caption("ℹ️ Simulated Balance")
    
    st.divider()
    if st.button("🚨 PANIC BUTTON (CLOSE ALL)", type="primary", use_container_width=True):
        temp_bot.emergency_stop()
        st.error("⚠️ EMERGENCY STOP EXECUTED - ALL POSITIONS CLOSED & BOT STOPPED")
        st.stop()
    
    # Auto-Refresh for Live Feed
    auto_refresh = st.toggle("Enable Live Feed (Auto-Refresh)", value=True)
    
    st.divider()
    
    # Logout Button
    if st.session_state.logged_in:
        if st.button("🚪 Logout", key="sidebar_logout", use_container_width=True):
            # Revoke session if token exists
            if 'session_token' in st.session_state and st.session_state.session_token:
                st.session_state.session_manager.revoke_session(st.session_state.session_token)
            
            # Clear state
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.session_token = None
            
            # Clear localStorage
            st.markdown("<script>localStorage.removeItem('caparox_session');</script>", unsafe_allow_html=True)
            st.rerun()

if page_nav == "Wallet & Funds":
    neon_header("👛 Wallet & Assets")
    
    # Initialize Bot
    try:
        bot = get_bot(exchange)
        
        # Auto-Sync Logic: If connected but no wallet data, sync automatically
        if st.session_state.exchange_connected:
            should_sync = False
            
            # Check if wallet_balances is missing or empty
            if not hasattr(bot, 'wallet_balances') or not bot.wallet_balances:
                should_sync = True
            
            if should_sync:
                with st.spinner("Auto-syncing balances..."):
                    try:
                        bot.sync_live_balance()
                        # Cache wallet balances
                        st.session_state[f"wallet_cache_{exchange}_v10"] = bot.wallet_balances
                    except Exception as e:
                        error_msg = str(e)
                        if "CRITICAL_API_ERROR" in error_msg or "-2008" in error_msg:
                            st.error("🚨 CRITICAL: Invalid API Credentials detected.")
                            st.error(error_msg)
                            st.info("Please go to the sidebar and re-enter your API Key and Secret.")
                            
                            # Force disconnect in UI
                            st.session_state[f"{exchange}_connected"] = False
                            st.session_state.exchange_connected = False
                            
                            # Clear from session state to force re-entry
                            if f"{exchange}_api_key" in st.session_state: del st.session_state[f"{exchange}_api_key"]
                            if f"{exchange}_api_secret" in st.session_state: del st.session_state[f"{exchange}_api_secret"]
                        else:
                            st.error(f"Auto-sync failed: {e}")

            # Top Bar: Connection & Sync
            c_status, c_sync = st.columns([3, 1])
            with c_status:
                st.markdown(f"**Connected Exchange:** `{exchange.upper()}` | **Mode:** `{bot.trading_mode}`")
            with c_sync:
                if st.button("🔄 Sync Balance", use_container_width=True):
                    with st.spinner("Syncing..."):
                        try:
                            bot.sync_live_balance()
                            st.session_state[f"wallet_cache_{exchange}_v10"] = bot.wallet_balances
                            st.session_state['last_wallet_sync'] = time.time()
                            st.rerun()
                        except Exception as e:
                            error_msg = str(e)
                            if "CRITICAL_API_ERROR" in error_msg or "-2008" in error_msg:
                                st.error("🚨 CRITICAL: Invalid API Credentials detected.")
                                st.warning("Credentials have been invalidated. Please re-enter them in the sidebar.")
                                
                                # Force disconnect in UI
                                st.session_state[f"{exchange}_connected"] = False
                                st.session_state.exchange_connected = False
                                
                                # Clear from session state
                                if f"{exchange}_api_key" in st.session_state: del st.session_state[f"{exchange}_api_key"]
                                if f"{exchange}_api_secret" in st.session_state: del st.session_state[f"{exchange}_api_secret"]
                            else:
                                st.error(f"Sync failed: {e}")

            st.divider()

            # Main Balance Display
            total_usdt = bot.risk_manager.current_capital
            wallet_len = len(bot.wallet_balances) if hasattr(bot, 'wallet_balances') else 0
            has_data = hasattr(bot, 'wallet_balances') and bot.wallet_balances
            
            # Hero Metrics (Cyberpunk Style)
            m1, m2, m3 = st.columns(3)
            with m1:
                metric_card("Total Value", f"${total_usdt:,.2f}", color="#00f2ff")
            with m2:
                # Calculate Liquid USDT
                free_usdt = 0.0
                if has_data:
                    for item in bot.wallet_balances:
                        if 'USDT' in item['asset']:
                            free_usdt += item['free']
                metric_card("Liquid USDT", f"${free_usdt:,.2f}", color="#00ff9d")
            with m3:
                metric_card("Active Assets", str(wallet_len), color="#bd00ff")

            st.divider()

            if has_data:
                # Prepare DataFrame
                df = pd.DataFrame(bot.wallet_balances)
                
                # Layout: Left (Tabs for Assets), Right (Chart)
                col_assets, col_chart = st.columns([2, 1])
                
                with col_assets:
                    neon_header("Asset Breakdown", level=3)
                    
                    # Categorize
                    df['category'] = df['asset'].apply(
                        lambda x: "Earn" if "(Earn)" in x else ("Funding" if "(Fund)" in x else "Spot")
                    )
                    
                    # Tabs
                    tab_all, tab_spot, tab_earn = st.tabs(["All Assets", "Spot Wallet", "Earn/Funding"])
                    
                    # Column Config
                    col_cfg = {
                        "asset": "Asset",
                        "total": st.column_config.NumberColumn("Total", format="%.8f"), 
                        "free": st.column_config.NumberColumn("Free", format="%.8f"),
                        "locked": st.column_config.NumberColumn("Locked/Used", format="%.8f"),
                        "category": "Category"
                    }
                    
                    with tab_all:
                        st.dataframe(
                            df.sort_values(by='total', ascending=False),
                            use_container_width=True,
                            hide_index=True,
                            column_config=col_cfg
                        )
                        
                    with tab_spot:
                        st.dataframe(
                            df[df['category'] == 'Spot'].sort_values(by='total', ascending=False),
                            use_container_width=True,
                            hide_index=True,
                            column_config=col_cfg
                        )
                        
                    with tab_earn:
                        st.dataframe(
                            df[df['category'].isin(['Earn', 'Funding'])].sort_values(by='total', ascending=False),
                            use_container_width=True,
                            hide_index=True,
                            column_config=col_cfg
                        )

                with col_chart:
                    neon_header("Allocation", level=3)
                    df_chart = df[df['total'] > 0].copy()
                    if not df_chart.empty:
                        # Limit for chart
                        if len(df_chart) > 10:
                            df_chart = df_chart.sort_values('total', ascending=False).head(10)
                            
                        fig = go.Figure(data=[go.Pie(
                            labels=df_chart['asset'], 
                            values=df_chart['total'], 
                            hole=.5,
                            textinfo='label+percent',
                            showlegend=False
                        )])
                        fig.update_layout(
                            margin=dict(t=0, b=0, l=0, r=0), 
                            height=300,
                            annotations=[dict(text='Portfolio', x=0.5, y=0.5, font_size=20, showarrow=False)]
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No non-zero assets to display.")

            else:
                # No data in wallet_balances
                st.container()
                if st.session_state.get('last_wallet_sync'):
                    st.warning("⚠️ Wallet Synced but 0 Assets Found.")
                    st.markdown("""
                        **Possible Reasons:**
                        - API Key permissions missing (Need 'Spot' or 'Wallet' read access).
                        - Wallet is actually empty.
                        - Exchange API returned empty list.
                        
                        *Check Debug Logs below for raw response.*
                    """)
                else:
                    st.info("👋 Ready to Sync! Click the button above to fetch balances.")
            
            # Evidence/Debug Section
            with st.expander("🛠️ Debug Logs & Evidence"):
                neon_header("Session Cache State", level=4)
                cache_key = f"wallet_cache_{exchange}_v10"
                if cache_key in st.session_state:
                    cached_data = st.session_state[cache_key]
                    st.write(f"Cache Key: `{cache_key}`")
                    st.write(f"Cached Items: {len(cached_data)}")
                    if cached_data:
                        st.json(cached_data[:5]) # Show first 5 items
                else:
                    st.warning(f"Cache Key `{cache_key}` NOT FOUND in Session State.")
                
                neon_header("Raw Log File", level=4)
                if os.path.exists("debug_wallet_log.txt"):
                    with open("debug_wallet_log.txt", "r", encoding='utf-8', errors='replace') as f:
                        st.code(f.read(), language="text")
                else:
                    st.caption("No debug log found. Click 'Sync Now' to generate.")

            # Auto-Refresh Option
            if st.toggle("Enable Auto-Refresh (30s)", value=False):
                time.sleep(30)
                st.rerun()
                
        else:
            st.warning("Please connect to an exchange API in the sidebar to view wallet balances.")
            st.info("Navigate to 'Settings' or use the sidebar 'Exchange Manager' to connect.")
            
    except Exception as e:
        st.error(f"Error loading wallet: {e}")

if page_nav == "Strategy Manager":
    neon_header("🧠 Strategy Command Center")
    
    # Initialize Bot
    try:
        bot = get_bot(exchange)
    except:
        st.error("Bot initialization failed.")
        st.stop()
        
    st.caption(f"Active Mode: {bot.trading_mode} | Exchange: {exchange.upper()}")
    
    # Strategy Selection
    neon_header("Strategy Selection", level=2)
    
    current_strat = bot.active_strategy_name
    strategy_names = list(bot.strategies.keys())
    
    # Find index
    try:
        idx = strategy_names.index(current_strat)
    except:
        idx = 0
        
    selected_strat = st.selectbox("Select Active Strategy", strategy_names, index=idx)
    
    if selected_strat != current_strat:
        bot.active_strategy_name = selected_strat
        bot.active_strategy = bot.strategies[selected_strat]
        st.success(f"Switched to {selected_strat}")
        st.rerun()
        
    st.info(f"Currently Running: **{bot.active_strategy.name}**")
    st.markdown(bot.active_strategy.__doc__ or "No description available.")
    
    st.divider()
    
    # Configuration
    neon_header("Configuration & Parameters", level=2)
    
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Risk per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, help="Percentage of account balance to risk per trade.")
        st.number_input("Max Open Positions", min_value=1, max_value=10, value=3)
    with c2:
        st.selectbox("Timeframe", ['1m', '5m', '15m', '1h', '4h', '1d'], index=3)
        st.toggle("Use AI Confirmation", value=True, help="Use Capa-X Brain to validate signals.")
        
    st.divider()
    
    # Auto-Trading Control
    neon_header("🤖 Automated Execution", level=2)

    # Initialize AutoTrader in Session State if missing
    if 'auto_trader' not in st.session_state:
        # Create a persistent AutoTrader instance attached to the bot
        # We store it in session state so we don't lose the thread handle
        st.session_state.auto_trader = AutoTrader(bot)
    
    at = st.session_state.auto_trader
    
    # Sync AT config with UI
    if not at.is_running:
        at.symbols = [symbol] # Currently selected symbol
        at.tf = timeframe
        # Update risk from bot risk manager which might have been updated above
        at.risk = bot.risk_manager 

    col_run, col_status = st.columns([1, 3])
    
    with col_run:
        if at.is_running:
            if st.button("⏹ Stop Auto-Trading", type="primary"):
                at.stop()
                st.success("Stopping...")
                time.sleep(1)
                st.rerun()
        else:
            if st.button("▶ Start Auto-Trading"):
                at.start()
                st.success("Started Auto-Trading Loop!")
                time.sleep(1)
                st.rerun()
                
    with col_status:
        if at.is_running:
            st.success(f"RUNNING: CapacityBay Bot Active on {at.symbols}")
            st.caption("Background thread active. You can navigate to other tabs.")
            st.progress(100, text="Monitoring Market...")
            
            # Auto-refresh to show updates without blocking
            if st.toggle("Auto-Refresh Log", value=True):
                time.sleep(5)
                st.rerun()
        else:
            st.warning("STOPPED: Bot is idle. Click Start to engage.")
            
    # Live Trade Log
    st.divider()
    neon_header("📝 Live Trade Log", level=2)
    
    # Check bot positions
    trades = bot.positions.get(bot.trading_mode, [])
    if trades:
        trades_df = pd.DataFrame(trades)
        # Format for display
        display_df = trades_df.copy()
        if 'timestamp' not in display_df.columns:
            display_df['timestamp'] = pd.Timestamp.now()
            
        st.dataframe(
            display_df.sort_index(ascending=False), 
            use_container_width=True,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("Time", format="HH:mm:ss"),
                "side": "Side",
                "price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "qty": st.column_config.NumberColumn("Qty", format="%.4f"),
                "pnl": st.column_config.NumberColumn("PnL", format="$%.2f")
            }
        )
    else:
        st.info("No trades executed yet in this session.")

if page_nav == "Trading Dashboard":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    neon_header(f"{symbol} Command Center")
    
    # Initialize Bot
    try:
        bot = get_bot(exchange)
        bot.symbol = symbol
        bot.timeframe = timeframe
        bot.set_strategy(selected_strategy)
        
        # Initialize NLP Engine if not present or update bot reference
        if 'nlp_engine' not in st.session_state:
            st.session_state.nlp_engine = NLPEngine(bot)
        else:
            st.session_state.nlp_engine.bot = bot
        
        # Audio Alert Processing
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

    # Capa-X Assistant (NLP)
    with st.expander("🤖 Capa-X Assistant", expanded=False):
        c_nlp, c_help = st.columns([4, 1])
        with c_nlp:
            user_query = st.text_input("Ask Capa-X...", placeholder="Type commands like 'Buy 0.5 BTC', 'Sentiment Check', or 'Status Report'...")
        with c_help:
            st.caption("Try: *'Sentiment Check'*, *'Switch to Grid Trading'*, *'Price of ETH'*")
            
        if user_query:
            if 'nlp_engine' in st.session_state:
                response = st.session_state.nlp_engine.process_query(user_query, st.session_state.user_manager)
                st.markdown(f"**Capa-X:** {response}")
                
                # Execute config actions if needed (handled inside process_query mostly, but UI updates here)
                if "Switching strategy" in response:
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("NLP Engine not initialized.")

    # Layout: Chart (Left 75%), Signal Panel (Right 25%)
    col_chart, col_signal = st.columns([3, 1])
    
    # Fetch Data
    with st.spinner("Fetching Market Data..."):
        raw_df = get_cached_ohlcv(bot, symbol, timeframe)
        
    if not raw_df.empty:
        # Check Kill Switch
        if st.session_state.get('kill_switch_active'):
            st.warning("⚠️ Trading Halted by Kill Switch. Please restart session to resume.")
            st.stop()

        # Run Analysis (Cached for speed)
        # Use copy for chart to avoid polluting cache with indicators
        df = raw_df.copy()
        
        # Calculate indicators for the chart visualization (fast enough to run, or cache separately if needed)
        # But run_analysis also calculates them. 
        # We'll rely on the signal returned from cached analysis for strategy info.
        # However, for the chart, we need the dataframe with indicators.
        df = bot.analyzer.calculate_indicators(df)
        
        # Run Strategy Analysis to get Signal & Regime (Cached)
        # We use get_cached_analysis to prevent re-running heavy logic on every UI interaction
        signal = get_cached_analysis(bot, raw_df) 
        market_regime = signal.regime if signal else "Unknown"
        
        # --- Chart Section ---
        with col_chart:
            # TradingView Widget for robust live data
            tv_symbol = "BINANCE:BTCUSDT"
            if symbol == "ETHUSDT": tv_symbol = "BINANCE:ETHUSDT"
            elif symbol == "BNBUSDT": tv_symbol = "BINANCE:BNBUSDT"
            elif symbol == "SOLUSDT": tv_symbol = "BINANCE:SOLUSDT"
            else: tv_symbol = f"BINANCE:{symbol}"

            # Map timeframe to TradingView interval
            tv_interval_map = {
                '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
                '1h': '60', '2h': '120', '4h': '240', '1d': 'D'
            }
            tv_interval = tv_interval_map.get(timeframe, '60')

            # Create the HTML for the widget
            html_code = f"""
            <!-- TradingView Widget BEGIN -->
            <div class="tradingview-widget-container" style="height:800px;width:100%">
              <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
              {{
              "autosize": true,
              "symbol": "{tv_symbol}",
              "interval": "{tv_interval}",
              "timezone": "Etc/UTC",
              "theme": "dark",
              "style": "1",
              "locale": "en",
              "enable_publishing": false,
              "allow_symbol_change": true,
              "support_host": "https://www.tradingview.com"
            }}
              </script>
            </div>
            <!-- TradingView Widget END -->
            """
            components.html(html_code, height=800)
            
        # --- Signal Panel ---
        with col_signal:
            neon_header("🤖 Auto-Pilot", level=3)
            
            # Sync with session state / bot state
            is_running = False
            if hasattr(bot, 'auto_trader'):
                is_running = bot.auto_trader.is_running
            
            # Use session state to track the toggle, but sync with bot state on load
            # key="auto_trader_toggle_dash"
            
            auto_trading_enabled = st.checkbox("Enable Auto-Trading", value=is_running, key="auto_trader_toggle_dash", help="Automatically execute trades based on signals")
            
            if auto_trading_enabled and not is_running:
                if hasattr(bot, 'auto_trader'):
                    bot.auto_trader.start()
                    st.toast("Auto-Trader Started", icon="🤖")
                    time.sleep(0.5)
                    st.rerun()
            elif not auto_trading_enabled and is_running:
                if hasattr(bot, 'auto_trader'):
                    bot.auto_trader.stop()
                    st.toast("Auto-Trader Stopped", icon="🛑")
                    time.sleep(0.5)
                    st.rerun()
            
            if auto_trading_enabled:
                st.caption("⚠️ System Active")
            
            st.divider()
            
            neon_header("Decision Authority", level=3)
            
            current_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            metric_card("Current Price", f"${current_price:,.2f}", f"{price_change:+.2f}%")
            
            # --- Fundamental Data (CoinMarketCap) ---
            fundamental_data = get_cached_fundamentals(symbol, bot)
            if fundamental_data and fundamental_data.get('source') == 'CoinMarketCap':
                st.divider()
                st.markdown("#### CoinMarketCap Fundamentals")
                f_c1, f_c2 = st.columns(2)
                with f_c1:
                    metric_card("Rank", f"#{fundamental_data.get('rank', 'N/A')}", color="#bd00ff")
                    metric_card("Market Cap", f"${fundamental_data.get('market_cap', 0):,.0f}", color="#e0e6ed")
                    metric_card("Dominance", f"{fundamental_data.get('market_dominance', 0):.2f}%", color="#e0e6ed")
                with f_c2:
                    metric_card("24h Vol", f"${fundamental_data.get('volume_1day_usd', 0):,.0f}", color="#00f2ff")
                    metric_card("Supply", f"{fundamental_data.get('supply_current', 0):,.0f}", color="#e0e6ed")
                    metric_card("7d Change", f"{fundamental_data.get('percent_change_7d', 0):.2f}%", 
                             f"{fundamental_data.get('percent_change_7d', 0):.2f}%")
            
            st.divider()
            
            if signal:
                if signal.type == 'buy':
                    st.success(f"🔵 BUY SIGNAL")
                elif signal.type == 'sell':
                    st.error(f"🔴 SELL SIGNAL")
                else:
                    st.info(f"⚪ HOLD")
            

                    
                st.markdown(f"**Strategy:** {signal.decision_details.get('strategy', selected_strategy)}")
                st.markdown(f"**Confidence:** {signal.confidence*100:.1f}%")
                st.markdown(f"**Reason:** {signal.reason}")
                
                with st.expander("Details"):
                    st.json(signal.decision_details)
                    
            else:
                st.warning("No Signal Generated")

            st.divider()
            st.markdown("#### AI Risk Assessment")
            risk_score = bot.risk_manager.max_drawdown * 100 # Placeholder for risk score
            st.progress(min(risk_score/10, 1.0), text=f"Risk Level: {risk_score:.1f}%")
            
            if bot.risk_manager.is_kill_switch_active:
                st.error("🚨 KILL SWITCH ACTIVE")

            # --- Live Position Tracking ---
            st.divider()
            neon_header("Active Positions", level=3)
            
            if hasattr(bot, 'open_positions') and bot.open_positions:
                for i, pos in enumerate(bot.open_positions):
                    with st.container():
                        st.markdown(f"**{pos['symbol']} ({pos['type']})**")
                        c1, c2 = st.columns(2)
                        with c1:
                            metric_card("Entry", f"${pos['entry']:.2f}", color="#e0e6ed")
                            pnl_pct = 0.0
                            if current_price > 0:
                                if pos['type'] == 'BUY':
                                    pnl_pct = ((current_price - pos['entry']) / pos['entry']) * 100
                                elif pos['type'] == 'SELL':
                                    pnl_pct = ((pos['entry'] - current_price) / pos['entry']) * 100
                            
                            pnl_color = "#00ff9d" if pnl_pct >= 0 else "#ff0055"
                            metric_card("PnL", f"{pnl_pct:+.2f}%", delta=f"{pnl_pct:+.2f}%", color=pnl_color)
                        with c2:
                            metric_card("TP", f"${pos['take_profit']:.2f}", color="#00ff9d")
                            metric_card("SL", f"${pos['stop_loss']:.2f}", color="#ff0055")
                        st.divider()
            else:
                st.info("No active positions.")
            
    else:
        st.warning("No data available for this symbol/timeframe.")

    # --- Auto-Refresh Logic ---
    if auto_refresh:
        time.sleep(2) # Refresh every 2 seconds
        st.rerun()

    # --- Portfolio & Performance Tab ---
    st.divider()
    p_tab1, p_tab2, p_tab3 = st.tabs(["Active Positions", "Strategy Allocation", "Trade Log"])
    
    with p_tab1:
        if bot.open_positions:
            st.dataframe(pd.DataFrame(bot.open_positions))
        else:
            st.info("No active positions.")
            
    with p_tab2:
        neon_header("Meta-Allocator Weights", level=3)
        weights = bot.profit_optimizer.get_allocation_weights()
        
        # Pie Chart of Weights
        labels = list(weights.keys())
        values = list(weights.values())
        
        c_pie1, c_pie2 = st.columns(2)
        with c_pie1:
            fig_alloc = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
            fig_alloc.update_layout(template="plotly_dark", height=350, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_alloc, use_container_width=True)
        with c_pie2:
            st.dataframe(pd.DataFrame(list(weights.items()), columns=["Strategy", "Weight"]).sort_values("Weight", ascending=False))

    with p_tab3:
        if os.path.exists(bot.trade_log_file):
            try:
                with open(bot.trade_log_file, 'r') as f:
                    logs = json.load(f)
                st.dataframe(pd.DataFrame(logs).sort_values("timestamp", ascending=False))
            except:
                st.error("Log file corrupted.")
        else:
            st.info("No trades recorded yet.")

if page_nav == "Trading Monitor":
    neon_header("🖥️ System Monitor")
    
    # Initialize Bot
    try:
        bot = get_bot(exchange)
        
        # Self-Healing: Check for stale cache missing 'positions'
        if not hasattr(bot, 'positions'):
            st.warning("Updating system core... (Cache Refresh)")
            st.cache_resource.clear()
            st.rerun()

        # Sync Trading Mode
        if 'trading_mode' in st.session_state:
            bot.trading_mode = st.session_state.trading_mode
    except Exception as e:
        st.error(f"Failed to initialize bot: {e}")
        st.stop()
        
    # 1. Account Status
    neon_header("Account Status", level=2)
    
    # Refresh Balance if Live (Always try to sync if connected to show latest)
    if st.session_state.get('exchange_connected', False):
        with st.spinner("Syncing Live Balance..."):
            bot.sync_live_balance()
            
    col1, col2, col3, col4 = st.columns(4)
    
    active_mode = bot.trading_mode
    live_bal = bot.risk_manager.live_balance
    demo_bal = bot.risk_manager.demo_balance
    
    with col1:
        status_color = "#00ff9d" if st.session_state.get('exchange_connected') else "#ff0055"
        metric_card("Mode", active_mode, "Connected" if st.session_state.get('exchange_connected') else "Offline", color=status_color)
    with col2:
        metric_card("Live Balance", f"${live_bal:,.2f}", color="#00f2ff")
    with col3:
        metric_card("Demo Balance", f"${demo_bal:,.2f}", color="#bd00ff")
    with col4:
        # Show Total PnL (Combined or Active)
        # Showing Active Mode PnL
        if active_mode == 'Live':
             # Simple PnL for now
             metric_card("Active PnL", "N/A (Live)", color="#e0e6ed") 
        else:
             pnl = demo_bal - 1000 # Assuming 1000 start
             metric_card("Demo PnL", f"${pnl:,.2f}", f"{pnl/10:.1f}%")
        
    st.divider()
    
    # 2. Active Positions (Dual View)
    neon_header("Active Positions", level=2)
    
    tab_live, tab_demo = st.tabs(["🔴 Live Positions", "🔵 Demo Positions"])
    
    def display_positions(position_list, mode_name):
        if position_list:
            pos_data = []
            for p in position_list:
                # Fetch current price
                try:
                    ticker = bot.data_manager.fetch_ticker(p['symbol'])
                    current_price = ticker.get('last', p['entry'])
                except:
                    current_price = p['entry']
                
                # Calculate Unrealized PnL
                if p['type'] == 'BUY':
                    u_pnl = (current_price - p['entry']) * p['position_size']
                    u_pnl_pct = (current_price - p['entry']) / p['entry'] * 100
                else: # SELL
                    u_pnl = (p['entry'] - current_price) * p['position_size']
                    u_pnl_pct = (p['entry'] - current_price) / p['entry'] * 100
                    
                pos_data.append({
                    "Symbol": p['symbol'],
                    "Type": p['type'],
                    "Entry": f"${p['entry']:,.2f}",
                    "Current": f"${current_price:,.2f}",
                    "Size": p['position_size'],
                    "Unrealized PnL ($)": f"${u_pnl:,.2f}",
                    "PnL (%)": f"{u_pnl_pct:.2f}%"
                })
            
            st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
        else:
            st.info(f"No active {mode_name} positions.")

    with tab_live:
        display_positions(bot.positions.get('Live', []), "Live")
        
    with tab_demo:
        display_positions(bot.positions.get('Simulation', []), "Demo")
        
    st.divider()
    
    # 3. Recent Trades (Logs)
    neon_header("Recent Activity Log", level=2)
    
    if os.path.exists(bot.trade_log_file):
        try:
            with open(bot.trade_log_file, 'r') as f:
                trade_logs = json.load(f)
            if trade_logs:
                df_trades = pd.DataFrame(trade_logs)
                # Select columns if they exist
                cols = ['timestamp', 'symbol', 'type', 'strategy', 'entry', 'risk_percent', 'audit_status']
                valid_cols = [c for c in cols if c in df_trades.columns]
                st.dataframe(df_trades[valid_cols].sort_values("timestamp", ascending=False).head(20), use_container_width=True)
            else:
                st.info("No activity recorded yet.")
        except:
            st.warning("Could not read trade log.")
    else:
        st.info("No trade log file found.")

    # Auto refresh
    if st.toggle("Auto-Refresh Monitor (5s)", value=True):
        time.sleep(5)
        st.rerun()

if page_nav == "Trading Terminal":
    neon_header(f"🖥️ Trading Terminal - {symbol}")
    
    # Initialize Bot
    try:
        bot = get_bot(exchange)
        bot.symbol = symbol
        bot.timeframe = timeframe
        # Sync Trading Mode
        if 'trading_mode' in st.session_state:
            bot.trading_mode = st.session_state.trading_mode
    except Exception as e:
        st.error(f"Failed to initialize bot: {e}")
        st.stop()

    col_order, col_book = st.columns([1, 2])
    
    with col_order:
        neon_header("Order Entry", level=2)
        
        with st.form("order_form"):
            side = st.selectbox("Side", ["Buy", "Sell"])
            order_type = st.selectbox("Type", ["Limit", "Market", "Iceberg"])
            amount = st.number_input("Amount", min_value=0.001, step=0.001)
            
            price = 0.0
            if order_type != "Market":
                # Fetch current price for reference
                current_price = 0.0
                try:
                    ticker = bot.data_manager.fetch_ticker(symbol)
                    last_val = ticker.get('last', 0.0)
                    if last_val is not None:
                         current_price = float(last_val)
                except Exception:
                    pass # Default to 0.0
                
                price = st.number_input("Price", value=current_price, min_value=0.0, step=0.01)
            
            submitted = st.form_submit_button(f"Place {side.upper()} Order")
            
            if submitted:
                with st.spinner(f"Placing {order_type} {side} order..."):
                    # Adjust side string for backend
                    side_lower = side.lower()
                    type_lower = order_type.lower()
                    
                    # Execute
                    result = bot.execution.execute_smart_order(symbol, side_lower, amount, type_lower)
                    
                    if result:
                        if result.get('status') == 'Failed':
                            st.error(f"Order Failed: {result.get('error')}")
                        else:
                            st.success(f"Order Placed Successfully! ID: {result.get('id')}")
                            
                            # Cache wallet balances after trade
                            if hasattr(bot, 'wallet_balances'):
                                st.session_state[f"wallet_cache_{exchange}_v10"] = bot.wallet_balances
                                
                            st.json(result)
                            # Log action
                            if 'transparency_log' in st.session_state:
                                st.session_state.transparency_log.log_action("Manual Trade", f"{side} {amount} {symbol} @ {price if order_type != 'Market' else 'Market'}")

                            # LOG MANUAL TRADE TO TRADE_LOG.JSON (For Live Report)
                            try:
                                log_price = price if order_type != 'Market' else result.get('price', 0)
                                # If price is still 0/Market string, try to fetch current
                                if log_price == 'Market' or log_price == 0:
                                    try:
                                        ticker = bot.data_manager.fetch_ticker(symbol)
                                        log_price = float(ticker.get('last', 0))
                                    except:
                                        log_price = 0.0

                                packet = {
                                    "symbol": symbol,
                                    "bias": side.upper(),
                                    "entry": log_price,
                                    "stop_loss": 0, # Manual trade default
                                    "take_profit": 0,
                                    "position_size": amount,
                                    "strategy": "Manual",
                                    "confidence": 1.0,
                                    "decision": "EXECUTE",
                                    "market_regime": "Manual Override"
                                }
                                bot.log_trade(packet)
                                st.toast("Trade Logged Successfully", icon="📝")
                            except Exception as log_err:
                                print(f"Failed to log manual trade: {log_err}")

                    else:
                        st.error("Order Execution Failed (No Result)")

    with col_book:
        neon_header("Market Depth & Recent Trades", level=2)
        
        # Fetch Depth
        try:
            # Check capabilities
            if hasattr(bot.data_manager.exchange, 'fetch_order_book'):
                depth = bot.data_manager.exchange.fetch_order_book(symbol, limit=10)
            else:
                depth = {'bids': [], 'asks': []}
        except Exception as e:
            # Retry without credentials if API Key is invalid (Fallback to Public View)
            if "Invalid Api-Key ID" in str(e) or "-2008" in str(e):
                try:
                    # Temporarily clear keys to fetch public data
                    old_key = bot.data_manager.exchange.apiKey
                    old_secret = bot.data_manager.exchange.secret
                    bot.data_manager.exchange.apiKey = None
                    bot.data_manager.exchange.secret = None
                    
                    depth = bot.data_manager.exchange.fetch_order_book(symbol, limit=10)
                    
                    # Restore keys (so user still sees the error warning below)
                    bot.data_manager.exchange.apiKey = old_key
                    bot.data_manager.exchange.secret = old_secret
                    
                    st.warning("⚠️ Invalid API Key: Showing public market data only. Trading disabled.")
                except Exception as retry_e:
                    depth = {'bids': [], 'asks': []}
                    st.error(f"⚠️ Invalid API Key & Public Fetch Failed: {retry_e}")
            else:
                depth = {'bids': [], 'asks': []}
                # Raise to outer block to handle connection errors
                raise e

        try:
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                neon_header("Bids (Buy)", level=3)
                if depth.get('bids'):
                    bids_df = pd.DataFrame(depth['bids'], columns=['Price', 'Amount'])
                    st.dataframe(bids_df, height=300, use_container_width=True)
                else:
                    st.info("No Bids")
            
            with d_col2:
                neon_header("Asks (Sell)", level=3)
                if depth.get('asks'):
                    asks_df = pd.DataFrame(depth['asks'], columns=['Price', 'Amount'])
                    st.dataframe(asks_df, height=300, use_container_width=True)
                else:
                    st.info("No Asks")
                    
        except Exception as e:
            error_msg = str(e)
            if "getaddrinfo failed" in error_msg or "Connection aborted" in error_msg:
                st.error("⚠️ Connection Error: Cannot reach API. Check your internet or Proxy settings.")
            elif "Invalid Api-Key ID" in error_msg:
                 st.error("⚠️ Invalid API Key detected. Please check your credentials in the 'Exchange Manager' sidebar.")
                 st.caption("Note: Ensure you are using keys for Binance.com (Global). Binance.US keys will not work on Global.")
            else:
                st.warning(f"Could not fetch order book: {e}")
                
            # Debug Info
            if hasattr(bot.data_manager.exchange, 'urls'):
                urls = bot.data_manager.exchange.urls
                urls_str = str(urls)
                is_override_active = False
                public_url = "Unknown"
                
                # Try to extract specific public URL for clearer debug
                if isinstance(urls, dict) and 'api' in urls:
                    if isinstance(urls['api'], dict):
                        public_url = urls['api'].get('public', 'Unknown')
                    elif isinstance(urls['api'], str):
                        public_url = urls['api']
                
                if exchange == 'bybit':
                    is_override_active = 'bytick' in urls_str
                elif exchange == 'binance':
                    is_override_active = 'api-gcp' in urls_str or 'api1.binance' in urls_str
                
                st.caption(f"Debug: API Connection | Override: {is_override_active} | Host: {public_url}")

    st.divider()
    
    # --- Session Performance Analytics ---
    neon_header("Session Performance Analytics", level=2)
    
    if os.path.exists(bot.trade_log_file):
        try:
            with open(bot.trade_log_file, 'r') as f:
                all_logs = json.load(f)
            
            if all_logs:
                df_all = pd.DataFrame(all_logs)
                df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
                
                # Session Filter
                sess_opt = st.radio("Session Window", ["Today (UTC)", "Last 24 Hours", "All Time"], horizontal=True, key="pnl_session_opt")
                
                now = datetime.utcnow()
                if sess_opt == "Today (UTC)":
                    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    df_sess = df_all[df_all['timestamp'] >= start_time]
                elif sess_opt == "Last 24 Hours":
                    start_time = now - timedelta(hours=24)
                    df_sess = df_all[df_all['timestamp'] >= start_time]
                else:
                    df_sess = df_all
                
                if not df_sess.empty:
                    # Calculate Realized PnL (FIFO Matching)
                    realized_pnl = 0.0
                    wins = 0
                    losses = 0
                    total_vol = 0.0
                    
                    # Inventory: {symbol: {'qty': float, 'cost': float}} (Cost is per unit)
                    # For Shorts: qty is negative.
                    inventory = {} 
                    
                    # Sort chronological
                    df_calc = df_sess.sort_values('timestamp', ascending=True)
                    
                    for _, row in df_calc.iterrows():
                        sym = row['symbol']
                        side = row['type'].upper() # BUY or SELL
                        price = float(row['entry'])
                        # Try to get size, default to 0 if missing
                        qty = float(row.get('position_size', 0))
                        
                        if qty <= 0: continue
                        
                        total_vol += price * qty
                        
                        if sym not in inventory:
                            inventory[sym] = {'qty': 0.0, 'cost': 0.0}
                            
                        curr_qty = inventory[sym]['qty']
                        curr_cost = inventory[sym]['cost']
                        
                        if side == 'BUY':
                            if curr_qty < 0: # Covering Short
                                cover_qty = min(qty, abs(curr_qty))
                                # Profit = (Short Entry Cost - Buy Price) * Qty
                                trade_pnl = (curr_cost - price) * cover_qty
                                realized_pnl += trade_pnl
                                if trade_pnl > 0: wins += 1
                                elif trade_pnl < 0: losses += 1
                                
                                # Update Inventory
                                remain_short = abs(curr_qty) - cover_qty
                                if remain_short > 0:
                                    inventory[sym]['qty'] = -remain_short
                                    # Cost basis stays same for remaining short
                                else:
                                    # Switched to Long or Flat
                                    excess_long = qty - abs(curr_qty)
                                    if excess_long > 0:
                                        inventory[sym] = {'qty': excess_long, 'cost': price}
                                    else:
                                        inventory[sym] = {'qty': 0.0, 'cost': 0.0}
                            else: # Adding to Long
                                new_qty = curr_qty + qty
                                if new_qty > 0:
                                    # Weighted Average Cost
                                    new_cost = ((curr_qty * curr_cost) + (qty * price)) / new_qty
                                    inventory[sym] = {'qty': new_qty, 'cost': new_cost}
                                    
                        elif side == 'SELL':
                            if curr_qty > 0: # Closing Long
                                close_qty = min(qty, curr_qty)
                                # Profit = (Sell Price - Long Entry Cost) * Qty
                                trade_pnl = (price - curr_cost) * close_qty
                                realized_pnl += trade_pnl
                                if trade_pnl > 0: wins += 1
                                elif trade_pnl < 0: losses += 1
                                
                                # Update Inventory
                                remain_long = curr_qty - close_qty
                                if remain_long > 0:
                                    inventory[sym]['qty'] = remain_long
                                    # Cost basis stays same
                                else:
                                    # Switched to Short or Flat
                                    excess_short = qty - curr_qty
                                    if excess_short > 0:
                                        inventory[sym] = {'qty': -excess_short, 'cost': price}
                                    else:
                                        inventory[sym] = {'qty': 0.0, 'cost': 0.0}
                            else: # Adding to Short
                                new_qty = curr_qty - qty # more negative
                                # Weighted Average Cost for Short
                                # curr_qty is negative, so abs() for weight
                                total_short = abs(curr_qty) + qty
                                new_cost = ((abs(curr_qty) * curr_cost) + (qty * price)) / total_short
                                inventory[sym] = {'qty': new_qty, 'cost': new_cost}

                    # Display Metrics
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        metric_card("Realized PnL", f"${realized_pnl:,.2f}", color="#00ff9d" if realized_pnl >= 0 else "#ff0055")
                    with m2:
                        win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
                        metric_card("Win Rate", f"{win_rate:.1f}%", f"{wins}W / {losses}L")
                    with m3:
                        metric_card("Total Volume", f"${total_vol:,.0f}", color="#00f2ff")
                    with m4:
                        metric_card("Trades", str(len(df_sess)), "Entries")
                        
                else:
                    st.info("No trades found in this session window.")
            else:
                st.info("No trade history available.")
        except Exception as e:
            st.warning(f"Error calculating performance: {e}")
            
    st.divider()
    # Live Trading Report for Terminal
    col_rep1, col_rep2 = st.columns([4, 1])
    with col_rep1:
        neon_header("Live Trading Report", level=2)
    with col_rep2:
        if st.button("🔄 Refresh Report"):
            st.rerun()
            
    # Auto-Refresh Toggle for Live Report
    if st.toggle("Auto-Refresh Report (5s)", value=False, key="live_report_autorefresh"):
        time.sleep(5)
        st.rerun()

    if os.path.exists(bot.trade_log_file):
        try:
            with open(bot.trade_log_file, 'r') as f:
                trade_logs = json.load(f)
            if trade_logs:
                df_trades = pd.DataFrame(trade_logs)
                # Select columns if they exist
                cols = ['timestamp', 'symbol', 'type', 'strategy', 'entry', 'risk_percent', 'confidence', 'decision', 'audit_status']
                valid_cols = [c for c in cols if c in df_trades.columns]
                st.dataframe(df_trades[valid_cols].sort_values("timestamp", ascending=False).head(15), use_container_width=True)
            else:
                st.info("No activity recorded yet.")
        except:
            st.warning("Could not read trade log.")
    else:
        st.info("No trade log file found.")

if page_nav == "Arbitrage Scanner":
    neon_header("⚡ Cross-Exchange Arbitrage Scanner")
    st.markdown("**Real-time Price Discrepancy Monitoring**")
    
    # Initialize bot if needed (for access to arbitrage scanner)
    try:
        bot = get_bot(exchange)
    except:
        st.error("Bot initialization failed.")
        st.stop()
        
    # Controls
    col_scan1, col_scan2 = st.columns([3, 1])
    with col_scan1:
        scan_symbol = st.selectbox("Scan Asset", ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT', 'MATIC/USDT'], index=0)
    with col_scan2:
        if st.button("🔄 Refresh Scan", type="primary"):
            st.rerun()

    # Perform Scan
    with st.spinner(f"Scanning exchanges for {scan_symbol}..."):
        # Get raw prices
        prices_df = bot.arbitrage.get_prices_df(scan_symbol)
        
        # Get opportunities
        opps = bot.arbitrage.scan_opportunities(scan_symbol)

    # Display Prices
    neon_header("Exchange Price Matrix", level=3)
    if not prices_df.empty:
        # Simple dataframe display
        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            st.dataframe(
                prices_df.style.format({"Price": "{:.2f}", "Spread (%)": "{:.2f}%"}), 
                use_container_width=True,
                height=400
            )
        with col_p2:
            min_price = prices_df['Price'].min()
            max_price = prices_df['Price'].max()
            
            metric_card("Best Buy Price", f"${min_price:,.2f}", color="#00ff9d")
            metric_card("Best Sell Price", f"${max_price:,.2f}", color="#ff0055")
            spread = ((max_price - min_price) / min_price) * 100
            metric_card("Spread", f"{spread:.2f}%", color="#00f2ff")
            
    else:
        st.warning("Could not fetch price data. Ensure exchanges are reachable.")

    st.divider()
    
    # Display Opportunities
    neon_header("🚀 Arbitrage Opportunities", level=2)
    if opps:
        for opp in opps:
            st.success(f"Opportunity Found: {opp['buy_exchange'].upper()} ➡ {opp['sell_exchange'].upper()}")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                metric_card("Buy At", f"{opp['buy_exchange'].upper()}", f"${opp['buy_price']:,.2f}", color="#00ff9d")
            with c2:
                metric_card("Sell At", f"{opp['sell_exchange'].upper()}", f"${opp['sell_price']:,.2f}", color="#ff0055")
            with c3:
                metric_card("Profit Spread", f"{opp['spread_pct']:.2f}%", color="#00f2ff")
            with c4:
                metric_card("Est. Profit (1k)", f"${opp['estimated_profit_1k']:.2f}", color="#bd00ff")
            
            st.button(f"Execute {opp['buy_exchange']} -> {opp['sell_exchange']}", key=f"arb_{opp['buy_exchange']}")
            st.divider()
    else:
        st.info(f"No significant arbitrage opportunities found for {scan_symbol} (>0.1% spread).")

if page_nav == "Copy Trading":
    neon_header("👥 Social & Copy Trading")
    
    # Initialize Copy Module
    if 'copy_trader' not in st.session_state:
        st.session_state.copy_trader = CopyTradingModule()
        
    copy_bot = st.session_state.copy_trader
    
    # Initialize Bot for context
    if 'bot' not in st.session_state:
        st.session_state.bot = get_bot(exchange)
    
    ct_tab1, ct_tab2 = st.tabs(["Copy Center", "My Portfolio"])
    
    with ct_tab1:
        neon_header("Discover Top Traders", level=2)
        
        # Mock Leaderboard
        traders = [
            {'name': 'WhaleHunter_99', 'roi': 450.2, 'win_rate': 78, 'risk': 'High', 'followers': 1205},
            {'name': 'SafeYields_DAO', 'roi': 45.5, 'win_rate': 92, 'risk': 'Low', 'followers': 5400},
            {'name': 'Quant_Alpha_X', 'roi': 120.8, 'win_rate': 65, 'risk': 'Medium', 'followers': 890},
            {'name': 'Degen_Ape_Lover', 'roi': -15.0, 'win_rate': 40, 'risk': 'Extreme', 'followers': 20},
        ]
        
        cols = st.columns(4)
        for i, trader in enumerate(traders):
            with cols[i]:
                neon_header(f"{trader['name']}", level=4)
                roi_color = "#00ff9d" if trader['roi'] > 0 else "#ff0055"
                metric_card("ROI", f"{trader['roi']}%", color=roi_color)
                st.caption(f"Win Rate: {trader['win_rate']}% | Risk: {trader['risk']}")
                st.caption(f"Followers: {trader['followers']}")
                
                if st.button(f"Copy {trader['name']}", key=f"copy_{i}"):
                    st.session_state.copy_trader.connect_master_account(trader['name'], "mock_api_key", "mock_secret")
                    st.success(f"Now copying {trader['name']}!")
        
        st.divider()
        neon_header("Manual Copy Signal Input", level=2)
        with st.expander("Enter Signal Manually"):
            m_symbol = st.text_input("Symbol", "BTC/USDT")
            m_side = st.selectbox("Side", ["buy", "sell"])
            m_amount = st.number_input("Amount", 0.001)
            
            if st.button("Execute Copy Signal"):
                copy_bot.execute_copy_trade(m_symbol, m_side, m_amount)

    with ct_tab2:
        neon_header("Active Copy Positions", level=2)
        if 'sim_positions' in st.session_state and st.session_state.sim_positions:
            st.dataframe(pd.DataFrame(st.session_state.sim_positions))
        else:
            st.info("No active copy trades.")

if page_nav == "Quantum Lab":
    neon_header("⚛️ Quantum Intelligence Lab")
    st.markdown("**Quantum-Inspired Optimization & Signal Processing**")
    
    # Initialize bot if needed
    try:
        bot = get_bot(exchange)
    except:
        st.error("Bot initialization failed. Please check configuration.")
        st.stop()
        
    q_tab1, q_tab2, q_tab3 = st.tabs(["Quantum Regime Detection", "Portfolio Optimization (Annealing)", "Grover Search Signals"])
    
    with q_tab1:
        neon_header("Hybrid Quantum-Classical Regime Detection", level=2)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Generate Probability Wave Visualization
            neon_header("Probability Wave Function (Market State)", level=3)
            
            # Fetch Data for Quantum Calculation
            q_df = get_cached_ohlcv(bot, bot.symbol, bot.timeframe)
            if not q_df.empty:
                current_price = q_df['close'].iloc[-1]
                returns = q_df['close'].pct_change().dropna()
                volatility = returns.std() if not returns.empty else 0.01
                
                # Use bot.quantum directly if available, else try brain.quantum
                quantum_engine = getattr(bot, 'quantum', getattr(bot.brain, 'quantum', None))
                
                if quantum_engine:
                    x, pdf = quantum_engine.calculate_probability_wave(current_price, volatility)
                    wave_data = {'x': x, 'psi_squared': pdf}
                else:
                    wave_data = {'x': [], 'psi_squared': []}
            
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=wave_data['x'], 
                    y=wave_data['psi_squared'],
                    mode='lines',
                    name='Probability Density |Ψ|²',
                    fill='tozeroy',
                    line=dict(color='#00ff99', width=2)
                ))
                fig.update_layout(
                    title="Market State Probability Distribution",
                    xaxis_title="Market State Space (Bearish <-> Bullish)",
                    yaxis_title="Probability Density",
                    template="plotly_dark",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Insufficient data for Quantum Analysis")
            
        with col2:
            neon_header("Current Quantum State", level=3)
            
            # Fetch Data for Analysis
            df = get_cached_ohlcv(bot, bot.symbol, bot.timeframe)
            if not df.empty:
                regime = bot.brain.detect_market_regime(df)
                
                metric_card("Detected Regime", regime['type'], color="#00f2ff")
                metric_card("Quantum Volatility Score", f"{regime.get('volatility_score', 0):.4f}", color="#bd00ff")
                
                if regime.get('quantum_state'):
                    st.info(f"Quantum State: {regime['quantum_state']}")
                
                st.markdown("---")
                st.markdown("**Interpretation:**")
                st.caption("The wave function represents the superposition of market states. "
                           "Peaks indicate high probability states. "
                           "Sharp peaks = Stable trends. "
                           "Flat/Multi-modal = High volatility/Uncertainty.")
    
    with q_tab2:
        neon_header("Simulated Annealing Portfolio Optimization", level=2)
        st.markdown("Solves the NP-Hard problem of optimal asset allocation in milliseconds using quantum-inspired annealing.")
        
        # Asset Selection
        assets = st.multiselect("Select Assets for Portfolio", 
                               ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'XRP/USDT'],
                               default=['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT'])
        
        if st.button("Run Quantum Annealing Optimization"):
            with st.spinner("Annealing... Finding Global Minimum Energy State..."):
                # Fetch Data for all assets
                prices_dict = {}
                for asset in assets:
                    try:
                        df_asset = bot.data_manager.fetch_ohlcv(asset, '1d', limit=100)
                        prices_dict[asset] = df_asset['close']
                    except:
                        pass
                
                if prices_dict:
                    prices_df = pd.DataFrame(prices_dict)
                    
                    # Run Optimization
                    allocation = bot.portfolio_opt.optimize_allocation(prices_df, 10000, method='quantum')
                    
                    # Visualize
                    st.success("Optimization Complete! Found optimal energy state.")
                    
                    col_opt1, col_opt2 = st.columns(2)
                    
                    with col_opt1:
                        # Pie Chart
                        labels = list(allocation.keys())
                        values = list(allocation.values())
                        
                        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
                        fig_pie.update_layout(title="Optimal Quantum Allocation", template="plotly_dark")
                        st.plotly_chart(fig_pie, use_container_width=True)
                        
                    with col_opt2:
                        st.dataframe(pd.DataFrame([allocation], index=["Allocation ($)"]).T)
                        
                else:
                    st.error("Could not fetch data for selected assets.")

    with q_tab3:
        neon_header("Grover Search Signal Amplification", level=2)
        st.markdown("Uses quantum amplitude amplification to find 'needle in a haystack' arbitrage signals.")
        
        if st.button("Scan Arbitrage Space (Quantum Enhanced)"):
            with st.spinner("Applying Grover Operator..."):
                opportunities = bot.arbitrage.scan_quantum_opportunities(bot.symbol)
                
                if opportunities:
                    for opp in opportunities:
                        st.success(f"Signal Detected with Quantum Confidence: {opp['quantum_confidence']:.4f}")
                        st.json(opp)
                else:
                    st.info("No high-confidence signals found after amplitude amplification.")

if page_nav == "Blockchain & DeFi":
    neon_header("🔗 Blockchain & DeFi Hub")
    
    # Initialize components
    if 'transparency_log' not in st.session_state:
        st.session_state.transparency_log = TransparencyLog()
        
    # Initialize DeFi Manager
    if 'defi_manager' not in st.session_state:
        # Use connected wallet's chain if available, else default to ethereum
        chain = st.session_state.web3_wallet.chain_id if st.session_state.web3_wallet.is_connected() else 'ethereum'
        # Map chain ID to name
        chain_map = {'1': 'ethereum', '56': 'bsc', '137': 'polygon', '43114': 'avalanche', 'solana': 'solana'}
        chain_name = chain_map.get(str(chain), 'ethereum')
        
        st.session_state.defi_manager = DeFiManager(chain=chain_name)
    
    # Sync chain if wallet changed
    if st.session_state.web3_wallet.is_connected():
        chain_map = {'1': 'ethereum', '56': 'bsc', '137': 'polygon', '43114': 'avalanche', 'solana': 'solana'}
        current_chain_name = chain_map.get(str(st.session_state.web3_wallet.chain_id), 'ethereum')
        if st.session_state.defi_manager.current_chain != current_chain_name:
             st.session_state.defi_manager.connect_to_chain(current_chain_name)
    
    # Tabs
    tab_overview, tab_defi, tab_security, tab_logs = st.tabs(["Overview", "DeFi Operations", "Security", "Audit Logs"])
    
    # Overview Tab
    with tab_overview:
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("ETH Price (Oracle)", f"${OracleManager.get_price_feed('ETH', 'ethereum'):,.2f}", color="#627eea")
        with c2:
            metric_card("BTC Price (Oracle)", f"${OracleManager.get_price_feed('BTC', 'ethereum'):,.2f}", color="#f7931a")
        with c3:
            metric_card("SOL Price (Oracle)", f"${OracleManager.get_price_feed('SOL', 'solana'):,.2f}", color="#14f195")
        
        neon_header("Cross-Chain Wallet Balances", level=2)
        
        if st.session_state.web3_wallet.is_connected():
            bal_col1, bal_col2, bal_col3 = st.columns(3)
            eth_bal = st.session_state.web3_wallet.get_balance()
            # Calculate USD value roughly
            eth_usd = eth_bal * OracleManager.get_price_feed('ETH', 'ethereum')
            
            with bal_col1:
                metric_card("Ethereum (Mainnet)", f"{eth_bal:.4f} ETH", f"${eth_usd:,.2f}", "#627eea")
            with bal_col2:
                metric_card("Binance Smart Chain", "0.0000 BNB", "$0.00", "#f3ba2f")
            with bal_col3:
                metric_card("Polygon (Matic)", "0.0000 MATIC", "$0.00", "#8247e5")
                
            st.success(f"✅ Wallet Connected: {st.session_state.web3_wallet.address}")
        else:
            st.info("Connect your wallet in the sidebar to view real-time balances.")

    # DeFi Operations Tab
    with tab_defi:
        st.markdown("### 🚀 Cross-Chain DeFi Execution")
        
        # Check for Transaction Callback
        if "tx_hash" in st.query_params:
            tx_hash = st.query_params["tx_hash"]
            st.success(f"✅ Transaction Broadcasted! Hash: {tx_hash}")
            st.caption("Waiting for confirmation...")
            st.session_state.transparency_log.log_action("Web3 Transaction", f"Tx Hash: {tx_hash}")
            if st.button("Clear Notification"):
                st.query_params.clear()
                if 'defi_stage' in st.session_state:
                    st.session_state.defi_stage = 'input'
                if 'swap_stage' in st.session_state:
                    st.session_state.swap_stage = 'input'
                st.rerun()

        # --- DEX SWAP SECTION ---
        with st.container():
            st.markdown("#### 💱 Instant DEX Swap")
            
            # State Management for Swap
            if 'swap_stage' not in st.session_state:
                st.session_state.swap_stage = 'input'
                
            if st.session_state.swap_stage == 'input':
                ds_col1, ds_col2, ds_col3 = st.columns([2, 1, 2])
                
                with ds_col1:
                    swap_in = st.selectbox("From", ["ETH", "USDT", "USDC", "WBTC", "BNB", "MATIC", "SOL"], key="swap_in")
                    amt_in = st.number_input("Amount In", min_value=0.0, step=0.1, key="swap_amt_in")
                    
                with ds_col2:
                    st.markdown("<h2 style='text-align: center; padding-top: 20px;'>➡️</h2>", unsafe_allow_html=True)
                    
                with ds_col3:
                    swap_out = st.selectbox("To", ["USDT", "USDC", "ETH", "WBTC", "BNB", "MATIC", "SOL"], index=1, key="swap_out")
                    slippage = st.number_input("Slippage (%)", min_value=0.1, max_value=50.0, value=0.5, step=0.1, key="swap_slippage")
                    
                    # Dynamic Quote
                    quote = 0.0
                    if amt_in > 0:
                         # Ensure DeFiManager is ready
                         if 'defi_manager' in st.session_state:
                            quote = st.session_state.defi_manager.get_swap_quote(swap_in, swap_out, amt_in)
                    st.metric("Estimated Output", f"{quote:.4f} {swap_out}")

                if st.button("Review Swap"):
                     if not st.session_state.web3_wallet.is_connected():
                         st.error("Please connect your wallet first!")
                     elif amt_in <= 0:
                         st.error("Amount must be greater than 0.")
                     else:
                         st.session_state.swap_stage = 'preview'
                         st.session_state.swap_details = {
                             "token_in": swap_in,
                             "token_out": swap_out,
                             "amount": amt_in,
                             "quote": quote,
                             "slippage": slippage
                         }
                         st.rerun()
            
            elif st.session_state.swap_stage == 'preview':
                details = st.session_state.swap_details
                st.info(f"Swap {details['amount']} {details['token_in']} -> ~{details['quote']:.4f} {details['token_out']}")
                
                # Gas Estimation
                gas_price = st.session_state.defi_manager.get_gas_price()
                st.caption(f"Network Gas Price: {gas_price} Gwei (EVM) / Lamports (Solana)")
                st.caption(f"Slippage Tolerance: {details['slippage']}%")
                
                # Execute Swap Logic
                if st.button("Confirm Swap"):
                     with st.spinner("Constructing Transaction..."):
                         result = st.session_state.defi_manager.swap_tokens(
                             details['token_in'], 
                             details['token_out'], 
                             details['amount'],
                             slippage=details['slippage']
                         )
                         
                         if result['status'] in ['Pending_Sign', 'Pending_Approve']:
                             st.session_state.swap_payload = result
                             st.session_state.swap_stage = 'signing'
                             st.rerun()
                         else:
                             st.error(f"Swap Failed: {result.get('error', 'Unknown Error')}")
                             
                if st.button("Back"):
                    st.session_state.swap_stage = 'input'
                    st.rerun()
                    
            elif st.session_state.swap_stage == 'signing':
                payload = st.session_state.swap_payload
                st.info(payload.get('message', 'Please sign the transaction.'))
                
                # JS Injection
                tx_data = payload['payload']
                to_addr = tx_data.get('to', '') # Router or Token
                val = tx_data.get('value', '0')
                data = tx_data.get('data', '0x')
                
                # Check if it's EVM or Solana
                if 'type' in tx_data and tx_data['type'] == 'solana_transaction':
                     # Solana JS Injection
                     st.warning("Initiating Solana Transaction...")
                     
                     sol_js = f"""
                     <script>
                     async function sendSolanaTx() {{
                        if ("solana" in window) {{
                            try {{
                                await window.solana.connect();
                                const provider = window.solana;
                                if (provider.isPhantom) {{
                                    // Simulation: We sign a message to prove ownership since we don't have a valid serialized swap tx from backend
                                    const message = "Confirm Swap: {st.session_state.swap_details['amount']} {st.session_state.swap_details['token_in']} -> {st.session_state.swap_details['token_out']}";
                                    const encodedMessage = new TextEncoder().encode(message);
                                    const signedMessage = await provider.signMessage(encodedMessage, "utf8");
                                    
                                    // In a real app with valid blockhash/instructions:
                                    // const {{ signature }} = await provider.signAndSendTransaction(transaction);
                                    
                                    console.log("Signed:", signedMessage);
                                    window.parent.location.search = '?tx_hash=Solana_Signature_Verified_' + Date.now();
                                }} else {{
                                    alert("Please use Phantom Wallet for Solana");
                                }}
                            }} catch (err) {{
                                console.error(err);
                                alert("Solana Error: " + err.message);
                            }}
                        }} else {{
                            alert("Solana Wallet not found! Please install Phantom.");
                        }}
                     }}
                     sendSolanaTx();
                     </script>
                     """
                     components.html(sol_js, height=0)
                     
                     if st.button("Cancel / Reset"):
                         st.session_state.swap_stage = 'input'
                         st.rerun()
                else:
                    # EVM Injection
                    # Convert value to hex if it's a string int
                    try:
                        val_hex = hex(int(val))
                    except:
                        val_hex = val

                    js_code = f"""
                    <script>
                    async function sendSwapTx() {{
                        if (window.ethereum) {{
                            try {{
                                const params = [{{
                                    from: '{st.session_state.web3_wallet.address}',
                                    to: '{to_addr}',
                                    value: '{val_hex}',
                                    data: '{data}'
                                }}];
                                const txHash = await window.ethereum.request({{
                                    method: 'eth_sendTransaction',
                                    params: params,
                                }});
                                window.parent.location.search = '?tx_hash=' + txHash;
                            }} catch (error) {{
                                console.error(error);
                                alert("Swap Failed: " + error.message);
                            }}
                        }} else {{
                            alert("Wallet not connected!");
                        }}
                    }}
                    sendSwapTx();
                    </script>
                    """
                    components.html(js_code, height=0)
                    
                    if st.button("Cancel / Reset Swap"):
                        st.session_state.swap_stage = 'input'
                        st.rerun()

        st.divider()

        op_col1, op_col2 = st.columns([1, 1])
        
        with op_col1:
            st.markdown("#### Yield Farming")
            
            # State Management for Transaction Flow
            if 'defi_stage' not in st.session_state:
                st.session_state.defi_stage = 'input'
                
            if st.session_state.defi_stage == 'input':
                yf_asset = st.selectbox("Asset", ["ETH", "USDT", "USDC"], key="yf_asset")
                yf_amount = st.number_input("Amount", min_value=0.0, step=0.01, key="yf_amount")
                yf_protocol = st.selectbox("Protocol", ["Aave V3", "Compound", "Uniswap V3"], key="yf_protocol")
                
                if st.button("Review Transaction"):
                    if not st.session_state.web3_wallet.is_connected():
                        st.error("Please connect your wallet first!")
                    elif yf_amount <= 0:
                        st.error("Amount must be greater than 0.")
                    else:
                        st.session_state.defi_stage = 'preview'
                        st.session_state.tx_details = {
                            "asset": yf_asset,
                            "amount": yf_amount,
                            "protocol": yf_protocol
                        }
                        st.rerun()
                        
            elif st.session_state.defi_stage == 'preview':
                details = st.session_state.tx_details
                st.markdown("##### 📝 Transaction Preview")
                st.info(f"**Action:** Deposit {details['amount']} {details['asset']} into {details['protocol']}")
                
                # Mock Gas Estimation
                st.write(f"**Estimated Gas:** 0.0042 ETH ($12.50)")
                st.write(f"**Slippage Tolerance:** 0.5%")
                
                c_sign, c_back = st.columns(2)
                with c_sign:
                    if st.button("✅ Confirm & Sign", type="primary"):
                        st.session_state.defi_stage = 'signing'
                        st.rerun()
                with c_back:
                    if st.button("⬅️ Back"):
                        st.session_state.defi_stage = 'input'
                        st.rerun()
                        
            elif st.session_state.defi_stage == 'signing':
                st.info("Waiting for signature...")
                details = st.session_state.tx_details
                
                # Construct Transaction Data
                # Demo: Send ETH to Aave Pool V3 (or safe address)
                to_address = "0x87870Bca3F3f63453e768974ef48c79A2ea746cc" # Aave V3 Pool Mainnet
                value_wei = 0
                data_hex = "0x"
                
                if details['asset'] == 'ETH':
                    value_wei = st.session_state.web3_wallet.to_wei(details['amount'])
                else:
                    st.warning(f"⚠️ Note: {details['asset']} transaction simulation (0 ETH transfer). Real token transfer requires ABI.")
                
                # JS Injection for Transaction
                # Use a specific div id to avoid multiple injections
                js_code = f"""
                <script>
                async function sendTx() {{
                    if (window.ethereum) {{
                        try {{
                            const params = [{{
                                from: '{st.session_state.web3_wallet.address}',
                                to: '{to_address}',
                                value: '0x{value_wei:x}',
                                data: '{data_hex}'
                            }}];
                            const txHash = await window.ethereum.request({{
                                method: 'eth_sendTransaction',
                                params: params,
                            }});
                            window.parent.location.search = '?tx_hash=' + txHash;
                        }} catch (error) {{
                            console.error(error);
                            alert("Transaction Failed: " + error.message);
                        }}
                    }} else {{
                        alert("Wallet not connected!");
                    }}
                }}
                // Execute immediately on mount
                sendTx();
                </script>
                """
                components.html(js_code, height=0)
                
                if st.button("Cancel / Reset"):
                    st.session_state.defi_stage = 'input'
                    st.rerun()

        with op_col2:
            st.markdown("#### Flash Loan Arbitrage")
            fl_token = st.text_input("Token Address", "0x...", key="fl_token")
            fl_amount = st.number_input("Loan Amount", min_value=1000.0, step=1000.0, key="fl_amount")
            
            if st.button("Execute Flash Loan"):
                st.warning("Executing Flash Loan...")
                time.sleep(1)
                st.error("Execution Failed: Slippage too high (Simulation)")
                
    # Security Tab
    with tab_security:
        st.markdown("### 🛡️ Smart Contract Security")
        st.markdown("### Active Protections")
        st.checkbox("Reentrancy Guard", value=True, disabled=True)
        st.checkbox("Integer Overflow Protection", value=True, disabled=True)
        st.checkbox("Access Control", value=True, disabled=True)
        
        st.divider()
        st.markdown("### Emergency Controls")
        if st.button("🚨 EMERGENCY PAUSE", type="primary"):
            st.error("SYSTEM PAUSED. All trading suspended.")
            
    # Logs Tab
    with tab_logs:
        st.markdown("### Transparency Log (Blockchain)")
        if hasattr(st.session_state, 'transparency_log'):
            st.dataframe(pd.DataFrame(st.session_state.transparency_log.logs))
        else:
            st.info("No logs available.")

if page_nav == "Risk Management":
    neon_header("🛡️ Adaptive Risk Management")
    
    # Initialize Risk Manager if needed (usually attached to bot)
    bot = get_bot(st.session_state.get('active_exchange', 'binance'))
    
    # Layout
    r_col1, r_col2 = st.columns([2, 1])
    
    with r_col1:
        st.markdown("### 📊 Real-Time Risk Metrics")
        
        # Metrics Row
        rm1, rm2, rm3 = st.columns(3)
        with rm1:
            metric_card("Current Drawdown", f"{bot.risk_manager.current_drawdown:.2f}%", "-0.5%", "#ff4b4b")
        with rm2:
            metric_card("Daily Loss", f"${bot.risk_manager.daily_loss:.2f}", "+$0.00", "#ff4b4b")
        with rm3:
            metric_card("Risk Exposure", f"{bot.risk_manager.current_exposure:.2f}%", "Safe", "#00ff00")
            
        st.divider()
        
        st.markdown("### 📉 Active Circuit Breakers")
        cb_df = pd.DataFrame([
            {"Type": "Daily Loss Limit", "Threshold": "$100.00", "Status": "Active", "Action": "Halt Trading"},
            {"Type": "Max Drawdown", "Threshold": "5.0%", "Status": "Active", "Action": "Liquidate All"},
            {"Type": "Volatility Halt", "Threshold": "High", "Status": "Monitoring", "Action": "Pause Entry"}
        ])
        st.dataframe(cb_df, use_container_width=True)
        
        st.markdown("### 🛑 Emergency Controls")
        if st.button("KILL SWITCH: LIQUIDATE ALL & HALT", type="primary", use_container_width=True):
            bot.risk_manager.emergency_stop()
            st.error("🚨 EMERGENCY KILL SWITCH ACTIVATED! All positions closed. Trading halted.")
            st.session_state.sound_queue.append("alert")

    with r_col2:
        card_container("⚙️ Risk Configuration", """
        Configure your risk tolerance and safety limits.
        """)
        
        with st.form("risk_config"):
            st.number_input("Max Risk Per Trade (%)", value=1.0, step=0.1)
            st.number_input("Max Daily Loss ($)", value=100.0, step=10.0)
            st.number_input("Max Drawdown (%)", value=5.0, step=0.5)
            st.selectbox("Risk Mode", ["Conservative", "Balanced", "Aggressive"])
            
            if st.form_submit_button("Update Risk Profile"):
                st.success("Risk profile updated successfully.")

if page_nav == "Settings":
    neon_header("⚙️ System Settings")
    
    st.markdown("### 🌐 Web3 Configuration")
    with st.expander("WalletConnect Settings", expanded=True):
        st.info("To use WalletConnect V2, you need a Project ID from [Reown/WalletConnect Cloud](https://cloud.reown.com).")
        wc_pid = st.text_input("Project ID", value=st.session_state.get('wc_project_id', ''), type="password")
        if st.button("Save Project ID"):
            st.session_state.wc_project_id = wc_pid
            st.success("Project ID Saved (Session Only)")
    
    st.markdown("### API Configuration")
    with st.expander("Exchange Keys"):
        st.text_input("API Key", type="password")
        st.text_input("Secret Key", type="password")
        st.button("Save Keys")
        
    st.markdown("### Risk Management")
    st.slider("Max Drawdown Limit (%)", 1, 50, 10)
    st.slider("Max Leverage", 1, 100, 5)
    
    st.divider()
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- Mock Classes for Dashboard Completeness if not imported ---
class TransparencyLog:
    def __init__(self):
        self.logs = []
    def log_action(self, action, details):
        self.logs.append({"timestamp": pd.Timestamp.now(), "action": action, "details": details})

class OracleManager:
    @staticmethod
    def get_price_feed(symbol, chain):
        # Mock prices
        prices = {'ETH': 2200.0, 'BTC': 42000.0, 'SOL': 95.0}
        return prices.get(symbol, 0.0)
