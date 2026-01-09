import os
import sys
import json

# Add root to path
sys.path.append(os.getcwd())

try:
    from google.cloud import firestore
except ImportError:
    print("google-cloud-firestore not installed. Please run: pip install google-cloud-firestore")
    sys.exit(1)

def sync_users():
    print("Syncing users to Firestore...")
    
    # Initialize Firestore
    # Try to detect project ID
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "caparox-bot")
    
    try:
        db = firestore.Client(project=project_id)
    except Exception as e:
        print(f"Failed to connect to Firestore: {e}")
        print("Please run: gcloud auth application-default login")
        return

    # Load local users
    users_path = os.path.join("data", "users", "users_db.json")
    if not os.path.exists(users_path):
        print(f"No local users found at {users_path}")
        return

    with open(users_path, 'r') as f:
        users = json.load(f)

    print(f"Found {len(users)} users locally.")

    for username, data in users.items():
        print(f"Syncing {username}...")
        try:
            # Clean up data if needed (e.g. convert datetimes)
            # Firestore handles strings fine.
            db.collection('users').document(username).set(data)
            print(f"  Synced {username}")
        except Exception as e:
            print(f"  Failed to sync {username}: {e}")

    print("Sync complete.")

if __name__ == "__main__":
    # Set env var if not set
    if "GOOGLE_CLOUD_PROJECT" not in os.environ:
        os.environ["GOOGLE_CLOUD_PROJECT"] = "caparox-bot"
        
    sync_users()
