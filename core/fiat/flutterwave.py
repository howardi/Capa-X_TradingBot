import requests
import uuid
import json
from typing import Dict, List, Optional
from core.fiat.adapter_base import FiatAdapter

class FlutterwaveAdapter(FiatAdapter):
    def __init__(self, api_key: str, secret_key: str, live_mode: bool = False, encryption_key: str = None):
        super().__init__(api_key, secret_key, live_mode, encryption_key)

    BASE_URL = "https://api.flutterwave.com/v3"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        url = f"{self.BASE_URL}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self._headers(), timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=self._headers(), json=data, timeout=10)
            else:
                return {"status": "error", "message": "Method not supported"}
            
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_rate(self, source_currency: str, destination_currency: str, amount: float = 1.0) -> Dict:
        """
        Get exchange rate from Flutterwave.
        """
        params = {
            "source_currency": source_currency,
            "destination_currency": destination_currency,
            "amount": amount
        }
        resp = self._request("GET", f"/transfers/rates?source_currency={source_currency}&destination_currency={destination_currency}&amount={amount}")
        
        if resp.get('status') == 'success':
            data = resp.get('data', {})
            return {
                "status": "success",
                "rate": data.get('rate'),
                "source_currency": data.get('source_currency'),
                "destination_currency": data.get('destination_currency')
            }
        return {"status": "error", "message": resp.get('message', 'Failed to fetch rate')}

    def initialize_deposit(self, amount: float, email: str, currency: str = "NGN", metadata: Dict = None) -> Dict:
        tx_ref = str(uuid.uuid4())
        payload = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": currency,
            "redirect_url": "https://localhost:8501", # Placeholder
            "customer": {
                "email": email
            },
            "meta": metadata or {}
        }
        
        resp = self._request("POST", "/payments", payload)
        
        if resp.get('status') == 'success':
            data = resp.get('data', {})
            return {
                "status": "success",
                "reference": tx_ref,
                "authorization_url": data.get('link'),
                "access_code": None # FW doesn't use access_code same way
            }
        return {"status": "error", "message": resp.get('message', 'Unknown error')}

    def verify_transaction(self, reference: str) -> Dict:
        """
        Verify transaction by tx_ref.
        """
        resp = self._request("GET", f"/transactions/verify_by_reference?tx_ref={reference}")
        
        if resp.get('status') == 'success':
            data = resp.get('data', {})
            return {
                "status": "success" if data.get('status') == "successful" else "pending",
                "amount": float(data.get('amount', 0)),
                "currency": data.get('currency'),
                "gateway_status": data.get('processor_response'),
                "id": data.get('id')
            }
        return {"status": "error", "message": resp.get('message')}

    def get_banks(self, country: str = "NG") -> List[Dict]:
        resp = self._request("GET", f"/banks/{country}")
        if resp.get('status') == 'success':
            banks = resp.get('data', [])
            return [{"name": b['name'], "code": b['code'], "id": b['id']} for b in banks]
        return []

    def resolve_account_number(self, account_number: str, bank_code: str) -> Dict:
        payload = {"account_number": account_number, "account_bank": bank_code}
        resp = self._request("POST", "/accounts/resolve", payload)
        if resp.get('status') == 'success':
            return {
                "status": "success",
                "account_name": resp['data']['account_name'],
                "account_number": resp['data']['account_number']
            }
        return {"status": "error", "message": resp.get('message')}

    def create_transfer_recipient(self, name: str, account_number: str, bank_code: str, currency: str = "NGN") -> Dict:
        """
        For Flutterwave, we pack the account details into a JSON string to act as a virtual 'recipient_code'.
        This allows us to maintain the same interface as Paystack while using FW's direct transfer endpoint.
        """
        details = {
            "account_bank": bank_code,
            "account_number": account_number,
            "currency": currency,
            "name": name
        }
        return {
            "status": "success",
            "recipient_code": json.dumps(details),
            "details": details
        }

    def get_balances(self) -> List[Dict]:
        """
        Fetch all balances.
        """
        resp = self._request("GET", "/balances")
        if resp.get('status') == 'success':
            return resp.get('data', [])
        return []

    def initiate_transfer(self, amount: float, recipient_code: str, reason: str = "") -> Dict:
        """
        Initiate a transfer using the virtual recipient code (JSON string of details).
        """
        try:
            details = json.loads(recipient_code)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid recipient code format for Flutterwave"}
            
        payload = {
            "account_bank": details.get("account_bank"),
            "account_number": details.get("account_number"),
            "amount": amount,
            "currency": details.get("currency", "NGN"),
            "narration": reason or "Withdrawal",
            "reference": str(uuid.uuid4())
            # "debit_currency": "NGN" # Removed to allow default payout source
        }
        
        # print(f"DEBUG: Transfer Payload: {json.dumps(payload, indent=2)}")
        
        resp = self._request("POST", "/transfers", payload)
        
        if resp.get('status') == 'success':
            data = resp.get('data', {})
            return {
                "status": "pending", # FW transfers are usually pending initially
                "reference": payload["reference"],
                "message": resp.get("message"),
                "id": data.get("id"),
                "fee": data.get("fee", 0)
            }
            
        return {"status": "error", "message": resp.get('message', 'Transfer failed')}
