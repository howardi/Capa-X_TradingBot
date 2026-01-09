import os
import json
import logging
try:
    from google.cloud import storage
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    storage = None

from tenacity import retry, stop_after_attempt, wait_fixed

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloudPersistence")

class CloudPersistence:
    """
    Handles syncing of local data files to Google Cloud Storage.
    Designed for Cloud Run stateless environments.
    """
    
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or os.environ.get("GCS_BUCKET_NAME")
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        
        # If no bucket configured or lib missing, persistence is disabled
        self.enabled = bool(self.bucket_name and self.project_id and GOOGLE_CLOUD_AVAILABLE)
        
        if self.enabled:
            try:
                self.client = storage.Client(project=self.project_id)
                self.bucket = self.client.bucket(self.bucket_name)
                logger.info(f"✅ Cloud Persistence Enabled. Bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Cloud Storage: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️ Cloud Persistence Disabled (GCS_BUCKET_NAME not set)")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def upload_file(self, local_path, remote_path):
        """Upload a file to GCS"""
        if not self.enabled:
            return
            
        if not os.path.exists(local_path):
            logger.warning(f"Skipping upload: Local file not found {local_path}")
            return

        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(local_path)
            logger.info(f"⬆️ Uploaded {local_path} -> gs://{self.bucket_name}/{remote_path}")
        except Exception as e:
            logger.error(f"Upload Failed {local_path}: {e}")
            raise e

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def download_file(self, remote_path, local_path):
        """Download a file from GCS"""
        if not self.enabled:
            return False

        try:
            blob = self.bucket.blob(remote_path)
            if not blob.exists():
                logger.info(f"Remote file {remote_path} does not exist. Skipping download.")
                return False
                
            # Ensure local dir exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob.download_to_filename(local_path)
            logger.info(f"⬇️ Downloaded gs://{self.bucket_name}/{remote_path} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"Download Failed {remote_path}: {e}")
            return False

    def sync_db_down(self):
        """Download all critical DB files on startup"""
        if not self.enabled:
            return
            
        # 1. User DB
        self.download_file("users_db.json", "data/users/users_db.json")
        
        # 2. Trading DB (SQLite)
        self.download_file("trading_bot.db", "trading_bot.db")
        
    def sync_db_up(self):
        """Upload all critical DB files (Call periodically or on change)"""
        if not self.enabled:
            return
            
        # 1. User DB
        self.upload_file("data/users/users_db.json", "users_db.json")
        
        # 2. Trading DB
        self.upload_file("trading_bot.db", "trading_bot.db")
