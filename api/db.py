import sqlite3
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'users.db'))
DATABASE_URL = os.getenv('DATABASE_URL')
if os.getenv('FORCE_SQLITE'):
    DATABASE_URL = None

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        # 1. Handle Placeholders: ? -> %s
        query = query.replace('?', '%s')
        
        # 2. Handle SQLite specific syntax
        if 'INSERT OR IGNORE' in query:
            # Postgres: INSERT INTO ... ON CONFLICT DO NOTHING
            query = query.replace('INSERT OR IGNORE', 'INSERT')
            if 'ON CONFLICT' not in query:
                query += ' ON CONFLICT DO NOTHING'
        
        try:
            if params:
                return self.cursor.execute(query, params)
            return self.cursor.execute(query)
        except Exception as e:
            # Log or re-raise
            print(f"Database Error: {e}")
            raise e

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()
    
    @property
    def rowcount(self):
        return self.cursor.rowcount

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn
        self.row_factory = None # Not used but for compatibility
        
    def cursor(self):
        import psycopg2.extras
        return PostgresCursorWrapper(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

def get_db_connection():
    if DATABASE_URL:
        import psycopg2
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            print(f"Failed to connect to Postgres: {e}")
            # Fallback to SQLite if Postgres fails (e.g. local dev without net)
            # But maybe user wants to know it failed.
            raise e
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    is_postgres = DATABASE_URL is not None
    
    # Define Types
    SERIAL_PK = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    # 1. Users
    c.execute(f'''CREATE TABLE IF NOT EXISTS users
                 (id {SERIAL_PK}, username TEXT UNIQUE, password TEXT, 
                  email TEXT UNIQUE, full_name TEXT, phone_number TEXT,
                  google_id TEXT, github_id TEXT,
                  reset_token TEXT, reset_token_expiry TIMESTAMP,
                  is_admin INTEGER DEFAULT 0)''')
    
    # Migrations for Users
    try:
        c.execute("SELECT email FROM users LIMIT 1")
    except Exception:
        if is_postgres: conn.rollback()
        try:
            c.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
            c.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            c.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
            c.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
            c.execute("ALTER TABLE users ADD COLUMN github_id TEXT")
            c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
            c.execute("ALTER TABLE users ADD COLUMN reset_token_expiry TIMESTAMP")
            c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            conn.commit()
        except:
            if is_postgres: conn.rollback()

    # Migration for new fields if email exists but full_name doesn't
    try:
        c.execute("SELECT full_name FROM users LIMIT 1")
    except Exception:
        if is_postgres: conn.rollback()
        try:
            c.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            c.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
            conn.commit()
        except:
             if is_postgres: conn.rollback()
    
    # 2. Wallets
    c.execute(f'''CREATE TABLE IF NOT EXISTS wallets
                 (id {SERIAL_PK}, username TEXT, address TEXT, private_key TEXT, type TEXT, name TEXT DEFAULT 'Main Wallet', balance REAL DEFAULT 0.0)''')
    conn.commit()
    
    # Migration: name
    try:
        c.execute("SELECT name FROM wallets LIMIT 1")
    except Exception:
        if is_postgres: conn.rollback()
        try:
            c.execute("ALTER TABLE wallets ADD COLUMN name TEXT DEFAULT 'Main Wallet'")
            conn.commit()
        except: 
            if is_postgres: conn.rollback()
    
    # 3. Exchanges
    c.execute(f'''CREATE TABLE IF NOT EXISTS exchanges
                 (id {SERIAL_PK}, username TEXT, exchange_id TEXT, api_key TEXT, secret TEXT, 
                 UNIQUE(username, exchange_id))''')
    conn.commit()
    
    # 4. Bot Settings
    c.execute('''CREATE TABLE IF NOT EXISTS bot_settings
                 (username TEXT PRIMARY KEY, enabled INTEGER DEFAULT 0, symbol TEXT DEFAULT 'BTC/USDT', 
                  timeframe TEXT DEFAULT '1h', risk_level TEXT DEFAULT 'medium', strategy TEXT DEFAULT 'technical',
                  investment_amount REAL DEFAULT 0.0, mode TEXT DEFAULT 'demo')''')
    conn.commit()
                  
    # Migrations for Bot Settings
    for col, dtype, default in [
        ('mode', 'TEXT', "'demo'"),
        ('stop_loss', 'REAL', '2.0'),
        ('take_profit', 'REAL', '4.0'),
        ('is_active', 'INTEGER', '0')
    ]:
        try:
            c.execute(f"SELECT {col} FROM bot_settings LIMIT 1")
        except Exception:
            if is_postgres: conn.rollback()
            try:
                c.execute(f"ALTER TABLE bot_settings ADD COLUMN {col} {dtype} DEFAULT {default}")
                conn.commit()
            except: 
                if is_postgres: conn.rollback()

    # 5. Bot Activity
    c.execute(f'''CREATE TABLE IF NOT EXISTS bot_activity
                 (id {SERIAL_PK}, username TEXT, type TEXT, symbol TEXT, 
                  price REAL, amount REAL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                  pnl REAL DEFAULT 0.0, status TEXT DEFAULT 'open', strategy TEXT,
                  stop_loss REAL, take_profit REAL, initial_entry REAL, mode TEXT DEFAULT 'live',
                  client_order_id TEXT UNIQUE)''')
    conn.commit()
    
    # Migration for Bot Activity
    try:
        c.execute("SELECT mode FROM bot_activity LIMIT 1")
    except Exception:
        if is_postgres: conn.rollback()
        try:
            c.execute("ALTER TABLE bot_activity ADD COLUMN mode TEXT DEFAULT 'live'")
            conn.commit()
        except: 
            if is_postgres: conn.rollback()

    try:
        c.execute("SELECT client_order_id FROM bot_activity LIMIT 1")
    except Exception:
        if is_postgres: conn.rollback()
        try:
            c.execute("ALTER TABLE bot_activity ADD COLUMN client_order_id TEXT UNIQUE")
            conn.commit()
        except:
            if is_postgres: conn.rollback()

    # 6. Demo Balances
    c.execute('''CREATE TABLE IF NOT EXISTS demo_balances
                 (username TEXT, currency TEXT, balance REAL, 
                  PRIMARY KEY (username, currency))''')

    # 7. Live Balances
    c.execute('''CREATE TABLE IF NOT EXISTS live_balances
                 (username TEXT, currency TEXT, balance REAL, 
                  PRIMARY KEY (username, currency))''')
                  
    # 8. Transactions
    c.execute(f'''CREATE TABLE IF NOT EXISTS transactions
                 (id {SERIAL_PK}, username TEXT, type TEXT, 
                  currency TEXT, amount REAL, status TEXT, tx_ref TEXT, 
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 9. Copy Trading
    c.execute(f'''CREATE TABLE IF NOT EXISTS copy_trade_following
                 (id {SERIAL_PK}, username TEXT, trader_id INTEGER, 
                  trader_name TEXT, status TEXT DEFAULT 'active', 
                  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(username, trader_id))''')

    # 10. Risk Daily Stats
    c.execute(f'''CREATE TABLE IF NOT EXISTS risk_daily_stats
                 (id {SERIAL_PK}, username TEXT, date TEXT, 
                  starting_balance REAL, current_balance REAL, 
                  daily_pnl REAL DEFAULT 0.0, max_drawdown REAL DEFAULT 0.0,
                  trade_count INTEGER DEFAULT 0, loss_count INTEGER DEFAULT 0,
                  is_locked INTEGER DEFAULT 0,
                  UNIQUE(username, date))''')

    # 11. System Health/Events
    c.execute(f'''CREATE TABLE IF NOT EXISTS system_events
                 (id {SERIAL_PK}, type TEXT, level TEXT, message TEXT, 
                  metadata TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()
