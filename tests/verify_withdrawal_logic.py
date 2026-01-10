import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bot import TradingBot
from unittest.mock import MagicMock

def test_token_resolution():
    print("Testing Token Resolution Logic...")
    
    bot = TradingBot()
    # Mock Web3Wallet
    bot.web3_wallet = MagicMock()
    bot.web3_wallet.is_connected.return_value = True
    bot.web3_wallet.send_token = MagicMock(return_value={"status": "success"})
    bot.web3_wallet.send_native = MagicMock(return_value={"status": "success"})
    
    # Test Cases
    test_cases = [
        # (ChainID, Asset, ExpectedAddress)
        ('1', 'USDT', '0xdAC17F958D2ee523a2206206994597C13D831ec7'), # ETH Mainnet
        ('56', 'USDT', '0x55d398326f99059fF775485246999027B3197955'), # BSC
        ('137', 'USDC', '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'), # Polygon
        ('42161', 'USDT', '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'), # Arbitrum
    ]
    
    bot.trading_mode = 'DEX'
    
    for chain_id, asset, expected_addr in test_cases:
        bot.web3_wallet.chain_id = chain_id
        
        # Call withdraw
        bot.withdraw_crypto(asset, 10.0, "0xUserAddress")
        
        # Verify send_token was called with correct contract address
        # args[0] is token_address
        call_args = bot.web3_wallet.send_token.call_args
        if call_args:
            actual_addr = call_args[0][0]
            if actual_addr == expected_addr:
                print(f"✅ [Chain {chain_id}] {asset} -> {actual_addr} (MATCH)")
            else:
                print(f"❌ [Chain {chain_id}] {asset} -> Expected {expected_addr}, Got {actual_addr}")
        else:
            print(f"❌ [Chain {chain_id}] {asset} -> send_token NOT CALLED")
            
        bot.web3_wallet.send_token.reset_mock()

    # Test Native
    bot.web3_wallet.chain_id = '1'
    bot.withdraw_crypto('ETH', 1.0, "0xUserAddress")
    if bot.web3_wallet.send_native.called:
        print("✅ Native ETH Withdrawal Triggered Correctly")
    else:
        print("❌ Native ETH Withdrawal Failed")

if __name__ == "__main__":
    test_token_resolution()
