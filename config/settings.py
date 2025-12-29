
# Global Settings

APP_NAME = "Capa-X"
VERSION = "1.1.0"

# API Keys (Third Party Data)
COINAPI_KEY = "729d83da-285b-4ef5-9a71-933a5c56d275"
CRYPTOAPIS_KEY = "5bf465481226e6debc6cb635437761e73cbcea8e"
CMC_API_KEY = "d86d040a411d4acbafdc7f26f5a0cc69"

# Default Configuration
DEFAULT_TIMEFRAME = '1h'
DEFAULT_SYMBOL = 'BTC/USDT'
DEFAULT_EXCHANGE = 'bybit'

# Risk Management
MAX_RISK_PER_TRADE = 0.02  # 2%
STOP_LOSS_PCT = 0.05       # 5%
TAKE_PROFIT_PCT = 0.10     # 10%

# Analysis
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# UI Settings
THEME = 'dark'
REFRESH_RATE = 60  # seconds

# Proxy Settings
# Use this if you are in a restricted region (US/UK/Canada) and cannot connect to Bybit/Binance.
# Example: "http://user:pass@host:port" or "socks5://user:pass@host:port"
HTTP_PROXY = ""
HTTPS_PROXY = ""
