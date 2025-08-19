import asyncio
from datetime import datetime
from typing import List
from aiohttp import ClientSession

from exchanges.bithumb import BithumbClient
from engine.executor import Executor
from storage.journal_csv import append_trade
from .news import fetch_and_parse
from .strategy import decide_on_news


def choose_symbol_on_bithumb(bh: BithumbClient, base: str, preferred_quote: str) -> str:
    """
    Возвращает реальный торговый символ на Bithumb:
    1) пытаемся {BASE}/{preferred_quote}
    2) иначе берём любой маркет с таким BASE
    3) иначе кидаем ошибку
    """
    base = base.upper()
    preferred_quote = preferred_quote.upper()

    want = f"{base}/{preferred_quote}"
    if want in bh._markets:  # markets загружены в __aenter__
        return want

    for s, m in bh._markets.items():
        if (m.get("base") or "").upper() == base:
            return s

    raise RuntimeError(f"{bh.name} has no market for base {base}")


async def run_hft(settings, metrics_state) -> None:
    """
    Фоновая задача: опрашивает NEWS_SOURCE_URL, на позитивной новости
    делает dry-run сделку на Bithumb.
    """
    url = getattr(settings, "news_source_url", "") or ""
    if not url:
        return

    quote = getattr(settings, "hft_quote", "KRW").upper()
    whitelist: List[str] = [t.upper() for t in getattr(settings, "hft_tickers_whitelist", [])]

    async with BithumbClient(settings.bithumb_api_key, settings.bithumb_api_secret) as bh, \
               ClientSession() as http:

        execu = Executor(bh, bh, dry_run=settings.dry_run)  # buy & sell на одной бирже, dry-run

        while True:
            try:
                news = await fetch_and_parse(http, url)
                signal = decide_on_news(news, whitelist)

                if not signal:
                    await asyncio.sleep(settings.hft_poll_sec)
                    continue

                base = signal["ticker"].upper()
                sym = choose_symbol_on_bithumb(bh, base, quote)

                # цены рынка
                ob = await bh.get_orderbook(sym)
                bid = float(ob["bids"][0][0])
                ask = float(ob["asks"][0][0])

                usd = float(settings.hft_order_usd)
                amount = bh.normalize_amount(sym, usd / ask)
                if amount <= 0:
                    await asyncio.sleep(settings.hft_poll_sec)
                    continue

                # dry-run хедж на одной бирже
                await execu.market_hedge(sym, amount)

                # фиктивный pnl (как будто моментально закрылись по bid)
                pnl = (bid - ask) * amount
                append_trade({
                    "ts": datetime.utcnow().isoformat(),
                    "symbol": sym,
                    "direction": "news_long",
                    "amount": amount,
                    "price_buy": ask,
                    "price_sell": bid,
                    "fee_buy": 0,
                    "fee_sell": 0,
                    "pnl": pnl,
                })

                metrics_state.total_trades += 1
                metrics_state.success_trades += 1

            except Exception as e:
                metrics_state.last_error = f"hft: {e}"

            await asyncio.sleep(settings.hft_poll_sec)
