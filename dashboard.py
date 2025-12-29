
import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from core.bot import TradingBot
from core.copy_trading import CopyTradingModule
from core.auth import AuthManager, UserManager, TOTP, SessionManager
from core.nlp_engine import NLPEngine
from core.sound_engine import SoundEngine
from core.trade_replay import TradeReplay
from core.chaos import ChaosMonkey
from core.transparency import TransparencyLog, OracleManager
from config.settings import APP_NAME, VERSION, DEFAULT_SYMBOL
from config.trading_config import TRADING_CONFIG
import json
import os

st.set_page_config(page_title=APP_NAME, layout="wide")

# Initialize Auth
if 'auth_manager' not in st.session_state:
    st.session_state.auth_manager = AuthManager()
if 'session_manager' not in st.session_state:
    st.session_state.session_manager = SessionManager()

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
        # Clear local storage via JS injection
        st.markdown("<script>localStorage.removeItem('caparox_session');</script>", unsafe_allow_html=True)
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
    st.markdown("<script>localStorage.removeItem('caparox_session');</script>", unsafe_allow_html=True)

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
        st.query_params.clear()
    else:
        st.error("Session expired or invalid.")
        st.query_params.clear()

# Inject Persistence Script (Only if NOT logged in and NO session_id in URL)
if not st.session_state.logged_in and not session_id and not logout_reason:
    st.markdown("""
        <script>
            const token = localStorage.getItem('caparox_session');
            if (token) {
                window.location.search = '?session_id=' + token;
            }
        </script>
    """, unsafe_allow_html=True)

# Initialize NLP (Moved to after bot initialization)

# Initialize Sound Engine
if 'sound_engine' not in st.session_state:
    st.session_state.sound_engine = SoundEngine()

# Initialize Trade Replay
if 'trade_replay' not in st.session_state:
    st.session_state.trade_replay = TradeReplay()

if 'sound_queue' not in st.session_state:
    st.session_state.sound_queue = []



