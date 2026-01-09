import streamlit as st
import os
import base64

def apply_custom_styles():
    st.markdown("""
<style>
/* --- GLOBAL FONTS & COLORS --- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-color: #050505; /* Deep Black for contrast */
    --card-bg: rgba(20, 25, 35, 0.6);
    --card-hover: rgba(30, 35, 45, 0.8);
    --sidebar-bg: #030303;
    
    /* Text Colors */
    --text-primary: #f0f4f8;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    
    /* Brand Accents */
    --accent-cyan: #00f2ff;
    --accent-blue: #2563eb;
    --accent-purple: #bd00ff;
    --accent-pink: #f472b6;
    
    /* Trading Colors */
    --trade-long: #00ff9d;
    --trade-short: #ff0055;
    --trade-neutral: #cbd5e1;
    
    /* Status Colors */
    --status-success: #10b981;
    --status-warning: #f59e0b;
    --status-error: #ef4444;
    --status-info: #3b82f6;
    
    /* Glassmorphism */
    --glass-border: 1px solid rgba(255, 255, 255, 0.08);
    --glass-highlight: 1px solid rgba(255, 255, 255, 0.15);
    --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    
    /* Neon Glows */
    --neon-cyan: 0 0 10px rgba(0, 242, 255, 0.4);
    --neon-green: 0 0 10px rgba(0, 255, 157, 0.4);
    --neon-red: 0 0 10px rgba(255, 0, 85, 0.4);
}

/* --- MAIN CONTAINER --- */
.stApp {
    background-color: var(--bg-color);
    background-image: 
        radial-gradient(circle at 15% 50%, rgba(76, 29, 149, 0.08) 0%, transparent 25%),
        radial-gradient(circle at 85% 30%, rgba(6, 182, 212, 0.08) 0%, transparent 25%);
    font-family: 'Inter', sans-serif;
    color: var(--text-primary);
}

/* --- SIDEBAR --- */
[data-testid="stSidebar"] {
    background-color: var(--sidebar-bg);
    border-right: 1px solid rgba(255, 255, 255, 0.03);
}

[data-testid="stSidebar"] .stMarkdown h1, 
[data-testid="stSidebar"] .stMarkdown h2, 
[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--accent-cyan);
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 1.1rem;
}

/* --- TOP NAVIGATION BAR --- */
.top-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(10, 10, 12, 0.8);
    backdrop-filter: blur(12px);
    border-bottom: var(--glass-border);
    padding: 0.75rem 1.5rem;
    margin: -1rem -1.5rem 1.5rem -1.5rem; /* Negative margin to span full width */
    position: sticky;
    top: 0;
    z-index: 999;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.nav-badge {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
}

.status-dot {
    height: 8px;
    width: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
}

/* --- HEADERS --- */
h1, h2, h3 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
}

h1 { font-size: clamp(1.8rem, 5vw, 2.5rem) !important; }
h2 { font-size: clamp(1.4rem, 4vw, 2rem) !important; }
h3 { font-size: clamp(1.1rem, 3vw, 1.5rem) !important; }

/* --- METRICS & CARDS --- */
[data-testid="stMetric"], div.css-1r6slb0, div.stDataFrame {
    background: var(--card-bg);
    border: var(--glass-border);
    border-radius: 8px;
    padding: 16px;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    transition: all 0.2s ease-in-out;
}

[data-testid="stMetric"]:hover {
    background: var(--card-hover);
    border: var(--glass-highlight);
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: clamp(0.7rem, 2vw, 0.85rem) !important;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: clamp(1.2rem, 4vw, 1.8rem) !important;
    color: var(--text-primary) !important;
}

/* --- BUTTONS --- */
.stButton > button {
    background: rgba(255, 255, 255, 0.03);
    color: var(--text-primary);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.2s ease;
    padding: 0.5rem 1rem;
}

.stButton > button:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: var(--accent-cyan);
    color: var(--accent-cyan);
    box-shadow: 0 0 12px rgba(0, 242, 255, 0.15);
}

/* Primary / Action Button */
button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

button[kind="primary"]:hover {
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5);
    transform: translateY(-1px);
}

/* --- INPUTS --- */
.stTextInput > div > div > input, 
.stNumberInput > div > div > input, 
.stSelectbox > div > div > div {
    background-color: rgba(0, 0, 0, 0.4) !important;
    color: var(--text-primary) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace;
}

.stTextInput > div > div > input:focus, 
.stNumberInput > div > div > input:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 0 2px rgba(0, 242, 255, 0.1) !important;
}

/* --- TABS --- */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: transparent;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding-bottom: 2px;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    border-radius: 6px 6px 0 0;
    color: var(--text-secondary);
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    padding: 8px 16px;
    border: none;
    transition: all 0.2s;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.02);
}

.stTabs [aria-selected="true"] {
    color: var(--accent-cyan) !important;
    border-bottom: 2px solid var(--accent-cyan) !important;
    background: linear-gradient(to top, rgba(0, 242, 255, 0.05), transparent) !important;
}

/* --- CUSTOM CLASSES --- */
.glass-panel {
    background: var(--card-bg);
    border: var(--glass-border);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(12px);
    box-shadow: var(--glass-shadow);
    margin-bottom: 16px;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding-bottom: 12px;
}

.panel-title {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    color: var(--text-primary);
    font-size: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

.data-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    font-size: 0.9rem;
}

.data-label {
    color: var(--text-secondary);
}

.data-value {
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
}

/* --- SCROLLBAR --- */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent; 
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1); 
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2); 
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

/* --- FORMS --- */
[data-testid="stForm"] {
    background: rgba(20, 25, 35, 0.7);
    border: 1px solid rgba(0, 242, 255, 0.2);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(10px);
}

/* --- CONTROL PANEL --- */
.control-panel-container {
    background: rgba(20, 25, 35, 0.6);
    border: 1px solid rgba(0, 242, 255, 0.1);
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 20px;
    backdrop-filter: blur(10px);
    display: flex;
    align-items: center;
    gap: 15px;
}

/* --- RESPONSIVENESS --- */
@media (max-width: 768px) {
    .control-panel-container {
        flex-direction: column;
        align-items: stretch;
        gap: 10px;
        padding: 10px;
    }
}

    .stApp {
        font-size: 14px;
    }
    h1 {
        font-size: 1.8rem !important;
    }
    h2 {
        font-size: 1.5rem !important;
    }
    h3 {
        font-size: 1.2rem !important;
    }
    .cyber-card {
        padding: 12px;
        margin-bottom: 15px;
    }
    /* Stack columns on mobile */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 auto !important;
        min-width: 100% !important;
    }
    
    /* Touch-friendly buttons */
    .stButton > button {
        width: 100%;
        min-height: 48px; /* Touch target size */
        font-size: 1rem;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    
    /* Input fields bigger for touch */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input, 
    .stSelectbox > div > div > div {
        min-height: 45px;
        font-size: 16px; /* Prevent zoom on iOS */
    }
    
    /* Tabs stacking or scrollable */
    .stTabs [data-baseweb="tab-list"] {
        flex-wrap: wrap;
        gap: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        flex-grow: 1;
        text-align: center;
        padding: 10px 5px;
    }
    
    /* Adjust padding for main container */
    .block-container {
        padding-top: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}

</style>
""", unsafe_allow_html=True)

