
import sys
import os

print(f"Current working directory: {os.getcwd()}")
print(f"Sys path: {sys.path}")

try:
    import core.styles as styles
    print(f"Successfully imported core.styles from {styles.__file__}")
    print(f"Dir(styles): {dir(styles)}")
    
    components = ['metric_card', 'neon_header', 'card_container', 'cyberpunk_logo', 'apply_custom_styles']
    for comp in components:
        if hasattr(styles, comp):
            print(f"✅ {comp} found")
        else:
            print(f"❌ {comp} MISSING")
            
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Error: {e}")
