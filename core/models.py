
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Trade:
    symbol: str
    side: str  # 'buy' or 'sell'
    price: float
    amount: float
    timestamp: datetime
    id: Optional[str] = None
    status: str = 'closed'
    pnl: Optional[float] = 0.0

@dataclass
class Signal:
    symbol: str
    type: str  # 'buy', 'sell', 'hold'
    price: float
    timestamp: datetime
    reason: str
    indicators: dict
    # Elite Bot Fields
    score: float = 0.0
    regime: str = "Unknown"
    liquidity_status: str = "Unknown"
    confidence: float = 0.0
    decision_details: dict = None

@dataclass
class MarketData:
    symbol: str
    timeframe: str
    ohlcv: List[List]  # [timestamp, open, high, low, close, volume]
