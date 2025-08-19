from __future__ import annotations
from typing import List, Tuple

def enough_depth(orderbook: dict, side: str, amount: float, limit_px: float) -> bool:
    """
    Проверяем, что кумулятивная глубина до защитной цены покрывает объем.
    side='buy' -> идём по asks <= limit_px
    side='sell'-> идём по bids >= limit_px
    """
    if side == "buy":
        levels: List[Tuple[float, float]] = orderbook["asks"]
        total = 0.0
        for px, qty in levels:
            if float(px) <= limit_px:
                total += float(qty)
                if total >= amount:
                    return True
            else:
                break
        return False
    else:
        levels = orderbook["bids"]
        total = 0.0
        for px, qty in levels:
            if float(px) >= limit_px:
                total += float(qty)
                if total >= amount:
                    return True
            else:
                break
        return False

def banded_limit(best_px: float, bps: int, side: str) -> float:
    """
    Строим лимитную «рыночную» цену с бэндом в bps.
    buy: лимит = best_ask * (1 + bps/10000)
    sell: лимит = best_bid * (1 - bps/10000)
    """
    k = 1.0 + (bps / 10000.0)
    if side == "buy":
        return best_px * k
    return best_px / k
