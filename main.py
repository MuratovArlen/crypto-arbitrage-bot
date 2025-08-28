import os
import asyncio
import uvloop
import logging
import signal
from datetime import datetime

from config import load_settings
from utils.log import setup_logging
from exchanges.bybit import BybitClient
from exchanges.gate import GateClient
from engine.signals import calc_spread, SpreadInput
from engine.executor import Executor
from engine.risk import AntiFlood, DailyLimitUsd
from storage.journal_csv import append_trade
from web.metrics import State, run_http
from hft_bithumb.runner import run_hft


async def trade_once(bybit: BybitClient, gate: GateClient, s, st: State,
                     af: AntiFlood, limit: DailyLimitUsd) -> None:
    for sym in s.symbols:
        try:
            ob_a = await bybit.get_orderbook(sym)
            ob_b = await gate.get_orderbook(sym)
            a_bid, a_ask = float(ob_a["bids"][0][0]), float(ob_a["asks"][0][0])
            b_bid, b_ask = float(ob_b["bids"][0][0]), float(ob_b["asks"][0][0])

            r1, r2 = calc_spread(SpreadInput(
                bid_a=a_bid, ask_a=a_ask,
                bid_b=b_bid, ask_b=b_ask,
                taker_fee_bps=10,
                slippage_bps=s.slippage_bps,
            ))

            st.avg_spread_bps = (st.avg_spread_bps * 0.9) + (max(r1.spread_bps, r2.spread_bps) * 0.1)

            target = None
            if r1.spread_bps >= s.spread_min_bps:
                target = ("buy_a_sell_b", bybit, gate, a_ask, b_bid)
            elif r2.spread_bps >= s.spread_min_bps:
                target = ("buy_b_sell_a", gate, bybit, b_ask, a_bid)

            if not target:
                if s.dry_run and getattr(s, "demo_mode", False):
                    target = ("buy_a_sell_b", bybit, gate, a_ask, a_ask * 1.0003)
                else:
                    continue


            usd = min(s.max_order_usd, s.daily_limit_usd)
            if not limit.can_spend(usd):
                continue

            dir_name, ex_buy, ex_sell, px_buy, px_sell = target

            min_cost_buy = ex_buy.min_notional(sym) or 0.0
            min_cost_sell = ex_sell.min_notional(sym) or 0.0
            usd_base = max(usd, min_cost_buy, min_cost_sell, s.min_notional)


            raw_amount = usd_base / px_buy

            amt_buy  = ex_buy.normalize_amount(sym,  raw_amount)
            amt_sell = ex_sell.normalize_amount(sym, raw_amount)

            amount = min(amt_buy, amt_sell)
            if amount <= 0:
                continue


            execu = Executor(ex_buy, ex_sell, dry_run=s.dry_run)

            t0 = asyncio.get_event_loop().time()
            await execu.market_hedge(sym, amount)
            t1 = asyncio.get_event_loop().time()
            st.avg_execution_ms = st.avg_execution_ms * 0.8 + (t1 - t0) * 1000.0 * 0.2


            pnl = (px_sell - px_buy) * amount
            append_trade({
                "ts": datetime.utcnow().isoformat(),
                "symbol": sym,
                "direction": dir_name,
                "amount": amount,
                "price_buy": px_buy,
                "price_sell": px_sell,
                "fee_buy": 0,
                "fee_sell": 0,
                "pnl": pnl,
            })

            st.total_trades += 1
            st.success_trades += 1
            limit.add(usd)

        except Exception as e:
            st.last_error = str(e)
            logging.getLogger("root").warning(f"trade loop error {e}")

async def main() -> None:
    s = load_settings()
    setup_logging(s.log_level)
    log = logging.getLogger("root")
    log.info("start")

    st = State()
    af = AntiFlood(seconds=getattr(s, "antiflood_seconds", 30))
    limit = DailyLimitUsd(limit_usd=s.daily_limit_usd)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    metrics_port = int(os.getenv("METRICS_PORT", getattr(s, "metrics_port", 8000)))
    http_task = asyncio.create_task(run_http(st, port=metrics_port, settings=s))

    hft_task = None
    if getattr(s, "hft_enabled", False):
        hft_task = asyncio.create_task(run_hft(s, st))

    async with BybitClient(s.bybit_api_key, s.bybit_api_secret) as bybit, \
               GateClient(s.gate_api_key, s.gate_api_secret) as gate:
        try:
            while not stop.is_set():
                if s.stop_trading:
                    await asyncio.sleep(1.0)
                    continue
                await trade_once(bybit, gate, s, st, af, limit)
                await asyncio.sleep(1.0)
        finally:
            if hft_task:
                hft_task.cancel()
                try:
                    await hft_task
                except asyncio.CancelledError:
                    pass

            http_task.cancel()
            try:
                await http_task
            except asyncio.CancelledError:
                pass
            log.info("stopped cleanly")

if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        pass
