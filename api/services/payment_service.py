import os
import requests
import uuid
import time

class PaymentService:
    def __init__(self):
        self.flutterwave_key = os.getenv('FLUTTERWAVE_SECRET_KEY')
        self.paystack_key = os.getenv('PAYSTACK_SECRET_KEY')
        self.stripe_key = os.getenv('STRIPE_SECRET_KEY')

    def initiate_flutterwave(self, user, amount, email, host_url):
        if not self.flutterwave_key:
            return {"error": "Flutterwave keys missing"}
            
        tx_ref = f"tx_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        headers = {
            "Authorization": f"Bearer {self.flutterwave_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": "NGN",
            "redirect_url": f"{host_url}dashboard",
            "payment_options": "card,banktransfer,ussd",
            "customer": {
                "email": email,
                "name": user or "CapaRox User"
            },
            "customizations": {
                "title": "CapaRox Deposit",
                "description": "Wallet Funding",
                "logo": "https://ui-avatars.com/api/?name=CapaRox&background=0D8ABC&color=fff"
            }
        }
        
        try:
            response = requests.post("https://api.flutterwave.com/v3/payments", json=payload, headers=headers)
            res_data = response.json()
            if res_data.get('status') == 'success':
                return {
                    "status": "success", 
                    "link": res_data['data']['link'],
                    "tx_ref": tx_ref,
                    "provider": "flutterwave"
                }
            return {"error": res_data.get('message', 'Payment generation failed')}
        except Exception as e:
            return {"error": str(e)}

    def initiate_paystack(self, user, amount, email, host_url):
        """Simulate Paystack or Real Implementation."""
        # For demo purposes, if no key is present, we simulate a success link (or use a test link)
        if not self.paystack_key:
            # Simulation Mode
            tx_ref = f"pstk_{int(time.time())}"
            return {
                "status": "success",
                "link": f"{host_url}simulate_payment?provider=paystack&ref={tx_ref}&amount={amount}",
                "tx_ref": tx_ref,
                "message": "Simulated Paystack Link (Key missing)",
                "provider": "paystack"
            }

        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {self.paystack_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "amount": int(float(amount) * 100), # Paystack is in kobo
            "callback_url": f"{host_url}dashboard",
            "reference": f"pstk_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            res_data = response.json()
            if res_data.get('status'):
                return {
                    "status": "success",
                    "link": res_data['data']['authorization_url'],
                    "tx_ref": res_data['data']['reference'],
                    "provider": "paystack"
                }
            return {"error": res_data.get('message', 'Paystack Init Failed')}
        except Exception as e:
            return {"error": str(e)}

    def initiate_stripe(self, user, amount, email, host_url):
        """Simulate Stripe Checkout."""
        # Stripe usually requires a backend session creation
        # For this demo/MVP, we'll return a simulation link
        tx_ref = f"strp_{int(time.time())}"
        return {
            "status": "success",
            "link": f"{host_url}simulate_payment?provider=stripe&ref={tx_ref}&amount={amount}",
            "tx_ref": tx_ref,
            "message": "Simulated Stripe Link (Demo Mode)",
            "provider": "stripe"
        }

    def verify_transaction(self, provider, tx_ref, transaction_id=None):
        """Verify transaction status across providers."""
        if provider == 'flutterwave':
            if not self.flutterwave_key:
                return {"error": "Flutterwave keys missing"}
                
            endpoint = f"{transaction_id}/verify" if transaction_id else f"verify_by_reference?tx_ref={tx_ref}"
            url = f"https://api.flutterwave.com/v3/transactions/{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.flutterwave_key}",
                "Content-Type": "application/json"
            }
            try:
                response = requests.get(url, headers=headers)
                data = response.json()
                if data.get('status') == 'success' and data['data']['status'] == 'successful':
                    return {
                        "status": "success",
                        "amount": data['data']['amount'],
                        "currency": data['data']['currency'],
                        "tx_ref": data['data']['tx_ref'],
                        "flw_ref": data['data']['flw_ref']
                    }
                
                # Detailed error message for debugging
                error_msg = data.get('message', 'Verification failed')
                if 'data' in data and isinstance(data['data'], dict):
                    status = data['data'].get('status', 'unknown')
                    processor_response = data['data'].get('processor_response', 'no response')
                    error_msg = f"{error_msg} | Status: {status} | Processor: {processor_response}"
                
                print(f"Flutterwave Verification Failed: {error_msg} | Input: {tx_ref}")
                return {"status": "failed", "message": error_msg}
            except Exception as e:
                print(f"Flutterwave Verification Exception: {str(e)}")
                return {"error": str(e)}

        elif provider == 'paystack':
            # Paystack Verification
            if not self.paystack_key:
                 return {"error": "Paystack keys missing"}
            
            url = f"https://api.paystack.co/transaction/verify/{tx_ref}"
            headers = {"Authorization": f"Bearer {self.paystack_key}"}
            try:
                response = requests.get(url, headers=headers)
                data = response.json()
                if data.get('status') and data['data']['status'] == 'success':
                    return {
                        "status": "success",
                        "amount": data['data']['amount'] / 100,
                        "currency": data['data']['currency'],
                        "tx_ref": data['data']['reference']
                    }
                return {"status": "failed"}
            except Exception as e:
                return {"error": str(e)}
                
        # Default/Mock
        return {"status": "success", "amount": 0, "currency": "USD", "message": "Mock Verification"}

