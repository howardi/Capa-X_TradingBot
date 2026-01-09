import streamlit as st
import time
import core.styles as styles

def render_top_nav(username, status="ONLINE"):
    """
    Renders the fixed top navigation bar.
    """
    # Use explicit HTML string with no indentation to avoid Markdown code block interpretation
    html_content = f'<div class="top-nav"><div class="nav-item"><span class="status-dot" style="background-color: var(--status-success);"></span><span>STATUS: {status}</span></div><div class="nav-item"><span>DEPLOY: PROD-V1.2</span></div><div style="flex-grow: 1;"></div><div class="nav-item"><span>{time.strftime("%H:%M:%S UTC", time.gmtime())}</span></div><div class="nav-item" style="margin-left: 20px;"><span class="nav-badge" style="background: rgba(0, 242, 255, 0.1); color: var(--accent-cyan);">{username}</span></div><div class="nav-item" style="margin-left: 15px;"><a href="?logout=true" target="_self" style="text-decoration: none; color: var(--text-secondary); font-size: 0.8rem;">LOGOUT</a></div></div>'
    st.markdown(html_content, unsafe_allow_html=True)

def render_sidebar_menu():
    """
    Renders the modernized sidebar menu with mutual exclusivity between sections.
    """
    # Initialize active page if not present
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Trading Dashboard"

    with st.sidebar:
        # Branding
        branding_html = '<div style="text-align: center; margin-bottom: 20px;"><div style="width: 60px; height: 60px; background: linear-gradient(135deg, #00f2ff, #2563eb); border-radius: 50%; margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.5rem; color: #fff; box-shadow: 0 0 20px rgba(0, 242, 255, 0.3);">CX</div><h2 style="margin: 0; font-size: 1.2rem; letter-spacing: 2px; color: #fff;">CAPA-X</h2><p style="margin: 0; font-size: 0.7rem; color: var(--text-muted);">INTELLIGENT TRADING</p></div>'
        st.markdown(branding_html, unsafe_allow_html=True)
        
        # Define Options
        nav_options = [
            "Trading Dashboard", 
            "Strategy Intelligence", 
            "Manual Trading",
            "AI Market Analyzer",
            "Wallet & Execution", 
            "Fiat Gateway (NGN)",
            "Performance Analytics", 
            "Active Positions",
            "System Targets",
            "Web3 Integration"
        ]
        
        lab_options = [
            "Arbitrage Scanner",
            "Copy Trading",
            "DeFi Bridge",
            "DeFi Staking",
            "Quantum Lab",
            "Risk Manager"
        ]
        
        # Determine current indices
        current_page = st.session_state.active_page
        nav_index = nav_options.index(current_page) if current_page in nav_options else None
        lab_index = lab_options.index(current_page) if current_page in lab_options else None
        
        # Callbacks
        def on_nav_change():
            st.session_state.active_page = st.session_state.main_nav_radio
            
        def on_lab_change():
            st.session_state.active_page = st.session_state.lab_nav_radio

        # Navigation Section
        st.markdown("<div style='margin-bottom: 10px; color: var(--text-muted); font-size: 0.8rem; font-weight: 600; padding-left: 10px;'>MAIN MODULES</div>", unsafe_allow_html=True)
        
        st.radio(
            "Navigation", 
            nav_options, 
            index=nav_index, 
            label_visibility="collapsed", 
            key="main_nav_radio", 
            on_change=on_nav_change
        )
        
        # Labs Section
        st.markdown("<div style='margin-top: 20px; margin-bottom: 10px; color: var(--text-muted); font-size: 0.8rem; font-weight: 600; padding-left: 10px;'>ADVANCED LABS</div>", unsafe_allow_html=True)
        
        st.radio(
            "Labs", 
            lab_options, 
            index=lab_index, 
            label_visibility="collapsed", 
            key="lab_nav_radio", 
            on_change=on_lab_change
        )
        
        return st.session_state.active_page
