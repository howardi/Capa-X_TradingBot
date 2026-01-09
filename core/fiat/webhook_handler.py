from flask import Flask, request, jsonify
import hmac
import hashlib
import os

app = Flask(__name__)

# This is a conceptual implementation of a Webhook Handler for Paystack/Flutterwave
# In a real deployment, this would be part of your backend API service (e.g., FastAPI, Flask, Django)


def verify_flutterwave_signature(request_headers, secret_hash):
    """
    Verify Flutterwave Webhook Signature
    """
    signature = request_headers.get('verif-hash')
    if not signature or signature != secret_hash:
        return False
    return True

@app.route('/webhook/flutterwave', methods=['POST'])
def flutterwave_webhook():
    secret_hash = os.environ.get("FLUTTERWAVE_SECRET_HASH")
    
    if not verify_flutterwave_signature(request.headers, secret_hash):
        return jsonify({"status": "error", "message": "Invalid signature"}), 400

    event = request.json
    
    # 1. Idempotency Check
    # if storage.get_transaction(event['data']['tx_ref']):
    #     return jsonify({"status": "success", "message": "Already processed"}), 200

    if event['event'] == 'charge.completed' and event['data']['status'] == 'successful':
        data = event['data']
        reference = data['tx_ref']
        amount = data['amount']
        email = data['customer']['email']
        
        # 2. Process Deposit
        # bot.fiat_manager.credit_user(email, amount, reference)
        
        print(f"Deposit Successful: {amount} NGN from {email} (Ref: {reference})")

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(port=5000)
