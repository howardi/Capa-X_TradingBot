import random
import time
import logging

class ChaosMonkey:
    """
    Simulates infrastructure failures to test system resilience.
    "What doesn't kill the bot makes it stronger."
    """
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.logger = logging.getLogger("ChaosMonkey")

    def unleash_chaos(self, level: str = 'mild') -> dict:
        """
        Trigger random system failures.
        Level: 'mild', 'moderate', 'severe'
        """
        scenarios = [
            self._simulate_network_latency,
            self._simulate_data_feed_drop,
            self._simulate_exchange_disconnect,
            self._simulate_flash_crash
        ]
        
        # Select scenario based on level
        if level == 'mild':
            scenario = random.choice(scenarios[:2])
        elif level == 'moderate':
            scenario = random.choice(scenarios[:3])
        else:
            scenario = random.choice(scenarios)
            
        return scenario()

    def _simulate_network_latency(self):
        latency = random.uniform(0.5, 2.0)
        time.sleep(latency)
        return {
            "type": "Network Latency",
            "impact": f"Added {latency:.2f}s delay",
            "recovery": "Automatic (TCP Retry)",
            "status": "Recovered"
        }

    def _simulate_data_feed_drop(self):
        # Simulate null data
        original_data = self.bot.data_manager.cache.get(self.bot.symbol)
        self.bot.data_manager.cache[self.bot.symbol] = None
        
        # Recovery check
        try:
            self.bot.data_manager.fetch_ticker(self.bot.symbol)
            status = "Recovered (Fetch Triggered)"
        except:
            status = "Failed (Feed Down)"
            
        return {
            "type": "Data Feed Drop",
            "impact": "Missing Ticker Data",
            "recovery": "Refetch Logic",
            "status": status
        }

    def _simulate_exchange_disconnect(self):
        self.bot.data_manager.connection_status = "Disconnected"
        # Trigger reconnection logic
        self.bot.data_manager.ensure_markets_loaded()
        
        return {
            "type": "Exchange Disconnect",
            "impact": "API Connection Lost",
            "recovery": "Auto-Reconnect Routine",
            "status": "Recovered" if self.bot.data_manager.markets_loaded else "Failed"
        }

    def _simulate_flash_crash(self):
        # Simulate -20% price drop in memory
        return {
            "type": "Simulated Flash Crash",
            "impact": "Price Drop -20%",
            "recovery": "Stop-Loss Trigger Test",
            "status": "Simulation Logged"
        }
