import math

from aiohttp import web
from typing import Any, Dict
from datetime import datetime
from exchanges.bithumb import BithumbClient
from engine.executor import Executor
from storage.journal_csv import append_trade, read_last_trades, pnl_summary
from storage.positions_csv import save_open_position, list_open_positions, find_open_position, close_position
from utils import news_parser


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
    return web.json_response({"ok": True, "see": [
        "/metrics", "/trades?limit=20", "/pnl",
        "/simulate_news", "/positions", "/close_position",
        "/hedge_sim_open", "/news_token", 
        ]})

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
    symbol = request.query.get("symbol")  # опционально: фильтр по символу
    sort = (request.query.get("sort") or "ts_desc").lower()

    items = read_last_trades(limit=limit)

    if symbol:
        items = [r for r in items if r["symbol"] == symbol]

    keymap = {
        "ts": lambda r: r["ts"],
        "pnl": lambda r: r["pnl"],
        "price_buy": lambda r: r["price_buy"],
        "price_sell": lambda r: r["price_sell"],
    }
    reverse = sort.endswith("_desc")
    base = sort.split("_")[0]
    key = keymap.get(base, keymap["ts"])

    items = sorted(items, key=key, reverse=reverse)
    return web.json_response({"count": len(items), "items": items})


async def handle_pnl(request: web.Request) -> web.Response:
    data = pnl_summary()
    order = (request.query.get("sort") or "").lower()  # asc|desc
    if order in ("asc","desc"):
        pairs = sorted(data["by_symbol"].items(), key=lambda kv: kv[1], reverse=(order=="desc"))
        data["by_symbol"] = {k: v for k, v in pairs}
    return web.json_response(data)


def build_app(state: State, settings=None) -> web.Application:
    app = web.Application()
    app["state"] = state
    app["settings"] = settings
    app.router.add_get("/", handle_root)
    app.router.add_get("/pnl", handle_pnl)
    app.router.add_get("/trades", handle_trades)
    app.router.add_get("/metrics", handle_metrics)
    app.router.add_get("/positions", handle_positions)
    app.router.add_get("/news_token", handle_news_token)
    app.router.add_get("/simulate_news", handle_simulate_news)
    app.router.add_get("/hedge_sim_open", handle_hedge_sim_open)
    app.router.add_get("/close_position", handle_close_position_get)
    return app


async def run_http(state: State, host: str = "0.0.0.0", port: int = 8000, settings=None) -> None:
    app = build_app(state, settings=settings)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()


async def handle_news_token(request: web.Request) -> web.Response:
    try:
        window = int(request.query.get("window", "80"))
        res = await news_parser.find_latest_token(max_ahead=window)
        return web.json_response(res, status=200 if res.get("ok") else 404)
    except Exception as e:
        request.app["state"].last_error = f"/news_token: {e}"
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_hedge_sim_open(request: web.Request) -> web.Response:
    try:
        symbol = request.query.get("symbol") or "TAC/USDT"
        budget = float(request.query.get("budget") or 1000)
        spot_px = float(request.query.get("spot_px") or 1.0)
        perp_px = float(request.query.get("perp_px") or spot_px)
        f8h = float(request.query.get("funding_8h") or 0.0001)
        from hedge.strategy import simulate_open
        res = simulate_open(symbol, budget, spot_px, perp_px, f8h)
        return web.json_response(res)
    except Exception as e:
        request.app["state"].last_error = f"/hedge_sim_open: {e}"
        return web.json_response({"ok": False, "error": str(e)}, status=400)


async def handle_positions(request: web.Request) -> web.Response:
    try:
        symbol = request.query.get("symbol")
        items = list_open_positions(symbol=symbol)
        return web.json_response({"ok": True, "count": len(items), "items": items})
    except Exception as e:
        request.app["state"].last_error = f"/positions: {e}"
        return web.json_response({"ok": False, "error": str(e)}, status=500)


def _pnl(px_buy, px_sell, amount): return (px_sell - px_buy) * amount