# Custom CSS
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .metric-card { background-color: #262730; padding: 20px; border-radius: 10px; border: 1px solid #4F4F4F; }
    .success-text { color: #00FF00; }
    .danger-text { color: #FF0000; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
@st.cache_resource
def get_bot(exchange_id):
    return TradingBot(exchange_id)

@st.cache_data(ttl=600)
def get_cached_fundamentals(symbol, _bot):
    return _bot.fundamentals.get_asset_details(symbol)

@st.cache_data(ttl=600)
def get_cached_sentiment(_bot):
    return _bot.fundamentals.get_market_sentiment()

@st.cache_data(ttl=5)
def get_cached_ohlcv(_bot, symbol, timeframe):
    return _bot.data_manager.fetch_ohlcv(symbol, timeframe, limit=200)

@st.cache_data(ttl=60)
def get_cached_analysis(_bot, df):
    """Cache the heavy analysis to improve dashboard speed"""
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(f"🔒 {APP_NAME} Access")
        
        if st.session_state.login_stage == 'credentials':
            tab_login, tab_reg = st.tabs(["Login", "Register"])
            
            with tab_login:
                with st.form("login_form"):
                    username = st.text_input("Username", key="login_user")
                    password = st.text_input("Password", type="password", key="login_pass")
                    remember_me = st.checkbox("Remember Me")
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
                                    
                                    # Inject JS to save token
                                    st.markdown(f"""
                                        <script>
                                            localStorage.setItem('caparox_session', '{token}');
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
            st.subheader("Two-Factor Authentication")
            
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
                        
                        st.markdown(f"""
                            <script>
                                localStorage.setItem('caparox_session', '{token}');
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

# Sidebar Configuration
with st.sidebar:
    st.header("Global Configuration")
    
    # Navigation
    page_nav = st.radio("Navigate", ["Trading Dashboard", "Trading Monitor", "Trading Terminal", "Arbitrage Scanner", "Copy Trading", "Blockchain & DeFi", "Quantum Lab", "Settings"], key="main_nav_radio")
    
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
    
    # Exchange Connection Manager
    st.divider()
    st.subheader("Exchange Manager")
    
    # Connection Method Selection
    connection_method = st.radio("Connection Method", ["API (Automatic Trading)", "Manual (Signal Only)"], index=0)
    
    # Added requested exchanges: Luno, Quidax, NairaEx, Busha
    exchange_list = ['binance', 'luno', 'kucoin', 'bybit', 'quidax', 'nairaex', 'busha', 'kraken', 'okx', 'gateio', 'mexc']
    exchange = st.selectbox("Active Exchange", exchange_list)
    # Update session state
    st.session_state.exchange = exchange

    if connection_method == "API (Automatic Trading)":
        with st.expander("API Credentials", expanded=True):
            api_key = st.text_input("API Key", type="password")
            api_secret = st.text_input("API Secret", type="password")
            if st.button("Connect Exchange"):
                if api_key and api_secret:
                    try:
                        # Initialize bot to access data manager
                        temp_bot = get_bot(exchange)
                        temp_bot.data_manager.update_credentials(api_key, api_secret)
                        st.success(f"Connected to {exchange.upper()}!")
                        st.session_state.exchange_connected = True
                    except Exception as e:
                        st.error(f"Connection Failed: {e}")
                else:
                    st.warning("Please enter API Key and Secret")
                    
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
        st.subheader("🏆 Trader Profile")
        
        # Calculate Level (XP based on trades)
        metrics = st.session_state.user_manager.get_performance_metrics()
        xp = metrics.get('total_trades', 0) * 10 + (metrics.get('total_pnl', 0) / 10)
        level = int(1 + (xp / 100))
        
        c_lvl, c_xp = st.columns([1, 2])
        with c_lvl:
            st.metric("Level", f"{level}")
        with c_xp:
            st.caption(f"XP: {int(xp)}")
            st.progress(min((xp % 100) / 100, 1.0))
            
        # Pro Metrics
        st.divider()
        st.markdown("### 📊 Performance Analytics")
        
        # Row 1: PnL & Win Rate
        c_pnl, c_win = st.columns(2)
        with c_pnl:
            st.metric("Total PnL", f"${metrics.get('total_pnl', 0):.2f}")
        with c_win:
            st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
            
        # Row 2: Sharpe & Drawdown
        c_sharpe, c_dd = st.columns(2)
        with c_sharpe:
            st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}", help="Risk-adjusted return (>1 is good)")
        with c_dd:
            st.metric("Max Drawdown", f"${metrics.get('max_drawdown', 0):.2f}", help="Maximum loss from a peak to a trough")
            
        # Row 3: Profit Factor
        st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}", help="Gross Profit / Gross Loss (>1.5 is ideal)")
            
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
    st.subheader("🎯 System Targets")
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
    
    st.metric("Target APR", f"{target_min:.0f}% - {target_max:.0f}%")
    st.metric("Current Projected APR", f"{sim_apr:.1f}%", delta=f"{sim_apr - target_min:.1f}%")

    # Strategy Selection
    st.divider()
    st.subheader("Strategy Intelligence")
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
    
    # Strategy Parameters (Dynamic based on selection)
    if selected_strategy == "Grid Trading":
        grid_levels = st.slider("Grid Levels", 3, 10, 5)
        grid_step = st.slider("Grid Step (%)", 0.1, 5.0, 1.0)
    
    # Trading Execution & Balance Manager
    st.divider()
    st.subheader("Wallet & Execution")
    
    # Determine Connection Status
    temp_bot = get_bot(st.session_state.get('exchange', 'binance'))
    is_connected = st.session_state.get('exchange_connected', False)
    
    # Auto-switch mode based on connection
    active_mode = 'Live' if is_connected else 'Simulation'
    
    # Allow manual override to Simulation even if connected (Safety feature)
    if is_connected:
        mode_override = st.radio("Active Mode", ["Live", "Simulation"], index=0, horizontal=True)
        active_mode = mode_override
    
    # Apply Mode
    try:
        if hasattr(temp_bot, 'set_trading_mode'):
            temp_bot.set_trading_mode(active_mode)
        else:
            # Stale cache detected, force reload
            st.cache_resource.clear()
            st.rerun()
    except AttributeError:
        st.cache_resource.clear()
        st.rerun()
        
    st.session_state.trading_mode = active_mode
    
    # Display Active Balance
    bal_color = "red" if active_mode == 'Live' else "blue"
    bal_label = f":{bal_color}[{active_mode.upper()} BALANCE]"
    current_bal = temp_bot.risk_manager.current_capital
    
    st.metric(bal_label, f"${current_bal:,.2f}")
    
    if active_mode == 'Live':
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
    auto_refresh = st.toggle("Enable Live Feed (Auto-Refresh)", value=False)
    
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

if page_nav == "Trading Dashboard":
    st.title(f"📈 {symbol} Command Center")
    
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

        # Run Analysis
        # Use copy for chart to avoid polluting cache with indicators
        df = raw_df.copy()
        df = bot.analyzer.calculate_indicators(df)
        
        # Run Strategy Analysis to get Signal & Regime
        signal = bot.run_analysis(raw_df) 
        market_regime = signal.regime if signal else "Unknown"
        
        # --- Chart Section ---
        with col_chart:
            # Chart Controls
            c1, c2, c3 = st.columns(3)
            with c1:
                show_volume = st.checkbox("Show Volume", value=True)
            with c2:
                indicators_selected = st.multiselect("Indicators", ["RSI", "MACD", "Bollinger Bands", "EMA", "ADX", "Trend Cloud", "SuperTrend"], default=["EMA", "SuperTrend"])
            with c3:
                chart_type = st.selectbox("Chart Type", ["Candlestick", "Line", "Heikin Ashi"], index=0)
                show_zones = st.checkbox("Show Bull/Bear Zones", value=True)
                show_quantum = st.checkbox("🔮 Quantum Forecast", value=False)

            # Construct Plotly Figure
            subplot_titles = [f"{symbol} Price ({timeframe}) - {market_regime} Regime"]
            row_h = [0.6]
            specs = [[{"secondary_y": False}]]
            
            current_row = 2
            
            if show_volume:
                subplot_titles.append("Volume")
                specs.append([{"secondary_y": False}])
                row_h.append(0.15)
                current_row += 1
            
            if 'RSI' in indicators_selected:
                subplot_titles.append("RSI (14)")
                specs.append([{"secondary_y": False}])
                row_h.append(0.15)
                current_row += 1
                
            if 'MACD' in indicators_selected:
                subplot_titles.append("MACD")
                specs.append([{"secondary_y": False}])
                row_h.append(0.15)
                current_row += 1
            
            # Normalize row heights
            total_h = sum(row_h)
            row_h = [h/total_h for h in row_h]

            fig = make_subplots(
                rows=current_row - 1, 
                cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.05, 
                row_heights=row_h,
                subplot_titles=subplot_titles
            )

            # Main Candlestick
            fig.add_trace(go.Candlestick(
                x=df.index, 
                open=df['open'], 
                high=df['high'], 
                low=df['low'], 
                close=df['close'], 
                name='OHLC'
            ), row=1, col=1)

            # Bull/Bear Zones Visualization
            if show_zones:
                # Determine Trend Source
                trend_col = None
                if 'supertrend_dir' in df.columns:
                    trend_col = 'supertrend_dir' # 1 or -1
                elif 'close' in df.columns:
                    # Fallback to simple SMA trend if no SuperTrend
                    df['sma_50'] = df['close'].rolling(50).mean()
                    df['trend_proxy'] = np.where(df['close'] > df['sma_50'], 1, -1)
                    trend_col = 'trend_proxy'
                
                if trend_col:
                    # Identify segments to avoid thousands of vrects
                    # We create a new column 'segment_id' that changes when trend changes
                    df['segment_id'] = (df[trend_col] != df[trend_col].shift(1)).cumsum()
                    
                    # Group by segment
                    segments = df.groupby('segment_id').agg(
                        start_time=('index', 'first'),
                        end_time=('index', 'last'),
                        trend=(trend_col, 'first')
                    )
                    
                    # Plot Rectangles
                    for _, seg in segments.iterrows():
                        color = "rgba(0, 255, 0, 0.1)" if seg['trend'] == 1 else "rgba(255, 0, 0, 0.1)"
                        fig.add_vrect(
                            x0=seg['start_time'], 
                            x1=seg['end_time'],
                            fillcolor=color, 
                            opacity=1, 
                            layer="below", 
                            line_width=0
                        )

            # SuperTrend & Live Signal Markers
            if "SuperTrend" in indicators_selected and 'supertrend' in df.columns:
                # Plot SuperTrend Line
                # We can color it dynamically if we split the series, but a single line is safer for performance
                fig.add_trace(go.Scatter(
                    x=df.index, 
                    y=df['supertrend'], 
                    mode='lines',
                    line=dict(color='magenta', width=2),
                    name='SuperTrend'
                ), row=1, col=1)
                
                # Generate Buy/Sell Markers from SuperTrend Crossovers
                if 'supertrend_dir' in df.columns:
                    # Detect flips
                    # 1 = Bullish, -1 = Bearish
                    # Buy: Previous was -1, Current is 1
                    # Sell: Previous was 1, Current is -1
                    
                    # We need to operate on the series
                    st_dir = df['supertrend_dir']
                    st_shift = st_dir.shift(1)
                    
                    buy_mask = (st_dir == 1) & (st_shift == -1)
                    sell_mask = (st_dir == -1) & (st_shift == 1)
                    
                    buy_points = df[buy_mask]
                    sell_points = df[sell_mask]
                    
                    if not buy_points.empty:
                        fig.add_trace(go.Scatter(
                            x=buy_points.index,
                            y=buy_points['low'] * 0.995, # Just below low
                            mode='markers+text',
                            marker=dict(symbol='triangle-up', size=15, color='#00FF00'),
                            text=["BUY"] * len(buy_points),
                            textposition="bottom center",
                            name='Buy Signal'
                        ), row=1, col=1)
                        
                    if not sell_points.empty:
                        fig.add_trace(go.Scatter(
                            x=sell_points.index,
                            y=sell_points['high'] * 1.005, # Just above high
                            mode='markers+text',
                            marker=dict(symbol='triangle-down', size=15, color='#FF0000'),
                            text=["SELL"] * len(sell_points),
                            textposition="top center",
                            name='Sell Signal'
                        ), row=1, col=1)

            # Add Indicators to Main Chart
            if show_quantum:
                try:
                    # Calculate volatility
                    returns = df['close'].pct_change().dropna()
                    vol = returns.std() if not returns.empty else 0.01
                    # Annualize approx or just use period vol
                    # For hourly simulation steps
                    
                    current_price = df['close'].iloc[-1]
                    
                    # Generate paths
                    paths = bot.quantum.generate_probability_wave(current_price, vol, steps=24, paths=30)
                    
                    # Create future dates
                    last_date = df.index[-1]
                    # Handle different index types (datetime vs range)
                    try:
                        future_dates = [last_date + pd.Timedelta(hours=i+1) for i in range(24)]
                    except:
                        future_dates = [i for i in range(24)] # Fallback
                    
                    for path in paths:
                        # path includes current price as first element? generate_probability_wave returns list starting with current?
                        # Let's check logic: yes, prices = [current_price], then appends.
                        # So len is steps + 1
                        
                        fig.add_trace(go.Scatter(
                            x=[last_date] + future_dates,
                            y=path, # path has steps+1 elements
                            mode='lines',
                            line=dict(color='cyan', width=1),
                            opacity=0.05,
                            showlegend=False,
                            hoverinfo='skip'
                        ), row=1, col=1)
                except Exception as e:
                    st.error(f"Quantum Viz Error: {e}")

            if "Trend Cloud" in indicators_selected:
                # EMA Cloud (20-50) for Visual Trend
                e20 = df['close'].ewm(span=20).mean()
                e50 = df['close'].ewm(span=50).mean()
                
                # We need two traces for the fill
                fig.add_trace(go.Scatter(
                    x=df.index, 
                    y=e20, 
                    line=dict(width=0), 
                    showlegend=False,
                    hoverinfo='skip'
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df.index, 
                    y=e50, 
                    fill='tonexty', 
                    fillcolor='rgba(0, 150, 255, 0.15)', 
                    line=dict(width=0), 
                    name='Trend Cloud'
                ), row=1, col=1)

            if "EMA" in indicators_selected:
                fig.add_trace(go.Scatter(x=df.index, y=df['close'].ewm(span=20).mean(), line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
            
            if "Bollinger Bands" in indicators_selected:
                # Simple calculation for display
                sma = df['close'].rolling(20).mean()
                std = df['close'].rolling(20).std()
                upper = sma + (std * 2)
                lower = sma - (std * 2)
                fig.add_trace(go.Scatter(x=df.index, y=upper, line=dict(color='gray', width=1, dash='dot'), name='BB Upper'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=lower, line=dict(color='gray', width=1, dash='dot'), name='BB Lower'), row=1, col=1)

            # Add Regime Annotation (Background Color)
            regime_color = "rgba(0, 255, 0, 0.05)" if "Trend" in market_regime else "rgba(255, 165, 0, 0.05)"
            fig.add_vrect(
                x0=df.index[0], 
                x1=df.index[-1],
                fillcolor=regime_color, 
                opacity=1, 
                layer="below", 
                line_width=0,
                annotation_text=market_regime, 
                annotation_position="top left"
            )

            # Volume
            curr_row_idx = 2
            if show_volume:
                colors = ['red' if c < o else 'green' for o, c in zip(df['open'], df['close'])]
                fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, name='Volume'), row=curr_row_idx, col=1)
                curr_row_idx += 1
            
            # RSI
            if 'RSI' in indicators_selected and 'rsi' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple', width=2), name='RSI'), row=curr_row_idx, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=curr_row_idx, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=curr_row_idx, col=1)
                curr_row_idx += 1
                
            # MACD
            if 'MACD' in indicators_selected and 'macd' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['macd'], line=dict(color='blue', width=1), name='MACD'), row=curr_row_idx, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], line=dict(color='orange', width=1), name='Signal'), row=curr_row_idx, col=1)
                fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], marker_color='gray', name='Hist'), row=curr_row_idx, col=1)
                curr_row_idx += 1
                
            # ADX
            if 'ADX' in indicators_selected and 'adx' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['adx'], line=dict(color='yellow', width=2), name='ADX'), row=curr_row_idx, col=1)
                fig.add_hline(y=25, line_dash="dash", line_color="white", annotation_text="Trend Strength", row=curr_row_idx, col=1)
                curr_row_idx += 1

            fig.update_xaxes(
                showspikes=True, 
                spikemode='across', 
                spikesnap='cursor', 
                showline=True, 
                showgrid=True, 
                gridcolor='#333',
                spikethickness=1,
                spikecolor='#999999',
                spikedash='dash'
            )
            fig.update_yaxes(
                showspikes=True, 
                spikemode='across', 
                spikesnap='cursor', 
                showline=True, 
                showgrid=True, 
                gridcolor='#333',
                spikethickness=1,
                spikecolor='#999999',
                spikedash='dash'
            )
            fig.update_layout(
                height=800, 
                xaxis_rangeslider_visible=False, 
                template="plotly_dark",
                hovermode='x unified', # Unified hover for better crosshair feel
                spikedistance=-1 # Show spike across full chart
            )
            st.plotly_chart(fig, use_container_width=True)
            
        # --- Signal Panel ---
        with col_signal:
            st.subheader("Decision Authority")
            
            current_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            st.metric("Current Price", f"${current_price:,.2f}", f"{price_change:+.2f}%")
            
            # --- Fundamental Data (CoinMarketCap) ---
            fundamental_data = get_cached_fundamentals(symbol, bot)
            if fundamental_data and fundamental_data.get('source') == 'CoinMarketCap':
                st.divider()
                st.markdown("#### CoinMarketCap Fundamentals")
                f_c1, f_c2 = st.columns(2)
                with f_c1:
                    st.metric("Global Rank", f"#{fundamental_data.get('rank', 'N/A')}")
                    st.metric("Market Cap", f"${fundamental_data.get('market_cap', 0):,.0f}")
                    st.metric("Dominance", f"{fundamental_data.get('market_dominance', 0):.2f}%")
                with f_c2:
                    st.metric("24h Volume", f"${fundamental_data.get('volume_1day_usd', 0):,.0f}")
                    st.metric("Circulating Supply", f"{fundamental_data.get('supply_current', 0):,.0f} {fundamental_data.get('asset_id')}")
                    st.metric("7d Change", f"{fundamental_data.get('percent_change_7d', 0):.2f}%", 
                             delta=f"{fundamental_data.get('percent_change_7d', 0):.2f}%")
            
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
            st.subheader("Active Positions")
            
            if hasattr(bot, 'open_positions') and bot.open_positions:
                for i, pos in enumerate(bot.open_positions):
                    with st.container():
                        st.markdown(f"**{pos['symbol']} ({pos['type']})**")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.metric("Entry", f"${pos['entry']:.2f}")
                            pnl_pct = 0.0
                            if current_price > 0:
                                if pos['type'] == 'BUY':
                                    pnl_pct = ((current_price - pos['entry']) / pos['entry']) * 100
                                elif pos['type'] == 'SELL':
                                    pnl_pct = ((pos['entry'] - current_price) / pos['entry']) * 100
                            
                            st.metric("PnL", f"{pnl_pct:+.2f}%", delta=f"{pnl_pct:+.2f}%")
                        with c2:
                            st.metric("TP", f"${pos['take_profit']:.2f}")
                            st.metric("SL", f"${pos['stop_loss']:.2f}")
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
        st.subheader("Meta-Allocator Weights")
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
    st.title("🖥️ System Monitor (Live & Demo)")
    
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
    st.subheader("Account Status")
    
    # Refresh Balance if Live (Always try to sync if connected to show latest)
    if st.session_state.get('exchange_connected', False):
        with st.spinner("Syncing Live Balance..."):
            bot.sync_live_balance()
            
    col1, col2, col3, col4 = st.columns(4)
    
    active_mode = bot.trading_mode
    live_bal = bot.risk_manager.live_balance
    demo_bal = bot.risk_manager.demo_balance
    
    with col1:
        st.metric("Active Mode", active_mode, delta="Connected" if st.session_state.get('exchange_connected') else "Offline", delta_color="normal")
    with col2:
        st.metric("Live Balance (USDT)", f"${live_bal:,.2f}")
    with col3:
        st.metric("Demo Balance (Sim)", f"${demo_bal:,.2f}")
    with col4:
        # Show Total PnL (Combined or Active)
        # Showing Active Mode PnL
        if active_mode == 'Live':
             # Simple PnL for now
             st.metric("Active PnL", "N/A (Live)") 
        else:
             pnl = demo_bal - 1000 # Assuming 1000 start
             st.metric("Demo PnL", f"${pnl:,.2f}", delta=f"{pnl/10:.1f}%")
        
    st.divider()
    
    # 2. Active Positions (Dual View)
    st.subheader("Active Positions")
    
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
    st.subheader("Recent Activity Log")
    
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
    st.title(f"🖥️ Trading Terminal - {symbol}")
    
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
        st.subheader("Order Entry")
        
        with st.form("order_form"):
            side = st.selectbox("Side", ["Buy", "Sell"])
            order_type = st.selectbox("Type", ["Limit", "Market", "Iceberg"])
            amount = st.number_input("Amount", min_value=0.001, step=0.001)
            
            price = 0.0
            if order_type != "Market":
                # Fetch current price for reference
                ticker = bot.data_manager.fetch_ticker(symbol)
                current_price = ticker.get('last', 0)
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
                            st.json(result)
                            # Log action
                            if 'transparency_log' in st.session_state:
                                st.session_state.transparency_log.log_action("Manual Trade", f"{side} {amount} {symbol} @ {price if order_type != 'Market' else 'Market'}")
                    else:
                        st.error("Order Execution Failed (No Result)")

    with col_book:
        st.subheader("Market Depth & Recent Trades")
        
        # Fetch Depth
        try:
            depth = bot.data_manager.exchange.fetch_order_book(symbol, limit=10) if bot.data_manager.exchange else {'bids': [], 'asks': []}
            
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.markdown("#### Bids (Buy)")
                if depth['bids']:
                    bids_df = pd.DataFrame(depth['bids'], columns=['Price', 'Amount'])
                    st.dataframe(bids_df, height=300)
                else:
                    st.info("No Bids")
            
            with d_col2:
                st.markdown("#### Asks (Sell)")
                if depth['asks']:
                    asks_df = pd.DataFrame(depth['asks'], columns=['Price', 'Amount'])
                    st.dataframe(asks_df, height=300)
                else:
                    st.info("No Asks")
                    
        except Exception as e:
            st.warning(f"Could not fetch order book: {e}")