def card_container(title, content):
    st.markdown(f'''
    <div style="background: rgba(20, 25, 35, 0.7); 
                border: 1px solid rgba(255, 255, 255, 0.1); 
                border-radius: 12px; 
                padding: clamp(15px, 3vw, 25px); 
                backdrop-filter: blur(10px); 
                margin-bottom: 20px;">
        <h4 style="margin-top: 0; color: #00f2ff; font-family: 'Inter', sans-serif; font-size: clamp(1rem, 2.5vw, 1.2rem);">{title}</h4>
        <div style="color: #e0e6ed; font-size: clamp(0.9rem, 2vw, 1rem); line-height: 1.5;">{content}</div>
    </div>
    ''', unsafe_allow_html=True)

def metric_card(label, value, delta=None, color=None):
    """
    Custom HTML Metric Card for Cyberpunk Look - Responsive
    """
    delta_html = ""
    if delta:
        delta_color = "#00ff9d" if not delta.startswith("-") else "#ff0055"
        delta_html = f'<span style="color: {delta_color}; font-size: clamp(0.7rem, 2vw, 0.9rem); margin-left: 10px;">{delta}</span>'
    
    val_color = color if color else "#e0e6ed"
    
    st.markdown(f"""
    <div class='cyber-card' style='height: 100%; min-height: 100px; display: flex; flex-direction: column; justify-content: center;'>
        <div style='color: #94a3b8; font-family: "JetBrains Mono", monospace; font-size: clamp(0.75rem, 1.5vw, 0.9rem); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;'>
            {label}
        </div>
        <div style='font-size: clamp(1.4rem, 4vw, 2rem); font-weight: 700; color: {val_color}; font-family: "Inter", sans-serif; display: flex; align-items: baseline; flex-wrap: wrap;'>
            {value}{delta_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def neon_header(text, level=1):
    font_size = "clamp(1.8rem, 5vw, 2.5rem)" if level == 1 else ("clamp(1.4rem, 4vw, 1.8rem)" if level == 2 else "clamp(1.1rem, 3vw, 1.4rem)")
    st.markdown(f'<h{level} style="font-family: \'Inter\', sans-serif; font-weight: 800; background: linear-gradient(90deg, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: {font_size}; margin-top: 20px; margin-bottom: 15px; text-shadow: 0 0 30px rgba(0, 242, 255, 0.2); word-wrap: break-word;">{text}</h{level}>', unsafe_allow_html=True)

def cyberpunk_logo(logo_path=None, size="180px", font_size="24px"):
    # Always render the code-based logo for consistent CapacityBay branding
    # Recreating the circular logo with Green Text on White Background - Responsive
    
    size_css = f"clamp(120px, 30vw, {size})"
    font_css = f"clamp(16px, 4vw, {font_size})"
    
    logo_html = f'''<div style="display: inline-flex; width: {size_css}; height: {size_css}; background: white; border: 5px solid #00994d; border-radius: 50%; margin-bottom: 20px; box-shadow: 0 0 30px rgba(0, 242, 255, 0.2); flex-direction: column; align-items: center; justify-content: center; font-family: 'Inter', sans-serif; overflow: hidden;"><div style="color: #00994d; font-size: {font_css}; font-weight: 800; letter-spacing: -1px; margin-bottom: 5px;">Capa-X</div><div style="color: #333; font-size: clamp(8px, 2vw, 10px); font-weight: 600; text-transform: capitalize; text-align: center; width: 90%;">Communicate | Collaborate | Create</div></div>'''
    
    st.markdown(f'<div style="display: flex; justify-content: center; width: 100%; margin-bottom: 30px; position: relative; z-index: 10;">{logo_html}</div>', unsafe_allow_html=True)
