import ccxt.async_support as ccxt
from typing import Any, Dict
from .base import BaseExchange

class GateClient(BaseExchange):
    name = "gate"

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.x = ccxt.gateio({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        self._markets: Dict[str, Any] = {}

    def normalize_symbol(self, common: str) -> str:
        if "/" in common:
            return common
        key = common.upper().replace("-", "").replace("_", "").replace(":", "").replace("/", "")
        for s in self._markets.keys():
            if s.replace("/", "").upper() == key:
                return s
        if common.upper().endswith("USDT"):
            return f"{common[:-4]}/USDT"
        return common

    def _m(self, symbol: str) -> Dict[str, Any]:
        sym = self.normalize_symbol(symbol)
        m = self._markets.get(sym)
        if not m:
            raise RuntimeError(f"markets not loaded or symbol not found: {sym}")
        return m

    def lot_size(self, symbol: str) -> float:
        m = self._m(symbol)
        step = m.get("limits", {}).get("amount", {}).get("min") or m.get("precision", {}).get("amount")
        return float(step or 0.000001)

    def price_step(self, symbol: str) -> float:
        m = self._m(symbol)
        p = m.get("precision", {}).get("price")
        if isinstance(p, int):
            return 10 ** (-p)
        return float(p or 0.01)

    def min_notional(self, symbol: str) -> float:
        m = self._m(symbol)
        cost = m.get("limits", {}).get("cost", {}).get("min")
        return float(cost or 0.0)

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        return await self.x.fetch_ticker(self.normalize_symbol(symbol))

    async def get_orderbook(self, symbol: str) -> Dict[str, Any]:
        return await self.x.fetch_order_book(self.normalize_symbol(symbol), limit=25)

    async def get_balance(self) -> Dict[str, float]:
        b = await self.x.fetch_balance()
        total = b.get("total", {})
        return {k: float(v) for k, v in total.items()}

    async def create_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        amt = self.normalize_amount(symbol, amount)
        return await self.x.create_order(self.normalize_symbol(symbol), "market", side, amt)

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        await self.x.cancel_order(order_id, self.normalize_symbol(symbol))

    async def close(self) -> None:
        await self.x.close()

    async def __aenter__(self) -> "GateClient":
        await self.x.load_markets()
        self._markets = self.x.markets
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
