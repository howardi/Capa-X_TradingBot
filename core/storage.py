import sqlite3
import json
import os
from datetime import datetime
import pandas as pd
from core.persistence import CloudPersistence

class StorageManager:
    def __init__(self, db_path="trading_bot.db"):
        self.db_path = db_path
        
        # Initialize Cloud Persistence
        self.cloud_storage = CloudPersistence()
        
        # Firestore Setup
        self.db_firestore = None
        try:
            from google.cloud import firestore
            if os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("K_SERVICE"):
                self.db_firestore = firestore.Client()
        except:
            pass

        # Try to download latest DB from cloud BEFORE connecting
        self.cloud_storage.download_file("trading_bot.db", self.db_path)
        
        self.conn = None
        self.cursor = None
        self.initialize_db()

    def initialize_db(self):
        """Initialize SQLite Database and Tables"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # 1. Trade History Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange TEXT,
                    symbol TEXT,
                    side TEXT,
                    amount REAL,
                    price REAL,
                    cost REAL,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    strategy TEXT,
                    pnl REAL DEFAULT 0.0
                )
            ''')
            
            # 2. Settings Table (Key-Value)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 3. Balance History
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS balance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_balance_usd REAL,
                    available_balance_usd REAL
                )
            ''')

            # 4. Fiat Transactions (Idempotency)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS fiat_transactions (
                    reference TEXT PRIMARY KEY,
                    type TEXT,
                    amount REAL,
                    currency TEXT,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            
            self.conn.commit()
            print(f"[Storage] Database initialized at {self.db_path}")

            # Attempt to seed from JSON if settings are empty
            self.seed_from_json()
            
            # Sync from Firestore (Source of Truth)
            self._sync_from_firestore()
            
        except Exception as e:
            print(f"[Storage] Init Error: {e}")

    def _sync_from_firestore(self):
        """Load settings and fiat txs from Firestore to local SQLite"""
        if not self.db_firestore:
            return

        print("[Storage] Syncing from Firestore...")
        try:
            # 1. Settings
            docs = self.db_firestore.collection('settings').stream()
            count = 0
            for doc in docs:
                data = doc.to_dict()
                key = doc.id
                value = data.get('value')
                
                self.cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, str(value)))
                count += 1
            
            if count > 0:
                print(f"[Storage] Synced {count} settings from Firestore.")
            
            # 2. Fiat Transactions
            docs = self.db_firestore.collection('fiat_transactions').stream()
            count = 0
            for doc in docs:
                data = doc.to_dict()
                # Ensure fields exist
                self.save_fiat_transaction(
                    data.get('reference'),
                    data.get('type'),
                    data.get('amount'),
                    data.get('currency'),
                    data.get('status'),
                    data.get('details')
                )
                count += 1
                
            self.conn.commit()
            
        except Exception as e:
            print(f"[Storage] Firestore Sync Error: {e}")

    def seed_from_json(self):
        """Seed DB from data/cloud_seed.json if available and DB is empty"""
        try:
            # Check if we already have data
            self.cursor.execute("SELECT count(*) FROM settings")
            if self.cursor.fetchone()[0] > 0:
                return # Already initialized
                
            seed_path = os.path.join("data", "cloud_seed.json")
            if not os.path.exists(seed_path):
                # Fallback to root data folder if running from different cwd
                seed_path = os.path.join(os.getcwd(), "data", "cloud_seed.json")
                if not os.path.exists(seed_path):
                    return

            print(f"[Storage] Seeding database from {seed_path}...")
            with open(seed_path, 'r') as f:
                data = json.load(f)
                
            # Seed Settings
            for k, v in data.get("settings", {}).items():
                self.save_setting(k, v)
                
            # Seed Transactions
            for tx in data.get("fiat_transactions", []):
                self.save_fiat_transaction(
                    tx.get('reference'),
                    tx.get('type'),
                    tx.get('amount'),
                    tx.get('currency'),
                    tx.get('status'),
                    tx.get('details')
                )
                
            print("[Storage] Seeding complete.")
            
        except Exception as e:
            print(f"[Storage] Seeding Failed: {e}")

    def save_trade(self, trade_data):
        """Save a trade execution to DB"""
        try:
            self.cursor.execute('''
                INSERT INTO trades (exchange, symbol, side, amount, price, cost, status, strategy, pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('exchange', 'Unknown'),
                trade_data.get('symbol', 'Unknown'),
                trade_data.get('side', 'Unknown'),
                trade_data.get('amount', 0.0),
                trade_data.get('price', 0.0),
                trade_data.get('cost', 0.0),
                trade_data.get('status', 'Executed'),
                trade_data.get('strategy', 'Manual'),
                trade_data.get('pnl', 0.0)
            ))
            self.conn.commit()
            
            # Sync to cloud after significant changes (Using a lightweight check could be better)
            # For simplicity, we won't sync on EVERY insert as it's slow.
            # Ideally, call sync_db_up() periodically or on shutdown.
            # But for critical things like balance/settings, we might want to sync.
            pass 
        except Exception as e:
            print(f"[Storage] Save Trade Error: {e}")

    def sync_to_cloud(self):
        """Manually trigger cloud sync"""
        if self.cloud_storage:
            self.cloud_storage.upload_file(self.db_path, "trading_bot.db")
            
    def get_trades(self, limit=50):
        """Fetch recent trades"""
        try:
            query = f"SELECT * FROM trades ORDER BY timestamp DESC LIMIT {limit}"
            return pd.read_sql_query(query, self.conn)
        except Exception as e:
            print(f"[Storage] Get Trades Error: {e}")
            return pd.DataFrame()

    def save_setting(self, key, value):
        """Save a setting (e.g. API Key encrypted, or config)"""
        try:
            # If value is dict/list, json dump it
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(value)))
            self.conn.commit()
            self.sync_to_cloud() # Sync settings immediately
        except Exception as e:
            print(f"[Storage] Save Setting Error: {e}")

    def get_setting(self, key, default=None):
        """Get a setting by key"""
        try:
            self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = self.cursor.fetchone()
            if result:
                val = result[0]
                # Try to load as JSON
                try:
                    return json.loads(val)
                except:
                    return val
            return default
        except Exception as e:
            print(f"[Storage] Get Setting Error: {e}")
            return default

    def save_fiat_transaction(self, reference, tx_type, amount, currency, status, details=None):
        """Save/Update a fiat transaction"""
        try:
            if isinstance(details, (dict, list)):
                details = json.dumps(details)
            
            # 1. SQLite Save
            self.cursor.execute('''
                INSERT OR REPLACE INTO fiat_transactions (reference, type, amount, currency, status, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (reference, tx_type, amount, currency, status, details))
            self.conn.commit()

            # 2. Firestore Save
            if self.db_firestore:
                try:
                    self.db_firestore.collection('fiat_transactions').document(str(reference)).set({
                        'reference': reference,
                        'type': tx_type,
                        'amount': amount,
                        'currency': currency,
                        'status': status,
                        'details': details,
                        'timestamp': firestore.SERVER_TIMESTAMP
                    })
                except Exception as e:
                    print(f"[Storage] Firestore Fiat Tx Save Error: {e}")

            self.sync_to_cloud() # Sync fiat transactions immediately
        except Exception as e:
            print(f"[Storage] Save Fiat Tx Error: {e}")

    def get_fiat_transaction(self, reference):
        """Get fiat transaction by reference"""
        try:
            self.cursor.execute('SELECT * FROM fiat_transactions WHERE reference = ?', (reference,))
            result = self.cursor.fetchone()
            if result:
                # Convert row to dict
                cols = [description[0] for description in self.cursor.description]
                return dict(zip(cols, result))
            return None
        except Exception as e:
            print(f"[Storage] Get Fiat Tx Error: {e}")
            return None

    def get_recent_fiat_transactions(self, limit=20):
        """Get recent fiat transactions"""
        try:
            self.cursor.execute(f'SELECT * FROM fiat_transactions ORDER BY timestamp DESC LIMIT {limit}')
            results = self.cursor.fetchall()
            if results:
                cols = [description[0] for description in self.cursor.description]
                return [dict(zip(cols, row)) for row in results]
            return []
        except Exception as e:
            print(f"[Storage] Get Recent Fiat Tx Error: {e}")
            return []

    def log_balance(self, total, available):
        """Log balance snapshot"""
        try:
            self.cursor.execute('''
                INSERT INTO balance_history (total_balance_usd, available_balance_usd)
                VALUES (?, ?)
            ''', (total, available))
            self.conn.commit()
        except Exception as e:
            print(f"[Storage] Log Balance Error: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
