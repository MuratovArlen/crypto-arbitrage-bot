from datetime import datetime, timedelta
from typing import Dict

class AntiFlood:
    def __init__(self, seconds: int = 30) -> None:
        self.seconds = seconds
        self._last: Dict[str, datetime] = {}

    def allow(self, symbol: str) -> bool:
        now = datetime.utcnow()
        last = self._last.get(symbol)
        if last and now - last < timedelta(seconds=self.seconds):
            return False
        self._last[symbol] = now
        return True

class DailyLimitUsd:
    def __init__(self, limit_usd: float) -> None:
        self.limit = limit_usd
        self.spent = 0.0

    def can_spend(self, usd: float) -> bool:
        return self.spent + usd <= self.limit

    def add(self, usd: float) -> None:
        self.spent += usd
