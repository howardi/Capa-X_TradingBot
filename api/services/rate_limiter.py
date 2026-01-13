import asyncio
import time
from api.core.logger import logger

class RateLimitManager:
    """
    Centralized Rate Limit Manager.
    Provides adaptive throttling and token bucket rate limiting per exchange.
    """
    def __init__(self):
        # exchange_id -> { 'tokens': float, 'last_refill': float, 'rate': float, 'backoff_until': float }
        self.limits = {}
        # Default: 10 requests per second (conservative)
        self.default_rate = 10.0
        self.default_capacity = 10.0
        self._lock = asyncio.Lock()

    def _get_limiter_state(self, exchange_id):
        if exchange_id not in self.limits:
            self.limits[exchange_id] = {
                'tokens': self.default_capacity,
                'last_refill': time.time(),
                'rate': self.default_rate,
                'backoff_until': 0.0
            }
        return self.limits[exchange_id]

    async def acquire(self, exchange_id, cost=1):
        """
        Acquire permission to send a request.
        Waits if rate limit is exceeded or if in backoff period.
        """
        while True:
            wait_time = 0.0
            async with self._lock:
                state = self._get_limiter_state(exchange_id)
                now = time.time()
                
                # 1. Check Backoff (Adaptive Throttling)
                if now < state['backoff_until']:
                    wait_time = state['backoff_until'] - now
                    logger.warning(f"RateLimit: Backing off for {exchange_id}, wait {wait_time:.2f}s")
                else:
                    # 2. Refill Tokens
                    elapsed = now - state['last_refill']
                    refill = elapsed * state['rate']
                    state['tokens'] = min(self.default_capacity, state['tokens'] + refill)
                    state['last_refill'] = now

                    # 3. Consume Tokens
                    if state['tokens'] >= cost:
                        state['tokens'] -= cost
                        return # Success
                    else:
                        # Calculate wait time
                        needed = cost - state['tokens']
                        wait_time = needed / state['rate']
                        logger.debug(f"RateLimit: Throttling {exchange_id} for {wait_time:.3f}s")

            # Sleep outside lock to avoid blocking other exchanges
            if wait_time > 0:
                await asyncio.sleep(wait_time)

    async def handle_429(self, exchange_id, retry_after=None):
        """
        Trigger backoff when a 429 is received.
        """
        async with self._lock:
            state = self._get_limiter_state(exchange_id)
            wait = retry_after if retry_after else 60.0 # Default 60s backoff
            state['backoff_until'] = time.time() + wait
            logger.warning(f"RateLimit: 429 received for {exchange_id}. Blocking for {wait}s")

rate_limit_manager = RateLimitManager()
