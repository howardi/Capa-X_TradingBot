
try:
    import dash
    print("dash imported successfully")
except ImportError as e:
    print(f"dash import failed: {e}")
except Exception as e:
    print(f"dash import error: {e}")

try:
    import websockets
    print("websockets imported successfully")
except ImportError as e:
    print(f"websockets import failed: {e}")
except Exception as e:
    print(f"websockets import error: {e}")
