
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class FeatureStore:
    """
    Centralized Feature Store for managing feature engineering, 
    versioning, and serving for both training and inference.
    Ensures training-serving skew is minimized.
    """
    def __init__(self, store_path="data/feature_store"):
        self.store_path = store_path
        self.feature_registry = {
            "v1": ["rsi", "ema_50", "ema_200", "atr", "adx"],
            "v2": ["rsi", "ema_50", "ema_200", "atr", "adx", "macd", "bollinger_width"]
        }
        self.active_version = "v2"
        
        if not os.path.exists(self.store_path):
            os.makedirs(self.store_path)
            
    def get_active_features(self) -> List[str]:
        return self.feature_registry.get(self.active_version, [])

    def compute_features(self, df: pd.DataFrame, version: str = None) -> pd.DataFrame:
        """
        Compute features based on the specified version.
        Uses the shared logic to ensure consistency.
        """
        if df.empty:
            return df
            
        target_version = version if version else self.active_version
        
        # Base copy
        df_features = df.copy()
        
        # --- Feature Engineering Logic (Centralized) ---
        # Note: In a real system, this might delegate to core.analysis or use a library like tsfresh
        # Here we ensure specific calculations are standardized.
        
        # RSI
        delta = df_features['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_features['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df_features['ema_50'] = df_features['close'].ewm(span=50, adjust=False).mean()
        df_features['ema_200'] = df_features['close'].ewm(span=200, adjust=False).mean()
        
        # ATR
        high_low = df_features['high'] - df_features['low']
        high_close = np.abs(df_features['high'] - df_features['close'].shift())
        low_close = np.abs(df_features['low'] - df_features['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df_features['atr'] = pd.Series(true_range).rolling(14).mean()
        
        # ADX (Simplified)
        df_features['adx'] = 25.0 # Placeholder for complex calc to save space
        
        if target_version == "v2":
            # MACD
            exp1 = df_features['close'].ewm(span=12, adjust=False).mean()
            exp2 = df_features['close'].ewm(span=26, adjust=False).mean()
            df_features['macd'] = exp1 - exp2
            
            # Bollinger Width
            sma = df_features['close'].rolling(window=20).mean()
            std = df_features['close'].rolling(window=20).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            df_features['bollinger_width'] = (upper - lower) / sma
            
            # Additional Features for AI (Input Dim = 10)
            df_features['returns'] = df_features['close'].pct_change()
            df_features['log_volume'] = np.log1p(df_features['volume'])
            df_features['high_low_pct'] = (df_features['high'] - df_features['low']) / df_features['close']

        # Market Regime Detection
        # 0: Ranging, 1: Trending, 2: Volatile
        df_features['regime_adx'] = df_features['adx'] > 25
        df_features['regime_vol'] = df_features['bollinger_width'] > df_features['bollinger_width'].rolling(50).quantile(0.8)
        
        conditions = [
            (df_features['regime_vol']), # High Volatility
            (df_features['regime_adx']), # Trending
        ]
        choices = ['Volatile', 'Trending']
        df_features['market_regime'] = np.select(conditions, choices, default='Ranging')
            
        # Fill NaNs created by rolling windows
        df_features = df_features.bfill()
        df_features = df_features.fillna(0)
        
        return df_features

    def save_features(self, df: pd.DataFrame, symbol: str, timestamp: datetime):
        """
        Save calculated features to the offline store (e.g., Parquet/CSV) for training.
        """
        filename = f"{symbol.replace('/', '_')}_{timestamp.strftime('%Y%m%d')}.parquet"
        path = os.path.join(self.store_path, filename)
        
        # Filter only registered features + targets
        cols = self.get_active_features() + ['close', 'timestamp'] # Keep identifiers
        existing_cols = [c for c in cols if c in df.columns]
        
        df[existing_cols].to_parquet(path)
        
    def load_training_dataset(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Retrieve historical features for model training.
        """
        # Placeholder: In a real system, this would query the Parquet files or a DB
        # For now, we return an empty DF or mock
        return pd.DataFrame()

    def check_feature_freshness(self, df: pd.DataFrame) -> dict:
        """
        Monitor feature freshness (latency).
        """
        if df.empty or 'timestamp' not in df.columns:
            return {'status': 'unknown', 'latency_ms': 0}
            
        last_ts = pd.to_datetime(df['timestamp'].iloc[-1])
        now = pd.Timestamp.now()
        latency = (now - last_ts).total_seconds() * 1000
        
        status = 'fresh' if latency < 60000 else 'stale' # 1 min threshold
        return {'status': status, 'latency_ms': latency}
