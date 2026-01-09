import os
import sys
import sqlite3
import json

# Add root to path
sys.path.append(os.getcwd())

try:
    from google.cloud import firestore
except ImportError:
    print("google-cloud-firestore not installed. Please run: pip install google-cloud-firestore")
    sys.exit(1)

def sync_settings():
    print("Syncing settings and transactions to Firestore...")
    
    # Initialize Firestore
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "caparox-bot")
    try:
        db = firestore.Client(project=project_id)
    except Exception as e:
        print(f"Failed to connect to Firestore: {e}")
        print("Please run: gcloud auth application-default login")
        return

    # Database Path
    db_path = "trading_bot.db"
    if not os.path.exists(db_path):
        print(f"No local database found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Sync Settings
    print("\n--- Syncing Settings ---")
    try:
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} settings.")
        
        for key, value in rows:
            print(f"  Syncing setting: {key}...")
            # Value is stored as string in SQLite, we can try to parse JSON if applicable
            # but Firestore handles strings fine. Let's keep it simple.
            db.collection('settings').document(key).set({
                'value': value,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
    except Exception as e:
        print(f"Error syncing settings: {e}")

    # 2. Sync Fiat Transactions
    print("\n--- Syncing Fiat Transactions ---")
    try:
        cursor.execute("SELECT reference, type, amount, currency, status, details FROM fiat_transactions")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} transactions.")
        
        for row in rows:
            ref, type_, amount, currency, status, details = row
            print(f"  Syncing tx: {ref}...")
            db.collection('fiat_transactions').document(ref).set({
                'reference': ref,
                'type': type_,
                'amount': amount,
                'currency': currency,
                'status': status,
                'details': details,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
    except Exception as e:
        # Table might not exist if no transactions yet
        print(f"Error syncing transactions (table might not exist): {e}")

    conn.close()
    print("\nSync complete.")

if __name__ == "__main__":
    if "GOOGLE_CLOUD_PROJECT" not in os.environ:
        os.environ["GOOGLE_CLOUD_PROJECT"] = "caparox-bot"
    
    sync_settings()
