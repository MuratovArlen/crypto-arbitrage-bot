from engine.signals import calc_spread, SpreadInput

def test_calc_spread_basic():
    r1, r2 = calc_spread(SpreadInput(
        bid_a=100, ask_a=101,
        bid_b=102, ask_b=103,
        taker_fee_bps=10,
        slippage_bps=10,
    ))
    assert r1.spread_bps > 0
