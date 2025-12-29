
# Exchange Configuration
# WARNING: Do not store real API keys in source control. Use environment variables.

import os
from dotenv import load_dotenv

load_dotenv()

EXCHANGES = {
    'bybit': {
        'apiKey': 'jzVVX4fUBWMzfJgDvJ',
        'secret': 'et0qHWE2KaSggw6qXylmhwpnUHiITzj4ylHh',
        'options': {
            'defaultType': 'swap',  # Derivatives/Perpetuals
            'adjustForTimeDifference': True,
        }
    },
    'binance': {
        'apiKey': os.getenv('BINANCE_API_KEY', ''),
        'secret': os.getenv('BINANCE_SECRET', ''),
        'options': {'defaultType': 'spot'}
    },
    'kraken': {
        'apiKey': os.getenv('KRAKEN_API_KEY', ''),
        'secret': os.getenv('KRAKEN_SECRET', ''),
    },
    'luno': {
        'apiKey': os.getenv('LUNO_API_KEY', ''),
        'secret': os.getenv('LUNO_SECRET', ''),
    },
    'quidax': {
        'apiKey': os.getenv('QUIDAX_API_KEY', ''),
        'secret': os.getenv('QUIDAX_SECRET', ''),
    },
    'nairaex': {
        'apiKey': os.getenv('NAIRAEX_API_KEY', ''),
        'secret': os.getenv('NAIRAEX_SECRET', ''),
    },
    'busha': {
        'apiKey': os.getenv('BUSHA_API_KEY', ''),
        'secret': os.getenv('BUSHA_SECRET', ''),
    },
    # Add more exchanges as needed
}

SUPPORTED_EXCHANGES = list(EXCHANGES.keys())
