
# Trading Configuration & Constraints
# Objectives: Target 70-90% APR (Non-guaranteed)

TRADING_CONFIG = {
    "objectives": {
        "target_apr_min": 0.70,  # 70%
        "target_apr_max": 0.90,  # 90%
        "max_drawdown_limit": 0.08, # 8% Max Drawdown allowed before kill-switch (Stricter for safety)
    },
    "risk": {
        "max_open_positions": 5,
        "max_correlation": 0.7, # Max allowed correlation between assets in portfolio
        "max_leverage": 3.0,
        "kill_switch_drawdown": 0.08, # User Config: 8% Drawdown Limit
        "per_trade_risk_min": 0.005, # 0.5%
        "per_trade_risk_max": 0.01, # 1.0% (Reduced from 1.5% for lower loss rate)
        "stop_atr_mult": 2.0, # User Config
        "tp_atr_mult": 3.0,   # User Config
    },
    "fees": {
        "maker": 0.0002, # 0.02%
        "taker": 0.0005, # 0.05%
        "slippage_est": 0.001 # 0.1% (10 bps)
    },
    "allocation": {
        "rebalance_frequency": "daily", # daily, hourly
        "min_confidence_threshold": 0.80 # Stricter (80%) for elite execution
    },
    "ai": {
        "enabled": True,
        "sentiment_analysis": True,
        "market_regime_detection": True,
        "ml_signal_weighting": True
    }
}