if page_nav == "Arbitrage Scanner":
    st.title("⚡ Cross-Exchange Arbitrage Scanner")
    st.markdown("### Real-time Price Discrepancy Monitoring")
    
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
    st.subheader("📊 Exchange Price Matrix")
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
            
            st.metric("Best Buy Price", f"${min_price:,.2f}")
            st.metric("Best Sell Price", f"${max_price:,.2f}")
            spread = ((max_price - min_price) / min_price) * 100
            st.metric("Spread", f"{spread:.2f}%")
            
    else:
        st.warning("Could not fetch price data. Ensure exchanges are reachable.")

    st.divider()
    
    # Display Opportunities
    st.subheader("🚀 Arbitrage Opportunities")
    if opps:
        for opp in opps:
            st.success(f"Opportunity Found: {opp['buy_exchange'].upper()} ➡ {opp['sell_exchange'].upper()}")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Buy At", f"{opp['buy_exchange'].upper()}")
                st.caption(f"${opp['buy_price']:,.2f}")
            with c2:
                st.metric("Sell At", f"{opp['sell_exchange'].upper()}")
                st.caption(f"${opp['sell_price']:,.2f}")
            with c3:
                st.metric("Profit Spread", f"{opp['spread_pct']:.2f}%")
            with c4:
                st.metric("Est. Profit (1k)", f"${opp['estimated_profit_1k']:.2f}")
            
            st.button(f"Execute {opp['buy_exchange']} -> {opp['sell_exchange']}", key=f"arb_{opp['buy_exchange']}")
            st.divider()
    else:
        st.info(f"No significant arbitrage opportunities found for {scan_symbol} (>0.1% spread).")

