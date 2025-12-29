import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data import DataManager
import time

def test_failover():
    print("Testing DataManager Failover Logic...")
    
    # Initialize with a fake exchange to force failure or just use binance and force switch
    dm = DataManager('binance')
    print(f"Initial Exchange: {dm.exchange_id}")
    
    # Mock the failover triggers
    # We can't easily force a network error without mocking ccxt, 
    # but we can test the switch_exchange method directly.
    
    print("\n--- Simulating Manual Failover Trigger ---")
    success = dm.switch_exchange()
    
    if success:
        print(f"✅ Failover Successful. New Exchange: {dm.exchange_id}")
        if dm.failover_active:
            print("✅ Failover flag is Active.")
        else:
            print("❌ Failover flag NOT Active.")
    else:
        print("❌ Failover Failed.")
        
    print(f"Current Exchange ID: {dm.exchange_id}")
    print(f"Primary Exchange ID: {dm.primary_exchange_id}")
    
    if dm.exchange_id != dm.primary_exchange_id:
        print("✅ Exchange ID changed correctly.")
    else:
        print("❌ Exchange ID did NOT change.")

    # Test Secondary Failover
    print("\n--- Simulating Secondary Failover ---")
    dm.switch_exchange()
    print(f"New Exchange: {dm.exchange_id}")

if __name__ == "__main__":
    test_failover()
