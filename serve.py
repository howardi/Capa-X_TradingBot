from waitress import serve
from api.index import app
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting CapaRox Production Server on port {port}...")
    print(f"🌍 Open http://localhost:{port} in your browser")
    serve(app, host='0.0.0.0', port=port)
