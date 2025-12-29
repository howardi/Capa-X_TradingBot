
import os
import requests
import logging

class NotificationManager:
    """
    Unified Alert System: Telegram, Discord, Twilio (SMS).
    """
    def __init__(self):
        # Telegram
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # Discord
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        
        # Twilio
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from = os.getenv("TWILIO_FROM_NUMBER")
        self.twilio_to = os.getenv("TWILIO_TO_NUMBER")
        
        self.twilio_client = None
        if self.twilio_sid and self.twilio_token:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(self.twilio_sid, self.twilio_token)
            except ImportError:
                print("Twilio library not installed.")

    def send_alert(self, message: str, level: str = "info"):
        """
        Send alert to all configured channels.
        Level: info, warning, critical
        """
        print(f"[{level.upper()}] ALERT: {message}")
        
        # Format message based on level
        emoji = "ℹ️"
        if level == "warning": emoji = "⚠️"
        elif level == "critical": emoji = "🚨"
        
        formatted_msg = f"{emoji} **CapaRox Bot Alert**\n{message}"
        
        self._send_telegram(formatted_msg)
        self._send_discord(formatted_msg)
        
        if level == "critical":
            self._send_sms(message) # Only SMS for critical alerts

    def _send_telegram(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            return
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram send failed: {e}")

    def _send_discord(self, message):
        if not self.discord_webhook:
            return
            
        payload = {"content": message}
        try:
            requests.post(self.discord_webhook, json=payload, timeout=5)
        except Exception as e:
            print(f"Discord send failed: {e}")

    def _send_sms(self, message):
        if not self.twilio_client:
            return
            
        try:
            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_from,
                to=self.twilio_to
            )
        except Exception as e:
            print(f"Twilio SMS failed: {e}")

