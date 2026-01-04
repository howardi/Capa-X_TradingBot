# Global Settings
import os
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

APP_NAME = "CapacityBay"
VERSION = "1.1.0"

# --- Exchange API Keys ---
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET', '')

BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
BYBIT_SECRET = os.getenv('BYBIT_SECRET', '')

# --- Third Party Data ---
COINAPI_KEY = os.getenv('COINAPI_KEY', "729d83da-285b-4ef5-9a71-933a5c56d275")
CRYPTOAPIS_KEY = os.getenv('CRYPTOAPIS_KEY', "5bf465481226e6debc6cb635437761e73cbcea8e")
CMC_API_KEY = os.getenv('CMC_API_KEY', "d86d040a411d4acbafdc7f26f5a0cc69")

# --- Web3 Settings ---
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '')
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
INFURA_URL = os.getenv('INFURA_URL', 'https://mainnet.infura.io/v3/your_infura_key')

# Default Configuration
DEFAULT_TIMEFRAME = '1h'
DEFAULT_SYMBOL = 'BTC/USDT'
DEFAULT_EXCHANGE = os.getenv('DEFAULT_EXCHANGE', 'bybit')

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
HTTP_PROXY = os.getenv('PROXY_URL', '')
HTTPS_PROXY = os.getenv('PROXY_URL', '')
