
import numpy as np
import pandas as pd
import logging

# Re-enable imports as this module is now lazy-loaded
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("Warning: PyTorch not found. Deep Learning modules disabled.")

try:
    from stable_baselines3 import PPO
    from gymnasium import Env, spaces
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    print("Warning: Stable-Baselines3/Gymnasium not found. RL modules disabled.")

SCIPY_AVAILABLE = False
try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    # Check for Scipy as fallback
    try:
        from scipy.optimize import minimize
        SCIPY_AVAILABLE = True
        print("Warning: PyPortfolioOpt not found. Using Scipy for optimization.")
    except ImportError:
        SCIPY_AVAILABLE = False
        print("Warning: PyPortfolioOpt and Scipy not found. Portfolio optimization disabled.")

class DriftDetector:
    """
    Monitors data distributions to detect Concept Drift or Data Drift.
    Triggers alerts if retraining is needed.
    """
    def __init__(self, reference_stats: dict = None):
        # reference_stats: {'feature_name': {'mean': x, 'std': y}, ...}
        self.reference_stats = reference_stats or {}
        self.drift_status = {}

    def update_reference(self, df: pd.DataFrame):
        """
        Update reference statistics from a 'golden' training dataset.
        """
        stats = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                stats[col] = {
                    'mean': df[col].mean(),
                    'std': df[col].std()
                }
        self.reference_stats = stats

    def check_drift(self, df: pd.DataFrame) -> dict:
        """
        Compare current batch stats with reference.
        Simple Z-Score / Std-Dev overlap check.
        """
        if not self.reference_stats or df.empty:
            return {'status': 'unknown', 'drift_score': 0.0}

        drift_scores = []
        drift_details = {}

        for col, ref in self.reference_stats.items():
            if col in df.columns:
                curr_mean = df[col].mean()
                curr_std = df[col].std()
                
                # Check if current mean is > 3 std devs away from ref mean (simplified)
                # Avoid division by zero
                ref_std = ref['std'] if ref['std'] > 1e-6 else 1.0
                z_score = abs(curr_mean - ref['mean']) / ref_std
                
                drift_scores.append(z_score)
                drift_details[col] = z_score

        avg_drift = np.mean(drift_scores) if drift_scores else 0.0
        
        status = 'stable'
        if avg_drift > 3.0:
            status = 'severe_drift'
        elif avg_drift > 1.5:
            status = 'moderate_drift'
            
        self.drift_status = {'status': status, 'score': avg_drift, 'details': drift_details}
        return self.drift_status

class LSTMModel(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self, input_dim, hidden_dim, output_dim, num_layers):
        if not TORCH_AVAILABLE: return
        super(LSTMModel, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        if not TORCH_AVAILABLE: return None
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

class TransformerModel(nn.Module if TORCH_AVAILABLE else object):
    """
    Simple Transformer Encoder for Time Series
    """
    def __init__(self, input_dim, d_model, nhead, num_layers, output_dim):
        if not TORCH_AVAILABLE: return
        super(TransformerModel, self).__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, output_dim)

    def forward(self, x):
        if not TORCH_AVAILABLE: return None
        x = self.embedding(x)
        x = x.permute(1, 0, 2) # Transformer expects (seq_len, batch, feature)
        out = self.transformer_encoder(x)
        out = out.permute(1, 0, 2)
        out = self.fc(out[:, -1, :]) # Take last time step
        return out

