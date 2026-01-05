from api.index import app

if __name__ == "__main__":
    print("Starting CapacityBay Local Server...")
    print("Open your browser at: http://127.0.0.1:5000/dashboard")
    print("Login with password: admin")
    app.run(debug=True, port=5000)
