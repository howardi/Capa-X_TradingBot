import os
import smtplib
import requests
from email.mime.text import MIMEText
from api.core.logger import logger
from dotenv import load_dotenv

load_dotenv()

class NotificationService:
    """
    Handles critical alerts via Telegram and Email.
    """
    
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.admin_email = os.getenv('ADMIN_EMAIL')

    def send_telegram(self, message):
        """Sends a message to the configured Telegram chat."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.debug("Telegram credentials not set. Skipping alert.")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info("Telegram alert sent.")
                return True
            else:
                logger.error(f"Telegram failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    def send_email(self, subject, body):
        """Sends an email to the admin."""
        if not self.smtp_user or not self.smtp_pass or not self.admin_email:
            logger.debug("SMTP credentials not set. Skipping email alert.")
            return False
            
        try:
            msg = MIMEText(body)
            msg['Subject'] = f"[CapaRox Alert] {subject}"
            msg['From'] = self.smtp_user
            msg['To'] = self.admin_email
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
                
            logger.info(f"Email alert sent to {self.admin_email}")
            return True
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

    def alert(self, subject, message, level='info'):
        """
        Unified alert method.
        Level: info, warning, critical
        """
        formatted_msg = f"*{subject}*\n\n{message}\n\n_Level: {level.upper()}_"
        
        # Always log
        if level == 'critical':
            logger.critical(f"{subject}: {message}")
            # Send both
            self.send_telegram(f"🚨 {formatted_msg}")
            self.send_email(subject, message)
        elif level == 'warning':
            logger.warning(f"{subject}: {message}")
            # Send Telegram only
            self.send_telegram(f"⚠️ {formatted_msg}")
        else:
            logger.info(f"{subject}: {message}")
            # Optional: Send Telegram for info?
            # self.send_telegram(f"ℹ️ {formatted_msg}")

# Global instance
notifier = NotificationService()