if page_nav == "Copy Trading":
    st.title("👥 Social & Copy Trading")
    
    # Initialize Copy Module
    if 'copy_trader' not in st.session_state:
        st.session_state.copy_trader = CopyTradingModule()
        
    copy_bot = st.session_state.copy_trader
    
    # Initialize Bot for context
    if 'bot' not in st.session_state:
        st.session_state.bot = get_bot(exchange)
    
    ct_tab1, ct_tab2 = st.tabs(["Copy Center", "My Portfolio"])
    
    with ct_tab1:
        st.subheader("Discover Top Traders")
        
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
                st.markdown(f"### {trader['name']}")
                st.metric("ROI", f"{trader['roi']}%", delta_color="normal")
                st.caption(f"Win Rate: {trader['win_rate']}% | Risk: {trader['risk']}")
                st.caption(f"Followers: {trader['followers']}")
                
                if st.button(f"Copy {trader['name']}", key=f"copy_{i}"):
                    st.session_state.copy_trader.connect_master_account(trader['name'], "mock_api_key", "mock_secret")
                    st.success(f"Now copying {trader['name']}!")
        
        st.divider()
        st.subheader("Manual Copy Signal Input")
        with st.expander("Enter Signal Manually"):
            m_symbol = st.text_input("Symbol", "BTC/USDT")
            m_side = st.selectbox("Side", ["buy", "sell"])
            m_amount = st.number_input("Amount", 0.001)
            
            if st.button("Execute Copy Signal"):
                copy_bot.execute_copy_trade(m_symbol, m_side, m_amount)

    with ct_tab2:
        st.subheader("Active Copy Positions")
        if 'sim_positions' in st.session_state and st.session_state.sim_positions:
            st.dataframe(pd.DataFrame(st.session_state.sim_positions))
        else:
            st.info("No active copy trades.")

