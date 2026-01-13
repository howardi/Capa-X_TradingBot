import os
# Force SQLite for local verification BEFORE any other imports
os.environ['FORCE_SQLITE'] = '1'

import threading
import time
import sys
import asyncio
import requests

# Import App
from api.index import app
from test_auth import test_auth
from test_deployment_async import test_deployment_async

def run_server():
    app.run(port=5000, debug=False, use_reloader=False)

def run_verification():
    # Run Bot Logic Tests First (It initializes DB)
    print("\n=== RUNNING BOT LOGIC TESTS ===")
    try:
        asyncio.run(test_deployment_async())
    except Exception as e:
        print(f"Bot Logic Test Exception: {e}")
        sys.exit(1)

    # Start Server in Thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("Waiting for server to start...")
    time.sleep(3) # Give it time
    
    # Run Auth Tests
    print("\n=== RUNNING AUTH TESTS ===")
    try:
        if not test_auth():
            print("Auth Tests Failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Auth Test Exception: {e}")
        sys.exit(1)
        
    print("\nALL VERIFICATIONS PASSED!")
    sys.exit(0)

if __name__ == "__main__":
    run_verification()
