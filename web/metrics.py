from aiohttp import web # type: ignore
from typing import Any, Dict

from datetime import datetime
from exchanges.bithumb import BithumbClient
from engine.executor import Executor
from storage.journal_csv import append_trade, read_last_trades, pnl_summary


def choose_symbol_on_bithumb(bh, base: str, preferred_quote: str) -> str:
    """
    Находит правильный символ на Bithumb:
    1) пробуем BASE/QUOTE
    2) иначе берём любой маркет с таким BASE
    """
    base = base.upper()
    preferred_quote = preferred_quote.upper()

    want = f"{base}/{preferred_quote}"
    if want in bh._markets:
        return want

    for s, m in bh._markets.items():
        if (m.get("base") or "").upper() == base:
            return s

    raise RuntimeError(f"{bh.name} has no market for base {base}")


class State:
    def __init__(self) -> None:
        self.total_trades = 0
        self.success_trades = 0
        self.avg_spread_bps = 0.0
        self.avg_execution_ms = 0.0
        self.last_error = ""

async def handle_root(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "see": ["/metrics", "/trades?limit=50", "/pnl"]})

async def handle_metrics(request: web.Request) -> web.Response:
    st: State = request.app["state"]
    data: Dict[str, Any] = {
        "total_trades": st.total_trades,
        "success_trades": st.success_trades,
        "avg_spread_bps": round(st.avg_spread_bps, 4),
        "avg_execution_ms": round(st.avg_execution_ms, 2),
        "last_error": st.last_error,
    }
    return web.json_response(data)

async def handle_trades(request: web.Request) -> web.Response:
    try:
        limit = int(request.query.get("limit", "50"))
    except ValueError:
        limit = 50
    data = read_last_trades(limit=limit)
    return web.json_response({"count": len(data), "items": data})

async def handle_pnl(request: web.Request) -> web.Response:
    data = pnl_summary()
    return web.json_response(data)

def build_app(state: State, settings=None) -> web.Application:
    app = web.Application()
    app["state"] = state
    app["settings"] = settings
    app.router.add_get("/", handle_root)
    app.router.add_get("/metrics", handle_metrics)
    app.router.add_get("/trades", handle_trades)
    app.router.add_get("/pnl", handle_pnl)
    app.router.add_get("/simulate_news", handle_simulate_news)
    return app


async def run_http(state: State, host: str = "0.0.0.0", port: int = 8000, settings=None) -> None:
    app = build_app(state, settings=settings)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()


async def handle_simulate_news(request: web.Request) -> web.Response:
    """
    Демка News-HFT: /simulate_news?ticker=BTC&text=listing
    Делает одну dry-run сделку на Bithumb.
    """
    st: State = request.app["state"]
    s = request.app["settings"]

    if not getattr(s, "dry_run", True):
        return web.json_response({"ok": False, "error": "only allowed in DRY_RUN"}, status=400)

    ticker = (request.query.get("ticker") or "BTC").upper()
    text = request.query.get("text") or "listing"
    quote = getattr(s, "hft_quote", "KRW")

    try:
        async with BithumbClient(s.bithumb_api_key, s.bithumb_api_secret) as bh:
            sym = choose_symbol_on_bithumb(bh, ticker, quote)

            ob = await bh.get_orderbook(sym)
            bid = float(ob["bids"][0][0])
            ask = float(ob["asks"][0][0])

            usd = float(getattr(s, "hft_order_usd", 50.0))
            amount = bh.normalize_amount(sym, usd / ask)
            if amount <= 0:
                return web.json_response({"ok": False, "error": "amount too small"}, status=400)

            execu = Executor(bh, bh, dry_run=True)
            await execu.market_hedge(sym, amount)

            pnl = (bid - ask) * amount
            append_trade({
                "ts": datetime.utcnow().isoformat(),
                "symbol": sym,
                "direction": "news_long_sim",
                "amount": amount,
                "price_buy": ask,
                "price_sell": bid,
                "fee_buy": 0,
                "fee_sell": 0,
                "pnl": pnl,
            })

            st.total_trades += 1
            st.success_trades += 1

            return web.json_response({
                "ok": True,
                "ticker": ticker,
                "text": text,
                "symbol": sym,
                "amount": amount,
                "price_buy": ask,
                "price_sell": bid,
                "pnl": pnl,
            })

    except Exception as e:
        st.last_error = f"simulate_news: {e}"
        return web.json_response({"ok": False, "error": str(e)}, status=500)
