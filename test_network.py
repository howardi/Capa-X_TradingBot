
import socket
import ccxt

def check_connection(host, port=443):
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception as e:
        return False

def test_connectivity():
    print("--- Global Exchange Connectivity Test ---")
    
    exchanges = {
        'Bybit': 'api.bybit.com',
        'Binance': 'api.binance.com',
        'Kraken': 'api.kraken.com',
        'CoinGecko': 'api.coingecko.com',
        'Google': 'google.com'
    }
    
    results = {}
    for name, host in exchanges.items():
        print(f"Testing {name} ({host})...", end=" ", flush=True)
        try:
            # Try DNS resolution first
            ip = socket.gethostbyname(host)
            # Try TCP connection
            connected = check_connection(host)
            if connected:
                print(f"✅ OK ({ip})")
                results[name] = True
            else:
                print(f"❌ TCP Fail ({ip})")
                results[name] = False
        except socket.gaierror:
            print("❌ DNS Fail")
            results[name] = False
        except Exception as e:
            print(f"❌ Error: {e}")
            results[name] = False
            
    return results

if __name__ == "__main__":
    test_connectivity()
