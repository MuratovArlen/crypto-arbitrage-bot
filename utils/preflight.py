from __future__ import annotations
from typing import List, Tuple
import math

async def preflight(ex_a, ex_b, symbols: List[str]) -> Tuple[bool, str]:
    """
    Проверяем доступ к биржам, рынки, балансы, min_notional и шаги.
    Возвращаем (ok, message).
    """
    try:
        await ex_a.load_markets()
        await ex_b.load_markets()

        for ex in (ex_a, ex_b):
            _ = await ex.get_orderbook(symbols[0])

        problems = []
        for sym in symbols:
            a_min = ex_a.min_notional(sym) or 0.0
            b_min = ex_b.min_notional(sym) or 0.0
            if (a_min == 0.0) or (b_min == 0.0):
                problems.append(f"{sym}: min_notional unknown (check markets)")

            amt = 1.0
            if ex_a.normalize_amount(sym, amt) <= 0 or ex_b.normalize_amount(sym, amt) <= 0:
                problems.append(f"{sym}: lot step looks invalid")

        if problems:
            return False, " / ".join(problems)

        ba = await ex_a.get_balance()
        bb = await ex_b.get_balance()
        if not ba or not bb:
            return False, "balance fetch failed"

        return True, "ok"
    except Exception as e:
        return False, f"preflight error: {e}"
