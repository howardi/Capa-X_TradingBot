
try:
    from core.styles import metric_card
    print("Successfully imported metric_card")
except ImportError as e:
    print(f"Import failed: {e}")
    import core.styles
    print(f"core.styles dir: {dir(core.styles)}")
