import asyncio
import os
import sys
import signal
import platform
from api.bot import BotEngine
from api.core.logger import logger
from api.services.health_monitor import HealthMonitor

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Global flag for shutdown
shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}. Initiating graceful shutdown...")
    # Schedule the event set in the running loop
    loop = asyncio.get_running_loop()
    loop.call_soon_threadsafe(shutdown_event.set)

async def main():
    logger.info("Starting CapaRox Bot Worker...")
    engine = BotEngine()
    health = HealthMonitor()
    
    tick_count = 0

    # Register Signal Handlers
    # Windows has limited signal support
    if platform.system() != 'Windows':
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, lambda: shutdown_event.set())
        loop.add_signal_handler(signal.SIGINT, lambda: shutdown_event.set())

    try:
        while not shutdown_event.is_set():
            try:
                start_time = asyncio.get_running_loop().time()
                
                # Health Check (Every ~60s)
                if tick_count % 12 == 0:
                    is_healthy = await health.run_health_check()
                    if not is_healthy:
                        logger.warning("System Health Check Failed. Pausing trading for 10s...")
                        try:
                            await asyncio.wait_for(shutdown_event.wait(), timeout=10)
                        except asyncio.TimeoutError:
                            pass # Continue if not shutdown
                        continue

                # Run Tick
                # We wrap in wait_for to allow checking shutdown_event if tick hangs (unlikely with async)
                # But engine.run_tick should be non-blocking
                results = await engine.run_tick()
                
                for res in results:
                    if "Error" in str(res):
                        logger.error(f"Tick Result: {res}")
                    elif res: # Only log non-empty results
                        logger.info(f"Tick Result: {res}")
                
                tick_count += 1

                # Sleep for remainder of interval (e.g., 5 seconds)
                elapsed = asyncio.get_running_loop().time() - start_time
                sleep_time = max(1.0, 5.0 - elapsed)
                
                # Interruptible Sleep
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=sleep_time)
                    if shutdown_event.is_set():
                        break
                except asyncio.TimeoutError:
                    pass # Timeout means sleep finished

            except asyncio.CancelledError:
                logger.info("Task cancelled. Exiting...")
                break
            except Exception as e:
                logger.critical(f"Bot Worker Critical Error: {e}")
                await asyncio.sleep(5) # Backoff on crash
    finally:
        logger.info("Shutting down Bot Engine...")
        await engine.close()
        logger.info("Bot Engine Shutdown Complete.")


if __name__ == "__main__":
    # Windows Signal Handling Workaround
    if platform.system() == 'Windows':
        def win_handler(sig, frame):
            logger.info("Windows Signal Received. Stopping...")
            # We can't easily access the loop here without globals or tricks.
            # But KeyboardInterrupt usually works.
            pass
        signal.signal(signal.SIGINT, win_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Allow standard Ctrl+C to exit cleanly if signal handler didn't catch it
        pass