class AIEngine:
    """
    Orchestrates AI/ML models: LSTM, Transformer, and RL.
    """
    def __init__(self):
        self.models = {}
        self.device = None
        
        if TORCH_AVAILABLE:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            # Initialize placeholder models (in production, load weights)
            self.lstm = LSTMModel(input_dim=10, hidden_dim=64, output_dim=1, num_layers=2).to(self.device)
            self.transformer = TransformerModel(input_dim=10, d_model=64, nhead=4, num_layers=2, output_dim=1).to(self.device)
            self.lstm.eval()
            self.transformer.eval()
        
        self.rl_agent = None
        if RL_AVAILABLE:
            # Placeholder for loading a trained PPO agent
            # self.rl_agent = PPO.load("path_to_agent")
            pass

    def predict_next_price_lstm(self, features: np.ndarray) -> float:
        """
        Predict next price using LSTM.
        Features shape: (seq_len, input_dim)
        """
        if not TORCH_AVAILABLE: return 0.0
        
        with torch.no_grad():
            x = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device) # Add batch dim
            prediction = self.lstm(x)
            return prediction.item()

    def predict_sentiment_transformer(self, features: np.ndarray) -> float:
        """
        Predict market sentiment/direction using Transformer.
        """
        if not TORCH_AVAILABLE: return 0.0
        
        with torch.no_grad():
            x = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
            prediction = self.transformer(x)
            return prediction.item()

    def get_rl_action(self, state: np.ndarray) -> int:
        """
        Get action from RL agent (0: Hold, 1: Buy, 2: Sell)
        """
        if not RL_AVAILABLE or self.rl_agent is None:
            return 0 # Default to Hold
        
        action, _ = self.rl_agent.predict(state)
        return int(action)

from core.quantum import QuantumEngine

class PortfolioOptimizer:
    """
    Manages dynamic capital allocation using PyPortfolioOpt, Scipy Fallback, or Quantum-Inspired Annealing.
    """
    def __init__(self):
        self.quantum = QuantumEngine()

    def optimize_allocation(self, prices_df: pd.DataFrame, total_capital: float, method: str = 'classical') -> dict:
        """
        Calculate optimal weights using Efficient Frontier (Max Sharpe).
        prices_df: DataFrame with columns as asset symbols and index as dates.
        method: 'classical' (PyPortfolioOpt/Scipy) or 'quantum' (Simulated Annealing)
        """
        if method == 'quantum':
            try:
                print("Initiating Quantum-Inspired Portfolio Optimization (Simulated Annealing)...")
                returns = prices_df.pct_change().dropna()
                weights = self.quantum.simulated_annealing_portfolio(
                    assets=prices_df.columns.tolist(),
                    returns=returns
                )
                allocation = {k: v * total_capital for k, v in weights.items()}
                return allocation
            except Exception as e:
                print(f"Quantum optimization failed: {e}. Falling back to classical.")
                # Fallback to classical

        if PYPFOPT_AVAILABLE:
            try:
                # Calculate expected returns and sample covariance
                mu = expected_returns.mean_historical_return(prices_df)
                S = risk_models.sample_cov(prices_df)

                # Optimize for maximal Sharpe ratio
                ef = EfficientFrontier(mu, S)
                weights = ef.max_sharpe()
                cleaned_weights = ef.clean_weights()
                
                # Convert weights to capital allocation
                allocation = {k: v * total_capital for k, v in cleaned_weights.items()}
                return allocation
            except Exception as e:
                print(f"PyPortfolioOpt optimization failed: {e}")
                # Fall through to fallback

        if SCIPY_AVAILABLE:
            try:
                return self._optimize_scipy(prices_df, total_capital)
            except Exception as e:
                print(f"Scipy optimization failed: {e}")

        # Fallback: Equal weighting
        assets = prices_df.columns
        n = len(assets)
        return {asset: total_capital / n for asset in assets}

    def _optimize_scipy(self, prices_df: pd.DataFrame, total_capital: float) -> dict:
        """
        Simple Max Sharpe optimization using Scipy.
        """
        returns = prices_df.pct_change().dropna()
        mean_returns = returns.mean()
        cov_matrix = returns.cov()
        num_assets = len(mean_returns)
        
        def negative_sharpe(weights):
            portfolio_return = np.sum(mean_returns * weights) * 252
            portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
            return -portfolio_return / portfolio_std

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))
        init_guess = num_assets * [1. / num_assets,]

        result = minimize(negative_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        
        if result.success:
            allocation = {asset: weight * total_capital for asset, weight in zip(prices_df.columns, result.x)}
            return allocation
        else:
            raise ValueError("Optimization did not converge")

