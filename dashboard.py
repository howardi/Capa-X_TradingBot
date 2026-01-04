import streamlit as st
import traceback
import os
import sys
import importlib

# Force reload of core modules to ensure updates are picked up
# This fixes issues where exec() uses cached modules with missing attributes
try:
    import core.styles
    importlib.reload(core.styles)
except ImportError:
    pass

# Import settings for page title
try:
    from config.settings import APP_NAME
except ImportError:
    APP_NAME = "Capa-X"

# Set page config moved to dashboard_impl.py for better control
# st.set_page_config(page_title=APP_NAME, layout="wide")

def main():
    try:
        # Run the actual dashboard implementation
        # We use exec to run it in the current global context so it behaves like a script
        with open("dashboard_impl.py", encoding='utf-8') as f:
            code = f.read()
        
        exec(code, globals())
        
    except Exception as e:
        st.error("⚠️ An Internal Server Error Occurred")
        st.markdown(
            """
            The application encountered a critical error. 
            Please share the details below with the developer to fix it.
            """
        )
        with st.expander("View Error Details", expanded=True):
            st.code(traceback.format_exc(), language="python")
        
        # Add a retry button
        if st.button("Retry / Reload"):
            st.rerun()

if __name__ == "__main__":
    main()
