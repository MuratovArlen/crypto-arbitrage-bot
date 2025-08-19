import asyncio
import logging
from typing import Dict, Any
from exchanges.base import BaseExchange

log = logging.getLogger("executor")

class Executor:
    def __init__(self, ex_buy: BaseExchange, ex_sell: BaseExchange, dry_run: bool = True) -> None:
        self.ex_buy = ex_buy
        self.ex_sell = ex_sell
        self.dry_run = dry_run

    async def market_hedge(self, symbol: str, amount: float) -> Dict[str, Any]:
        if self.dry_run:
            log.info({"event": "dry_trade", "symbol": symbol, "amount": amount})
            return {"status": "dry", "symbol": symbol, "amount": amount}

        buy = asyncio.create_task(self.ex_buy.create_market_order(symbol, "buy", amount))
        sell = asyncio.create_task(self.ex_sell.create_market_order(symbol, "sell", amount))

        done, pending = await asyncio.wait({buy, sell}, timeout=5, return_when=asyncio.ALL_COMPLETED)

        if pending:
            for t in pending:
                t.cancel()
            log.warning("timeout on one leg")
        res_buy = buy.result() if buy.done() else {"error": "buy_timeout"}
        res_sell = sell.result() if sell.done() else {"error": "sell_timeout"}

        if "error" in res_buy and "id" in res_sell:
            await self.ex_sell.create_market_order(symbol, "buy", amount)
        if "error" in res_sell and "id" in res_buy:
            await self.ex_buy.create_market_order(symbol, "sell", amount)

        return {"buy": res_buy, "sell": res_sell}
