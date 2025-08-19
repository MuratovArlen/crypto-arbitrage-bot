import asyncio
import logging
from typing import Tuple
from exchanges.base import BaseExchange, best_bid_ask

log = logging.getLogger("feeder")

async def fetch_pair(ex_a: BaseExchange, ex_b: BaseExchange, symbol: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    ob_a = await ex_a.get_orderbook(symbol)
    ob_b = await ex_b.get_orderbook(symbol)
    ba = best_bid_ask(ob_a)
    bb = best_bid_ask(ob_b)
    return ba, bb

async def stream_quotes(ex_a: BaseExchange, ex_b: BaseExchange, symbols: list[str], interval: float = 1.0):
    while True:
        for sym in symbols:
            try:
                a, b = await fetch_pair(ex_a, ex_b, sym)
                log.info({"symbol": sym, "a_bid": a[0], "a_ask": a[1], "b_bid": b[0], "b_ask": b[1]})
            except Exception as e:
                log.warning(f"quote error {sym} {e}")
        await asyncio.sleep(interval)
