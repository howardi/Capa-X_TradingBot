import streamlit as st
import os
import base64

def apply_custom_styles():
    st.markdown("""
        <style>
        /* --- GLOBAL FONTS & COLORS --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
        
        :root {
            --bg-color: #0a0e17;
            --card-bg: rgba(20, 25, 35, 0.7);
            --sidebar-bg: #05080d;
            --text-primary: #e0e6ed;
            --text-secondary: #94a3b8;
            --accent-cyan: #00f2ff;
            --accent-purple: #bd00ff;
            --accent-green: #00ff9d;
            --accent-red: #ff0055;
            --glass-border: 1px solid rgba(255, 255, 255, 0.1);
            --neon-shadow: 0 0 10px rgba(0, 242, 255, 0.3);
        }

        /* --- MAIN CONTAINER --- */
        .stApp {
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(189, 0, 255, 0.1) 0%, transparent 20%),
                radial-gradient(circle at 90% 80%, rgba(0, 242, 255, 0.1) 0%, transparent 20%);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
        }

        /* --- SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
            text-shadow: 0 0 5px rgba(0, 242, 255, 0.5);
        }

        /* --- HEADERS --- */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #fff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        h1 {
            font-size: 2.5rem !important;
            padding-bottom: 1rem;
        }

        /* --- METRICS & CARDS --- */
        [data-testid="stMetric"], div.css-1r6slb0, div.stDataFrame {
            background: var(--card-bg);
            border: var(--glass-border);
            border-radius: 12px;
            padding: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(0, 242, 255, 0.1);
            border-color: rgba(0, 242, 255, 0.3);
        }

        [data-testid="stMetricLabel"] {
            color: var(--text-secondary) !important;
            font-size: 0.9rem !important;
            font-family: 'JetBrains Mono', monospace;
        }

        [data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: var(--text-primary) !important;
        }

        /* --- DATAFRAME --- */
        [data-testid="stDataFrame"] {
            background: transparent !important;
            border: none !important;
        }
        
        div[data-testid="stDataFrame"] > div {
            background: var(--card-bg);
            border-radius: 12px;
            border: var(--glass-border);
            overflow: hidden;
        }

        /* --- BUTTONS --- */
        .stButton > button {
            background: linear-gradient(45deg, #1a1f2e, #252a3a);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 242, 255, 0.3);
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .stButton > button:hover {
            background: linear-gradient(45deg, rgba(0, 242, 255, 0.2), rgba(189, 0, 255, 0.2));
            border-color: var(--accent-cyan);
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.4);
            color: #fff;
        }

        /* Primary Button Style (e.g. Panic Button) */
        button[kind="primary"] {
            background: linear-gradient(45deg, #ff0055, #bd00ff) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 0 10px rgba(255, 0, 85, 0.5);
        }
        
        button[kind="primary"]:hover {
            box-shadow: 0 0 20px rgba(255, 0, 85, 0.8);
        }

        /* --- INPUTS --- */
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > div {
            background-color: rgba(0, 0, 0, 0.3) !important;
            color: var(--text-primary) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            font-family: 'JetBrains Mono', monospace;
        }
        
        .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus {
            border-color: var(--accent-cyan) !important;
            box-shadow: 0 0 0 1px var(--accent-cyan) !important;
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            background-color: transparent;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 8px;
            color: var(--text-secondary);
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            padding: 10px 20px;
        }

        .stTabs [aria-selected="true"] {
            background: rgba(0, 242, 255, 0.1) !important;
            color: var(--accent-cyan) !important;
            border: 1px solid rgba(0, 242, 255, 0.3) !important;
        }

        /* --- EXPANDERS --- */
        .streamlit-expanderHeader {
            background-color: var(--card-bg) !important;
            border-radius: 8px !important;
            color: var(--text-primary) !important;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            border: var(--glass-border);
        }
        
        .streamlit-expanderContent {
            background-color: rgba(0,0,0,0.2) !important;
            border-radius: 0 0 8px 8px !important;
            border-left: var(--glass-border);
            border-right: var(--glass-border);
            border-bottom: var(--glass-border);
            color: var(--text-secondary) !important;
        }

        /* --- DIVIDERS --- */
        hr {
            border-color: rgba(255, 255, 255, 0.1) !important;
        }
        
        /* --- CUSTOM SCROLLBAR --- */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-color); 
        }
        
        ::-webkit-scrollbar-thumb {
            background: #334155; 
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-cyan); 
        }
        
        /* --- ANIMATIONS --- */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(0, 242, 255, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(0, 242, 255, 0); }
            100% { box-shadow: 0 0 0 0 rgba(0, 242, 255, 0); }
        }

        /* --- CUSTOM CLASSES --- */
        .cyber-card {
            background: linear-gradient(135deg, rgba(20, 25, 35, 0.9) 0%, rgba(10, 14, 23, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .cyber-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 242, 255, 0.15);
            border-color: rgba(0, 242, 255, 0.4);
        }
        
        .cyber-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, #00f2ff, transparent);
        }

        /* --- TOASTS --- */
        div[data-testid="stToast"] {
            background-color: var(--card-bg) !important;
            border: 1px solid var(--accent-cyan) !important;
            color: white !important;
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.2);
        }

        </style>
    """, unsafe_allow_html=True)

