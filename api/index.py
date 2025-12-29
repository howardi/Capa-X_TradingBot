from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Capa-X Trading Bot API is accessible. For the full trading dashboard and continuous execution, please deploy the Docker container to Railway or Render.",
        "version": "1.0.0",
        "environment": "Vercel Serverless"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# Vercel expects 'app' to be the entry point
