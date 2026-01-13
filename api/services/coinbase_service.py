import json
import time
import threading
import websocket
import jwt
import hashlib
import hmac
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CoinbaseService:
    def __init__(self):
        self.api_key = os.getenv('COINBASE_API_KEY')
        self.secret_key = os.getenv('COINBASE_SECRET')
        self.ws_url = "wss://advanced-trade-ws.coinbase.com"
        self.ws = None
        self.thread = None
        self.running = False
        self.latest_data = {}
        self.logger = logging.getLogger(__name__)

        if not self.api_key or not self.secret_key:
            self.logger.warning("⚠️ Coinbase API Key or Secret missing.")

    def _get_formatted_private_key(self):
        """
        Formats the base64 secret into a PEM formatted EC Private Key.
        """
        if not self.secret_key:
            return None
        
        # If it already has headers, return as is
        if "-----BEGIN EC PRIVATE KEY-----" in self.secret_key:
            return self.secret_key
            
        # Wrap the raw base64 secret
        return f"-----BEGIN EC PRIVATE KEY-----\n{self.secret_key}\n-----END EC PRIVATE KEY-----"

    def sign_with_jwt(self, message, channel, products=[]):
        try:
            private_key = self._get_formatted_private_key()
            if not private_key:
                # Fallback to HMAC if private key format is invalid (e.g. legacy key)
                return self.sign_with_hmac(message, channel, products)

            if "-----BEGIN EC PRIVATE KEY-----" not in private_key:
                 # If it doesn't look like a PEM key, try HMAC
                return self.sign_with_hmac(message, channel, products)

            payload = {
                "iss": "coinbase-cloud",
                "nbf": int(time.time()),
                "exp": int(time.time()) + 120,
                "sub": self.api_key,
            }
            headers = {
                "kid": self.api_key,
                "nonce": hashlib.sha256(os.urandom(16)).hexdigest()
            }
            
            # ES256 algorithm requires cryptography library
            token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
            message['jwt'] = token
            return message
        except Exception as e:
            self.logger.error(f"JWT Signing Error: {e}")
            # Try HMAC as last resort if JWT fails?
            return self.sign_with_hmac(message, channel, products)

    def sign_with_hmac(self, message, channel, products=[]):
        try:
            timestamp = str(int(time.time()))
            product_ids_str = ",".join(products)
            message_body = f"{timestamp}{channel}{product_ids_str}"
            
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message_body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            message['api_key'] = self.api_key
            message['timestamp'] = timestamp
            message['signature'] = signature
            return message
        except Exception as e:
            self.logger.error(f"HMAC Signing Error: {e}")
            return message

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            # Store latest data by channel/product
            if 'channel' in data:
                channel = data['channel']
                self.latest_data[channel] = data
                
            # Log specific events
            if data.get('events'):
                for event in data['events']:
                    if event.get('type') == 'snapshot' or event.get('type') == 'update':
                        # self.logger.info(f"Coinbase Update: {event}")
                        pass
                        
            # self.logger.debug(f"Coinbase Message: {data}")
            
        except Exception as e:
            self.logger.error(f"Message Parse Error: {e}")

    def on_error(self, ws, error):
        self.logger.error(f"Coinbase WS Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.logger.info(f"Coinbase WS Closed: {close_status_code} - {close_msg}")
        # Do NOT set self.running = False here, to allow auto-reconnect in run_thread

    def on_open(self, ws):
        self.logger.info("Coinbase WS Opened")
        products = ["BTC-USD", "ETH-USD"]
        channel = "level2" # Using level2 as requested in example
        
        subscribe_message = {
            "type": "subscribe",
            "channel": channel,
            "product_ids": products
        }
        
        signed_message = self.sign_with_jwt(subscribe_message, channel, products)
        ws.send(json.dumps(signed_message))
        self.logger.info(f"Subscribed to {products} on {channel}")

    def start_stream(self):
        if self.running:
            self.logger.warning("Coinbase stream already running.")
            return

        self.running = True
        # Enable trace for debugging if needed
        # websocket.enableTrace(True)
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        def run_thread():
            while self.running:
                try:
                    self.ws.run_forever()
                except Exception as e:
                    self.logger.error(f"Coinbase WS Crash: {e}")
                
                if self.running:
                    self.logger.info("Coinbase WS disconnected. Reconnecting in 5s...")
                    time.sleep(5)
                    # Re-init ws object because run_forever closes it? 
                    # Actually WebSocketApp can be reused or needs recreation?
                    # usually needs recreation.
                    self.ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=self.on_open,
                        on_message=self.on_message,
                        on_error=self.on_error,
                        on_close=self.on_close
                    )

        self.thread = threading.Thread(target=run_thread, daemon=True)
        self.thread.start()
        self.logger.info("Coinbase WebSocket Service Started")

    def stop_stream(self):
        if self.ws:
            self.ws.close()
        self.running = False
        self.logger.info("Coinbase Service Stopped")

    def get_latest_data(self):
        return self.latest_data

# Singleton instance
coinbase_service = CoinbaseService()