async def handle_close_position_get(request: web.Request) -> web.Response:
    symbol = request.query.get("symbol")
    price  = request.query.get("price")
    if not symbol or not price:
        return web.json_response({"ok": False, "error": "need symbol & price"}, status=400)
    try:
        px = float(price)
    except ValueError:
        return web.json_response({"ok": False, "error": "bad price"}, status=400)

    pos = find_open_position(symbol)
    if not pos:
        return web.json_response({"ok": False, "error": f"no open position for {symbol}"}, status=404)

    amount  = float(pos["amount"])
    px_buy  = float(pos["price_buy"])
    pnl     = _pnl(px_buy, px, amount)

    close_position(symbol)
    append_trade({
        "ts": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "direction": "news_long_close",
        "amount": amount,
        "price_buy": px_buy,
        "price_sell": px,
        "fee_buy": 0,
        "fee_sell": 0,
        "pnl": pnl,
    })
    st: State = request.app["state"]
    st.total_trades += 1
    st.success_trades += 1
    return web.json_response({"ok": True, "symbol": symbol, "price_sell": px, "pnl": pnl})


async def handle_simulate_news(request: web.Request) -> web.Response:
    """
    Демка News HFT (dry-run/офлайн фолбэк):
      /simulate_news?ticker=BTC&quote=KRW&budget=5000000&mode=smart&tp_bps=20&sl_bps=30&min_arb_bps=5
    Режимы:
      - instant: buy@ask -> sell@bid
      - smart:   cross-exch. arb, иначе TP/SL, иначе открыть
      - hold:    просто открыть
    """
    st: State = request.app["state"]
    s = request.app["settings"]

    if not getattr(s, "dry_run", True):
        return web.json_response({"ok": False, "error": "only allowed in DRY_RUN"}, status=400)

    ticker = (request.query.get("ticker") or "BTC").upper()
    quote  = (request.query.get("quote") or getattr(s, "hft_quote", "KRW")).upper()
    budget = float(request.query.get("budget") or getattr(s, "hft_budget_quote", 100000.0))
    mode   = (request.query.get("mode") or "instant").lower()
    tp_bps = float(request.query.get("tp_bps") or 15)
    sl_bps = float(request.query.get("sl_bps") or 25)
    min_arb_bps = float(request.query.get("min_arb_bps") or 5)  # оставил для совместимости

    try:
        # --- безопасные ключи + оффлайн ---
        api_key = getattr(s, "bithumb_api_key", "") or ""
        api_secret = getattr(s, "bithumb_api_secret", "") or ""

        bh = None
        sym = f"{ticker}/{quote}"
        bid = ask = None
        m: Dict[str, Any] = {}

        if api_key or api_secret:
            async with BithumbClient(api_key, api_secret) as bh_client:
                bh = bh_client
                sym = choose_symbol_on_bithumb(bh, ticker, quote)
                ob = await bh.get_orderbook(sym)
                bid = float(ob["bids"][0][0])
                ask = float(ob["asks"][0][0])
                m = getattr(bh, "_markets", {}).get(sym, {}) or {}
        else:
            ask = 158_800_000.0
            bid = 158_780_000.0

        limits  = (m.get("limits") or {})
        amt_lim = (limits.get("amount") or {})
        cost_lim= (limits.get("cost") or {})

        min_amt = float(amt_lim.get("min") or 0.0)
        step    = amt_lim.get("step")
        prec    = (m.get("precision") or {}).get("amount")
        min_cost= float(cost_lim.get("min") or 0.0)

        eff_quote = max(float(budget), min_cost)
        raw = eff_quote / ask
        if step:
            amount = math.floor(raw / step) * step
        elif prec is not None:
            q = 10 ** int(prec)
            amount = math.floor(raw * q) / q
        else:
            amount = math.floor(raw * 1e6) / 1e6

        if amount <= 0 or amount < min_amt:
            need_quote_for_amount = (min_amt * ask) if min_amt > 0 else 0.0
            need_quote = max(min_cost, need_quote_for_amount)
            return web.json_response({
                "ok": False, "error": f"amount too small (min {min_amt}, got {amount})",
                "symbol": sym, "quote": quote, "ask": ask,
                "budget_quote": budget, "min_amount": min_amt,
                "min_notional": min_cost, "suggest_budget": need_quote,
            }, status=400)

        execu = Executor(bh, bh, dry_run=True) if bh is not None else None

        if mode == "instant":
            if execu is not None:
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
                "mode": mode,
                "ticker": ticker,
                "symbol": sym,
                "quote": quote,
                "budget_quote": budget,
                "amount": amount,
                "price_buy": ask,
                "price_sell": bid,
                "pnl": pnl,
                "note": "instant = проверка цепочки; прибыль не цель",
            })


        elif mode == "smart":
            tp_price = ask * (1.0 + tp_bps / 10_000.0)
            sl_price = ask * (1.0 - sl_bps / 10_000.0)
            ts_open = datetime.utcnow().isoformat()
            save_open_position(
                symbol=sym,
                amount=amount,
                price_open=ask,
                tp_price=tp_price,
                sl_price=sl_price,
                ts_open=ts_open,
                meta={"tp_bps": tp_bps, "sl_bps": sl_bps},
            )

            if bid >= tp_price:
                pnl = (bid - ask) * amount
                append_trade({
                    "ts": datetime.utcnow().isoformat(),
                    "symbol": sym, "direction": "news_long_tp",
                    "amount": amount, "price_buy": ask, "price_sell": bid,
                    "fee_buy": 0, "fee_sell": 0, "pnl": pnl,
                })
                st.total_trades += 1; st.success_trades += 1
                return web.json_response({
                    "ok": True, "mode": mode, "hit": "tp", "ticker": ticker, "symbol": sym,
                    "quote": quote, "budget_quote": budget, "amount": amount,
                    "price_buy": ask, "price_sell": bid, "pnl": pnl,
                })

            if bid <= sl_price:
                pnl = (bid - ask) * amount
                append_trade({
                    "ts": datetime.utcnow().isoformat(),
                    "symbol": sym, "direction": "news_long_sl",
                    "amount": amount, "price_buy": ask, "price_sell": bid,
                    "fee_buy": 0, "fee_sell": 0, "pnl": pnl,
                })
                st.total_trades += 1; st.success_trades += 1
                return web.json_response({
                    "ok": True, "mode": mode, "hit": "sl", "ticker": ticker, "symbol": sym,
                    "quote": quote, "budget_quote": budget, "amount": amount,
                    "price_buy": ask, "price_sell": bid, "pnl": pnl,
                })
            # Gate
            best_ex = None
            best_bid2 = -1.0

            try:
                from exchanges.gate import GateClient
                async with GateClient(getattr(s, "gate_api_key", ""), getattr(s, "gate_api_secret", "")) as ex2:
                    ob2 = await ex2.get_orderbook(sym)
                    bid2 = float(ob2["bids"][0][0])
                    if bid2 > best_bid2:
                        best_bid2, best_ex = bid2, "gate"
            except Exception:
                pass

            # Bybit
            try:
                from exchanges.bybit import BybitClient
                async with BybitClient(getattr(s, "bybit_api_key", ""), getattr(s, "bybit_api_secret", "")) as ex2:
                    ob2 = await ex2.get_orderbook(sym)
                    bid2 = float(ob2["bids"][0][0])
                    if bid2 > best_bid2:
                        best_bid2, best_ex = bid2, "bybit"
            except Exception:
                pass

            if best_ex is not None and best_bid2 > 0:
                arb_bps = (best_bid2 / ask - 1.0) * 10_000.0
                if arb_bps >= min_arb_bps:
                    pnl = (best_bid2 - ask) * amount
                    append_trade({
                        "ts": datetime.utcnow().isoformat(),
                        "symbol": sym,
                        "direction": f"arb_bithumb_to_{best_ex}",
                        "amount": amount,
                        "price_buy": ask,
                        "price_sell": best_bid2,
                        "fee_buy": 0,
                        "fee_sell": 0,
                        "pnl": pnl,
                    })
                    st.total_trades += 1
                    st.success_trades += 1
                    return web.json_response({
                        "ok": True, "mode": mode, "sell_ex": best_ex,
                        "ticker": ticker, "symbol": sym, "quote": quote,
                        "budget_quote": budget, "amount": amount,
                        "price_buy": ask, "price_sell": best_bid2,
                        "arb_bps": arb_bps, "pnl": pnl,
                        "note": "кросс-биржевой арбитраж (dry-run фиксация)",
                    })

            # TP/SL прямо сейчас на Bithumb
            tp_price = ask * (1.0 + tp_bps / 10_000.0)
            sl_price = ask * (1.0 - sl_bps / 10_000.0)

            if bid >= tp_price:
                pnl = (bid - ask) * amount
                append_trade({
                    "ts": datetime.utcnow().isoformat(),
                    "symbol": sym,
                    "direction": "news_long_tp",
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
                    "ok": True, "mode": mode, "hit": "tp",
                    "ticker": ticker, "symbol": sym, "quote": quote,
                    "budget_quote": budget, "amount": amount,
                    "price_buy": ask, "price_sell": bid, "pnl": pnl,
                })

            if bid <= sl_price:
                pnl = (bid - ask) * amount
                append_trade({
                    "ts": datetime.utcnow().isoformat(),
                    "symbol": sym,
                    "direction": "news_long_sl",
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
                    "ok": True, "mode": mode, "hit": "sl",
                    "ticker": ticker, "symbol": sym, "quote": quote,
                    "budget_quote": budget, "amount": amount,
                    "price_buy": ask, "price_sell": bid, "pnl": pnl,
                })

            ts_open = datetime.utcnow().isoformat()
            save_open_position(
                symbol=sym, amount=amount, price_buy=ask, ts_open=ts_open,
                meta={"tp_bps": tp_bps, "sl_bps": sl_bps},
            )
            append_trade({
                "ts": ts_open, "symbol": sym, "direction": "news_long_open",
                "amount": amount, "price_buy": ask, "price_sell": 0,
                "fee_buy": 0, "fee_sell": 0, "pnl": 0,
            })
            st.total_trades += 1; st.success_trades += 1
            unrealized = (bid - ask) * amount
            return web.json_response({
                "ok": True, "mode": mode, "ticker": ticker, "symbol": sym, "quote": quote,
                "budget_quote": budget, "amount": amount,
                "price_buy": ask, "current_bid": bid, "unrealized": unrealized,
                "tp_bps": tp_bps, "sl_bps": sl_bps, "tp_price": tp_price, "sl_price": sl_price,
                "ts_open": ts_open, "note": "арбитража нет; позиция открыта (логически)",
            })

        elif mode == "hold":
            tp_price = ask * (1.0 + tp_bps / 10_000.0)
            sl_price = ask * (1.0 - sl_bps / 10_000.0)
            ts_open = datetime.utcnow().isoformat()

            save_open_position(
                symbol=sym,
                amount=amount,
                price_open=ask,
                tp_price=tp_price,
                sl_price=sl_price,
                ts_open=ts_open,
                meta={"tp_bps": tp_bps, "sl_bps": sl_bps},
            )
            append_trade({
                "ts": ts_open, "symbol": sym, "direction": "news_long_open",
                "amount": amount, "price_buy": ask, "price_sell": 0,
                "fee_buy": 0, "fee_sell": 0, "pnl": 0,
            })
            st.total_trades += 1; st.success_trades += 1
            unrealized = (bid - ask) * amount
            return web.json_response({
                "ok": True, "mode": mode, "ticker": ticker, "symbol": sym, "quote": quote,
                "budget_quote": budget, "amount": amount,
                "price_buy": ask, "current_bid": bid, "unrealized": unrealized,
                "tp_bps": tp_bps, "sl_bps": sl_bps, "tp_price": tp_price, "sl_price": sl_price,
                "ts_open": ts_open, "note": "позиция открыта (логически), продажа сейчас не выполнена",
            })

        else:
            return web.json_response({"ok": False, "error": f"unknown mode '{mode}'"}, status=400)

    except Exception as e:
        st.last_error = f"simulate_news: {e}"
        return web.json_response({"ok": False, "error": str(e)}, status=500)
