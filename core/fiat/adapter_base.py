from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class FiatAdapter(ABC):
    """
    Abstract Base Class for Fiat Payment Providers (Paystack, Flutterwave, etc.)
    """
    
    def __init__(self, api_key: str, secret_key: str, live_mode: bool = False, encryption_key: str = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.live_mode = live_mode
        self.encryption_key = encryption_key

    @abstractmethod
    def initialize_deposit(self, amount: float, email: str, currency: str = "NGN", metadata: Dict = None) -> Dict:
        """
        Initialize a deposit transaction.
        Returns: Dict containing 'authorization_url', 'reference', etc.
        """
        pass

    @abstractmethod
    def verify_transaction(self, reference: str) -> Dict:
        """
        Verify the status of a transaction.
        Returns: Dict with status ('success', 'failed'), amount, etc.
        """
        pass

    @abstractmethod
    def get_banks(self, country: str = "Nigeria") -> List[Dict]:
        """
        Get list of supported banks.
        """
        pass

    @abstractmethod
    def resolve_account_number(self, account_number: str, bank_code: str) -> Dict:
        """
        Resolve account name from number and bank code.
        """
        pass

    @abstractmethod
    def initiate_transfer(self, amount: float, recipient_code: str, reason: str = "") -> Dict:
        """
        Initiate a transfer (withdrawal) to a bank account.
        """
        pass

    @abstractmethod
    def create_transfer_recipient(self, name: str, account_number: str, bank_code: str, currency: str = "NGN") -> Dict:
        """
        Create a transfer recipient (beneficiary).
        """
        pass
