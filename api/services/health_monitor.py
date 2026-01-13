import asyncio
import time
import ccxt.async_support as ccxt
from api.core.logger import logger
from api.db import get_db_connection

class HealthMonitor:
    """
    Monitors System Health:
    1. Database Connectivity
    2. Exchange API Latency & Availability
    3. Heartbeat Logging
    """
    
    def __init__(self):
        self.status = "healthy"
        self.last_heartbeat = time.time()
        self.exchange_latencies = {}
        self.errors_count = 0
        self.max_errors_threshold = 5

    async def check_db(self):
        """Verifies Database Connection."""
        try:
            conn = get_db_connection()
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception as e:
            logger.critical(f"Health Check Failed: Database unreachable: {e}")
            return False

    async def check_exchange(self, exchange_id='binance'):
        """Checks Exchange Latency and Availability."""
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class()
            
            start = time.time()
            await exchange.fetch_time() # Lightweight call
            latency = (time.time() - start) * 1000 # ms
            
            await exchange.close()
            
            self.exchange_latencies[exchange_id] = latency
            
            if latency > 1000: # 1s warning
                logger.warning(f"High Latency for {exchange_id}: {latency:.2f}ms")
            
            return True, latency
        except Exception as e:
            logger.error(f"Health Check Failed: Exchange {exchange_id} unreachable: {e}")
            return False, 0.0

    async def run_health_check(self):
        """Runs full system health check."""
        db_ok = await self.check_db()
        ex_ok, latency = await self.check_exchange('binance')
        
        if db_ok and ex_ok:
            self.status = "healthy"
            self.errors_count = 0
            logger.info(f"System Health: OK | DB: Connected | Binance Latency: {latency:.2f}ms")
            return True
        else:
            self.status = "degraded"
            self.errors_count += 1
            if self.errors_count >= self.max_errors_threshold:
                logger.critical("System Unhealthy: Max error threshold reached. Triggering shutdown/alert.")
                # Could trigger emergency stop here
            return False

    def log_heartbeat(self):
        logger.info(f"HEARTBEAT | Status: {self.status} | Uptime: {int(time.time() - self.last_heartbeat)}s")
