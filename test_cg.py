
import requests

def test_coingecko(symbol):
    try:
        base = symbol.split('/')[0].lower()
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'symbols': base
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, params=params, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Data: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

test_coingecko("BTC/USDT")
