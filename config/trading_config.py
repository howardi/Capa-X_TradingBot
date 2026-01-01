
# Trading Configuration & Constraints
# Objectives: Target 70-90% APR (Non-guaranteed)

TRADING_CONFIG = {
    "objectives": {
        "target_apr_min": 0.70,  # 70%
        "target_apr_max": 0.90,  # 90%
        "max_drawdown_limit": 0.10, # 10% Max Drawdown allowed before kill-switch (User Config)
    },
    "risk": {
        "max_open_positions": 5,
        "max_correlation": 0.7, # Max allowed correlation between assets in portfolio
        "max_leverage": 3.0,
        "kill_switch_drawdown": 0.10, # User Config: 10% Drawdown Limit
        "per_trade_risk_min": 0.005, # 0.5%
        "per_trade_risk_max": 0.015, # 1.5%
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
        "min_confidence_threshold": 0.65 # User Config
    }
}
