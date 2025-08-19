from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple
import math


def round_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return math.floor(value / step) * step

class BaseExchange(ABC):
    name: str

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]: ...
    @abstractmethod
    async def get_orderbook(self, symbol: str) -> Dict[str, Any]: ...
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]: ...
    @abstractmethod
    async def create_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]: ...
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> None: ...
    @abstractmethod
    def normalize_symbol(self, common: str) -> str: ...

    # новое
    @abstractmethod
    def lot_size(self, symbol: str) -> float: ...
    @abstractmethod
    def price_step(self, symbol: str) -> float: ...
    @abstractmethod
    def min_notional(self, symbol: str) -> float: ...

    def normalize_amount(self, symbol: str, amount: float) -> float:
        step = self.lot_size(symbol)
        return round_step(amount, step)

    def normalize_price(self, symbol: str, price: float) -> float:
        step = self.price_step(symbol)
        return round_step(price, step)

def best_bid_ask(ob: Dict[str, Any]) -> Tuple[float, float]:
    bids = ob.get("bids") or []
    asks = ob.get("asks") or []
    bid = float(bids[0][0]) if bids else 0.0
    ask = float(asks[0][0]) if asks else 0.0
    return bid, ask
