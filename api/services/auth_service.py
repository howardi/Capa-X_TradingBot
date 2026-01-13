import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from api.db import get_db_connection

class AuthService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    def register_user(self, username, email, password, full_name=None, phone_number=None):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            # Check if exists
            c.execute("SELECT id FROM users WHERE username=? OR email=?", (username, email))
            if c.fetchone():
                return {"error": "Username or email already exists"}
                
            # Hash Password
            hashed_pw = generate_password_hash(password)
            
            c.execute("INSERT INTO users (username, email, password, full_name, phone_number, is_admin) VALUES (?, ?, ?, ?, ?, 0)", 
                      (username, email, hashed_pw, full_name, phone_number))
            conn.commit()
            return {"status": "success", "message": "User registered successfully"}
        except Exception as e:
            conn.rollback()
            return {"error": str(e)}
        finally:
            conn.close()

    def login_user(self, username, password):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("SELECT id, username, password, email, full_name, phone_number, is_admin FROM users WHERE username=?", (username,))
            user = c.fetchone()
            
            if not user or not user['password']:
                return {"error": "Invalid credentials"}
                
            if check_password_hash(user['password'], password):
                return {
                    "status": "success", 
                    "username": user['username'], 
                    "is_admin": user['is_admin'],
                    "token": "dummy_token_for_now" # In prod, return JWT
                }
            else:
                return {"error": "Invalid credentials"}
        finally:
            conn.close()

    def forgot_password(self, email):
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT id, username FROM users WHERE email=?", (email,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return {"error": "Email not found"}
            
        # Generate Token
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)
        
        c.execute("UPDATE users SET reset_token=?, reset_token_expiry=? WHERE id=?", 
                  (token, expiry, user['id']))
        conn.commit()
        conn.close()
        
        # Send Email
        reset_link = f"{self.frontend_url}/reset-password?token={token}"
        subject = "CapaRox Password Reset"
        body = f"Hi {user['username']},\n\nClick the link below to reset your password:\n{reset_link}\n\nThis link expires in 1 hour."
        
        return self._send_email(email, subject, body)

    def reset_password(self, token, new_password):
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT id, reset_token_expiry FROM users WHERE reset_token=?", (token,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return {"error": "Invalid token"}
            
        # Check Expiry
        # SQLite returns string, Postgres returns datetime
        expiry = user['reset_token_expiry']
        if isinstance(expiry, str):
            expiry = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S.%f') if '.' in expiry else datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S')
            
        if datetime.utcnow() > expiry:
            conn.close()
            return {"error": "Token expired"}
            
        # Update Password (In prod, hash this!)
        hashed_pw = generate_password_hash(new_password)
        c.execute("UPDATE users SET password=?, reset_token=NULL, reset_token_expiry=NULL WHERE id=?", 
                  (hashed_pw, user['id']))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Password updated successfully"}

    def _send_email(self, to_email, subject, body):
        if not self.smtp_user or not self.smtp_pass:
            # Mock Send
            print(f"--- MOCK EMAIL TO {to_email} ---\nSubject: {subject}\n{body}\n-----------------------------")
            return {"status": "success", "message": "Email sent (mock)"}
            
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
                
            return {"status": "success", "message": "Email sent"}
        except Exception as e:
            print(f"Email Error: {e}")
            return {"error": "Failed to send email"}

    def oauth_login(self, provider, profile):
        """
        Handles OAuth login/signup.
        profile: dict containing email, name, id from provider
        """
        conn = get_db_connection()
        c = conn.cursor()
        
        email = profile.get('email')
        provider_id = profile.get('sub') or profile.get('id')
        name = profile.get('name') or email.split('@')[0]
        
        # Check if user exists by provider ID
        id_col = f"{provider}_id"
        c.execute(f"SELECT * FROM users WHERE {id_col}=?", (provider_id,))
        user = c.fetchone()
        
        if user:
            conn.close()
            # Convert to dict to ensure .get() works for sqlite3.Row
            user_dict = dict(user)
            return {"status": "success", "username": user_dict['username'], "is_admin": user_dict.get('is_admin', 0)}
            
        # Check if email exists (link account)
        if email:
            c.execute("SELECT * FROM users WHERE email=?", (email,))
            user = c.fetchone()
            if user:
                # Link account
                c.execute(f"UPDATE users SET {id_col}=? WHERE id=?", (provider_id, user['id']))
                conn.commit()
                conn.close()
                user_dict = dict(user)
                return {"status": "success", "username": user_dict['username'], "is_admin": user_dict.get('is_admin', 0)}
        
        # Create new user
        # Handle username collision
        base_username = name.replace(' ', '').lower()
        username = base_username
        counter = 1
        while True:
            c.execute("SELECT id FROM users WHERE username=?", (username,))
            if not c.fetchone():
                break
            username = f"{base_username}{counter}"
            counter += 1
            
        c.execute(f"INSERT INTO users (username, email, {id_col}, is_admin) VALUES (?, ?, ?, 0)", 
                  (username, email, provider_id))
        conn.commit()
        conn.close()
        
        return {"status": "success", "username": username, "message": "Account created via OAuth"}
