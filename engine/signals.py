from dataclasses import dataclass

@dataclass
class SpreadInput:
    bid_a: float
    ask_a: float
    bid_b: float
    ask_b: float
    taker_fee_bps: int
    slippage_bps: int

@dataclass
class SpreadResult:
    dir_name: str
    spread_bps: float
    ok: bool

def bps(x: float) -> float:
    return x * 10000.0

def calc_spread(inp: SpreadInput) -> tuple[SpreadResult, SpreadResult]:
    # вариант купить на a продать на b
    # эффективная покупка a с учетом slippage и fee
    buy_a = inp.ask_a * (1 + inp.slippage_bps / 10000.0)
    sell_b = inp.bid_b * (1 - inp.taker_fee_bps / 10000.0)
    s1 = bps((sell_b - buy_a) / buy_a)

    buy_b = inp.ask_b * (1 + inp.slippage_bps / 10000.0)
    sell_a = inp.bid_a * (1 - inp.taker_fee_bps / 10000.0)
    s2 = bps((sell_a - buy_b) / buy_b)

    r1 = SpreadResult("buy_a_sell_b", s1, False)
    r2 = SpreadResult("buy_b_sell_a", s2, False)
    return r1, r2
