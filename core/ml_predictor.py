import pandas as pd
import numpy as np
import joblib
import os
from typing import Dict, Any

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import precision_score, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class EnsemblePredictor:
    def __init__(self, model_path="models/rf_model.joblib"):
        self.model_path = model_path
        self.model = None
        self.is_trained = False
        self.feature_columns = []
        
        if SKLEARN_AVAILABLE:
            self.model = RandomForestClassifier(
                n_estimators=100, 
                max_depth=10, 
                n_jobs=-1, 
                random_state=42
            )
            self.load_model()
    
    def load_model(self):
        if os.path.exists(self.model_path) and SKLEARN_AVAILABLE:
            try:
                data = joblib.load(self.model_path)
                # Handle both direct model load and dict load (if we saved metadata)
                if isinstance(data, dict) and 'model' in data:
                    self.model = data['model']
                    self.feature_columns = data.get('features', [])
                else:
                    self.model = data
                    # Try to recover features if possible, else might fail on predict
                    if hasattr(self.model, 'feature_names_in_'):
                        self.feature_columns = list(self.model.feature_names_in_)
                        
                self.is_trained = True
                print(f"Loaded AI Model from {self.model_path}")
            except Exception as e:
                print(f"Failed to load model: {e}")

    def save_model(self):
        if self.model and SKLEARN_AVAILABLE:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            save_data = {
                'model': self.model,
                'features': self.feature_columns
            }
            joblib.dump(save_data, self.model_path)
            print(f"Saved AI Model to {self.model_path}")

    def train(self, df: pd.DataFrame, target_col: str = 'target_success'):
        """
        Train the model on historical data.
        target_col should be boolean (1 for profitable trade, 0 for loss)
        """
        if not SKLEARN_AVAILABLE:
            print("Scikit-learn not installed. AI training skipped.")
            return {'status': 'error', 'message': 'Missing dependencies'}
            
        if df.empty or target_col not in df.columns:
            return {'status': 'error', 'message': 'Invalid training data'}
            
        # Feature Selection
        # Exclude non-numeric and target
        exclude_cols = ['timestamp', 'symbol', target_col, 'close', 'high', 'low', 'open', 'volume', 'market_regime']
        feature_cols = [c for c in df.columns if c not in exclude_cols and np.issubdtype(df[c].dtype, np.number)]
        
        X = df[feature_cols].fillna(0)
        y = df[target_col]
        
        if len(X) < 50:
             return {'status': 'error', 'message': 'Insufficient data points'}

        # Update feature columns
        self.feature_columns = feature_cols
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        # Train
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        preds = self.model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        
        self.save_model()
        
        return {
            'status': 'success',
            'accuracy': acc,
            'precision': prec,
            'feature_importance': dict(zip(feature_cols, self.model.feature_importances_))
        }

    def predict_confidence(self, current_features: Dict[str, float]) -> float:
        """
        Predict probability of trade success given current market features.
        """
        if not self.is_trained or not SKLEARN_AVAILABLE or not self.feature_columns:
            return 0.5 # Neutral confidence
            
        try:
            # Construct feature vector in correct order
            vector = []
            for col in self.feature_columns:
                vector.append(current_features.get(col, 0.0))
                
            X = np.array([vector])
            
            # Predict Probability
            # Classes are [0, 1], we want prob of 1
            probs = self.model.predict_proba(X)
            if probs.shape[1] == 2:
                return float(probs[0][1])
            else:
                # If only one class seen during training (e.g. all wins), handle edge case
                return float(self.model.classes_[0])
                
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0.5
