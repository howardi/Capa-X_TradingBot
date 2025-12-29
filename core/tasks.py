from celery import Celery
import os

# Initialize Celery
# Default to localhost if not in Docker
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app = Celery('capax_tasks', broker=broker_url)

@app.task
def execute_trade_async(trade_data):
    """
    Background task to execute trade or log it.
    """
    print(f"Async Task: Processing trade for {trade_data.get('symbol')}")
    # In a real scenario, this would retry orders or update DB
    return f"Processed {trade_data.get('symbol')}"

@app.task
def train_model_async(symbol):
    """
    Background task to retrain AI models
    """
    print(f"Async Task: Retraining model for {symbol}")
    # Simulate training
    import time
    time.sleep(5)
    return f"Model trained for {symbol}"