def card_container(title, content):
    st.markdown(f"""
    <div style="
        background: rgba(20, 25, 35, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    ">
        <h4 style="margin-top: 0; color: #00f2ff; font-family: 'Inter', sans-serif;">{title}</h4>
        <div style="color: #e0e6ed;">{content}</div>
    </div>
    """, unsafe_allow_html=True)

def metric_card(label, value, delta=None, color=None):
    """
    Custom HTML Metric Card for Cyberpunk Look
    """
    delta_html = ""
    if delta:
        delta_color = "#00ff9d" if not delta.startswith("-") else "#ff0055"
        delta_html = f'<span style="color: {delta_color}; font-size: 0.8rem; margin-left: 10px;">{delta}</span>'
    
    val_color = color if color else "#e0e6ed"
    
    st.markdown(f"""
    <div class="cyber-card">
        <div style="color: #94a3b8; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">
            {label}
        </div>
        <div style="font-size: 1.8rem; font-weight: 700; color: {val_color}; font-family: 'Inter', sans-serif; display: flex; align-items: baseline;">
            {value}
            {delta_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def neon_header(text, level=1):
    font_size = "2.5rem" if level == 1 else ("1.8rem" if level == 2 else "1.4rem")
    st.markdown(f"""
    <h{level} style="
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        background: linear-gradient(90deg, #fff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: {font_size};
        margin-top: 20px;
        margin-bottom: 15px;
        text-shadow: 0 0 30px rgba(0, 242, 255, 0.2);
    ">
        {text}
    </h{level}>
    """, unsafe_allow_html=True)

def cyberpunk_logo(logo_path=os.path.join("assets", "logo.png")):
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        # Responsive Logo Image with Glow
        logo_html = f'''
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{encoded}" 
                     style="
                        width: 150px; 
                        height: 150px; 
                        object-fit: contain; 
                        border-radius: 50%; 
                        box-shadow: 0 0 30px rgba(0, 242, 255, 0.3);
                        transition: transform 0.3s ease;
                     "
                     onmouseover="this.style.transform='scale(1.05)'"
                     onmouseout="this.style.transform='scale(1)'"
                >
            </div>
        '''
        # Hide Text if Logo is present (Cleaner look for CapacityBay)
        text_html = "" 
    else:
        logo_html = """
        <div style="
            display: inline-block;
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #00f2ff, #bd00ff);
            border-radius: 50%;
            margin-bottom: 20px;
            box-shadow: 0 0 30px rgba(0, 242, 255, 0.5);
            display: flex; align-items: center; justify-content: center; font-size: 40px;
        ">🦅</div>
        """
        text_html = """
        <h1 style="
            color: #fff; 
            font-size: 3rem; 
            font-weight: 800;
            letter-spacing: -2px;
            margin: 0;
            text-shadow: 0 0 20px rgba(0, 242, 255, 0.5);
        ">CAPA-X</h1>
        """

    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 30px; animation: fadeIn 1s ease-in;">
        {logo_html}
        {text_html}
        <p style="
            color: #00f2ff; 
            font-family: 'JetBrains Mono', monospace; 
            letter-spacing: 2px;
            text-transform: uppercase;
            font-size: 0.8rem;
            opacity: 0.8;
        ">Quantum Trading Intelligence</p>
    </div>
    """, unsafe_allow_html=True)