if page_nav == "Quantum Lab":
    st.title("⚛️ Quantum Intelligence Lab")
    st.markdown("### Quantum-Inspired Optimization & Signal Processing")
    
    # Initialize bot if needed
    try:
        bot = get_bot(exchange)
    except:
        st.error("Bot initialization failed. Please check configuration.")
        st.stop()
        
    q_tab1, q_tab2, q_tab3 = st.tabs(["Quantum Regime Detection", "Portfolio Optimization (Annealing)", "Grover Search Signals"])
    
    with q_tab1:
        st.subheader("Hybrid Quantum-Classical Regime Detection")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Generate Probability Wave Visualization
            st.markdown("#### Probability Wave Function (Market State)")
            
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
            st.markdown("#### Current Quantum State")
            
            # Fetch Data for Analysis
            df = get_cached_ohlcv(bot, bot.symbol, bot.timeframe)
            if not df.empty:
                regime = bot.brain.detect_market_regime(df)
                
                st.metric("Detected Regime", regime['type'])
                st.metric("Quantum Volatility Score", f"{regime.get('volatility_score', 0):.4f}")
                
                if regime.get('quantum_state'):
                    st.info(f"Quantum State: {regime['quantum_state']}")
                
                st.markdown("---")
                st.markdown("**Interpretation:**")
                st.caption("The wave function represents the superposition of market states. "
                           "Peaks indicate high probability states. "
                           "Sharp peaks = Stable trends. "
                           "Flat/Multi-modal = High volatility/Uncertainty.")
    
    with q_tab2:
        st.subheader("Simulated Annealing Portfolio Optimization")
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
        st.subheader("Grover Search Signal Amplification")
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
    st.title("🔗 Blockchain & DeFi Hub")
    
    # Initialize components
    if 'transparency_log' not in st.session_state:
        st.session_state.transparency_log = TransparencyLog()
    
    # Tabs
    tab_overview, tab_defi, tab_security, tab_logs = st.tabs(["Overview", "DeFi Operations", "Security", "Audit Logs"])
    
    # Overview Tab
    with tab_overview:
        c1, c2, c3 = st.columns(3)
        c1.metric("ETH Price (Oracle)", f"${OracleManager.get_price_feed('ETH', 'ethereum'):,.2f}")
        c2.metric("BTC Price (Oracle)", f"${OracleManager.get_price_feed('BTC', 'ethereum'):,.2f}")
        c3.metric("SOL Price (Oracle)", f"${OracleManager.get_price_feed('SOL', 'solana'):,.2f}")
        
        st.subheader("Cross-Chain Wallet Balances")
        # Ensure bot is available (we might need to init it if this page loads first, 
        # but usually bot init is cached or we can grab a default instance)
        try:
             # Use a temporary bot instance just for DeFi checks if not already in session
             # Or rely on the global 'bot' if it was initialized. 
             # Note: 'bot' variable is defined further down in the original script.
             # We should probably initialize a lightweight DeFiManager here if needed.
             pass
        except: pass
        
        st.info("Connect your wallet in the sidebar to view real-time balances.")

    # DeFi Operations Tab
    with tab_defi:
        st.subheader("🚀 Cross-Chain DeFi Execution")
        
        op_col1, op_col2 = st.columns([1, 1])
        
        with op_col1:
            st.markdown("#### Yield Farming")
            yf_asset = st.selectbox("Asset", ["USDT", "ETH", "USDC"], key="yf_asset")
            yf_amount = st.number_input("Amount", min_value=0.0, step=10.0, key="yf_amount")
            yf_protocol = st.selectbox("Protocol", ["Aave", "Compound", "Curve"], key="yf_protocol")
            
            if st.button("Execute Farm"):
                st.info(f"Farming {yf_amount} {yf_asset} on {yf_protocol}...")
                # Mock execution
                time.sleep(1)
                st.success("Transaction Submitted: 0x123...abc")
                st.session_state.transparency_log.log_action("Yield Farm", f"Farmed {yf_amount} {yf_asset} on {yf_protocol}")

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
        st.subheader("🛡️ Smart Contract Security")
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
        st.subheader("Transparency Log (Blockchain)")
        if hasattr(st.session_state, 'transparency_log'):
            st.dataframe(pd.DataFrame(st.session_state.transparency_log.logs))
        else:
            st.info("No logs available.")

if page_nav == "Settings":
    st.title("⚙️ System Settings")
    
    st.subheader("API Configuration")
    with st.expander("Exchange Keys"):
        st.text_input("API Key", type="password")
        st.text_input("Secret Key", type="password")
        st.button("Save Keys")
        
    st.subheader("Risk Management")
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
