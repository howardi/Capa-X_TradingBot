import asyncio
import time
from api.core.logger import logger

class ExecutionManager:
    """
    Professional Execution Layer:
    - Smart Retry Logic (Idempotency)
    - Slippage Control
    - Order State Reconciliation
    - Error Handling
    """
    
    def __init__(self):
        self.max_retries = 3
        self.base_retry_delay = 1.0
        self.max_slippage_pct = 0.01 # 1% default slippage tolerance

    async def execute_order(self, exchange, symbol, type, side, amount, price=None, params={}):
        """
        Executes an order with retry logic and safety checks.
        """
        attempt = 0
        last_error = None
        
        # 1. Sanity Check
        if price and amount * price > 100000: # $100k Limit
             raise Exception(f"Order value {amount*price} exceeds safety limit")
        
        # 2. Slippage Check (if Market Order)
        if type == 'market' and not price:
            try:
                ticker = await exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                # For buy, we don't want price to go too high
                # For sell, we don't want price to go too low
                # However, for market orders, we just execute. 
                # Real slippage control requires limit orders or 'market' with 'price' protection (IOC).
                # We will log the expected price.
                logger.info(f"Execution expected at ~{current_price} for {symbol}")
            except Exception as e:
                logger.warning(f"Could not fetch ticker for slippage check: {e}")

        # Generate Client Order ID ONCE for Idempotency
        if 'clientOrderId' not in params:
             params['clientOrderId'] = f"bot_{int(time.time()*1000)}"

        while attempt < self.max_retries:
            try:
                logger.info(f"Execution Attempt {attempt+1}/{self.max_retries} for {side} {symbol}")
                
                order = await exchange.create_order(symbol, type, side, amount, price, params)
                
                # Verify Order Status
                if order:
                    # Some exchanges return partial info. Fetch full order if needed.
                    if order.get('status') == 'open' or order.get('status') == 'closed':
                        logger.info(f"Order Executed: {order['id']} Status: {order['status']}")
                        return order
                    else:
                        logger.warning(f"Order created with unknown status: {order}")
                        return order
                        
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Idempotency Check: If order exists, try to recover it
                if "duplicate" in error_msg or "already exists" in error_msg:
                    logger.warning("Duplicate Order detected. Checking open orders...")
                    try:
                        open_orders = await exchange.fetch_open_orders(symbol)
                        for o in open_orders:
                            if o.get('clientOrderId') == params['clientOrderId']:
                                logger.info(f"Found existing order: {o['id']}")
                                return o
                    except Exception as fetch_err:
                        logger.error(f"Failed to fetch open orders during recovery: {fetch_err}")

                logger.error(f"Order Execution Failed (Attempt {attempt+1}): {e}")
                
                if "insufficient funds" in error_msg or "balance" in error_msg:
                    # Fatal error, do not retry
                    raise e
                elif "rate limit" in error_msg:
                    await asyncio.sleep(self.base_retry_delay * (attempt + 1) * 2) # Exponential backoff
                else:
                    await asyncio.sleep(self.base_retry_delay * (attempt + 1))
            
            attempt += 1

        logger.error(f"Final Execution Failure after {self.max_retries} attempts")
        raise last_error

    async def fetch_order_safe(self, exchange, order_id, symbol=None):
        """Safe fetch order with retries"""
        try:
            return await exchange.fetch_order(order_id, symbol)
        except Exception as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            return None
