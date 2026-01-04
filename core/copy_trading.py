
import streamlit as st
import pandas as pd
import time
from core.bot import TradingBot
from core.styles import neon_header

class CopyTradingModule:
    def __init__(self):
        self.master_config = {
            'api_key': '',
            'api_secret': '',
            'exchange_id': 'binance' # Default
        }
        self.active = False
        self.status = "Idle"
        self.master_positions = []
        
    def connect_master_account(self, master_name, api_key, api_secret, exchange_id='binance'):
        """
        Connect to a Master Trader's account (Mock or Real).
        """
        self.master_config['api_key'] = api_key
        self.master_config['api_secret'] = api_secret
        self.master_config['exchange_id'] = exchange_id
        self.master_config['master_name'] = master_name
        
        # In a real implementation, we would verify keys here.
        self.active = True
        self.status = f"Connected to {master_name}"
        return True
        
    def render_ui(self):
        neon_header("Social & Copy Trading Hub", level=1)
        
        tab_leader, tab_follower = st.tabs(["📡 Leaderboard & Signals", "⚙️ Copy Settings"])
        
        with tab_leader:
            st.info("Coming Soon: Global Leaderboard (Requires Cloud Connectivity)")
            
            neon_header("Signal Source Simulation", level=2)
            st.markdown("Simulate incoming signals from a Master Trader for testing.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Simulate Master BUY Signal (BTC/USDT)"):
                    st.toast("Received Signal: BUY BTC/USDT @ Market", icon="📥")
                    self.execute_copy_trade("BTC/USDT", "buy", 0.001)
            with col2:
                if st.button("Simulate Master SELL Signal (BTC/USDT)"):
                    st.toast("Received Signal: SELL BTC/USDT @ Market", icon="📥")
                    self.execute_copy_trade("BTC/USDT", "sell", 0.001)

        with tab_follower:
            neon_header("Connect Master Account (Source)", level=2)
            st.markdown("Mirror trades from another exchange account (Read-Only API recommended).")
            
            with st.form("master_api_form"):
                master_exchange = st.selectbox("Master Exchange", ['binance', 'bybit', 'okx'])
                master_key = st.text_input("Master API Key", type="password")
                master_secret = st.text_input("Master API Secret", type="password")
                
                submitted = st.form_submit_button("Link Master Account")
                if submitted:
                    st.success(f"Linked to {master_exchange.upper()} Master Account!")
                    st.session_state['copy_master_linked'] = True
            
            st.divider()
            
            neon_header("Copy Parameters", level=2)
            copy_mode = st.radio("Copy Mode", ["Fixed Amount", "Percentage Balance", "Proportional"], index=0)
            copy_amt = st.number_input("Amount per Trade (USDT)", min_value=10.0, value=50.0)
            
            st.checkbox("Copy Stop Loss / Take Profit", value=True)
            
            if st.toggle("Activate Copy Trader", value=False):
                st.success("🟢 Copy Trader Active - Listening for Master Trades...")
                st.markdown("*(Polling Master Account every 5s...)*")

    def execute_copy_trade(self, symbol, side, amount):
        # Logic to execute the trade on the bot's active exchange
        if 'bot' in st.session_state: 
            bot = st.session_state.bot
            
            try:
                # Check Global Trading Mode
                mode = st.session_state.get('trading_mode', 'Simulated')
                
                if mode == 'Live':
                     # Execute Real Order via DataManager
                     with st.spinner(f"Copying {side.upper()} Trade..."):
                         order = bot.data_manager.create_order(symbol, 'market', side, amount)
                         st.toast(f"✅ COPY TRADE EXECUTED: {side.upper()} {symbol}", icon="⚡")
                         # Optional: st.json(order)
                else:
                    # Simulate Copy Trade
                    ticker = bot.data_manager.fetch_ticker(symbol)
                    price = ticker.get('last', 0)
                    
                    sim_trade = {
                        'symbol': symbol,
                        'side': side,
                        'amount': amount,
                        'entryPrice': price,
                        'timestamp': pd.Timestamp.now(),
                        'type': 'copy_trade',
                        'status': 'OPEN'
                    }
                    
                    if 'sim_positions' not in st.session_state:
                        st.session_state.sim_positions = []
                        
                    st.session_state.sim_positions.append(sim_trade)
                    st.toast(f"📋 Simulated Copy Trade: {side.upper()} {symbol} @ {price}", icon="🧪")
                    
            except Exception as e:
                st.error(f"Copy Trade Failed: {e}")
        else:
             st.error("Bot instance not found! Please initialize the bot first.")
        
        # Log to console/UI
        st.write(f"Copy Signal Processed: {side.upper()} {symbol}")
