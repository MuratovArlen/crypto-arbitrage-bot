from engine.signals import calc_spread, SpreadInput

def test_signal_positive_when_sell_b_more_than_buy_a():
    r1, r2 = calc_spread(SpreadInput(
        bid_a=100.0,
        ask_a=101.0,
        bid_b=103.0,
        ask_b=104.0,
        taker_fee_bps=10,
        slippage_bps=10,
    ))
    assert r1.spread_bps > 0 or r2.spread_bps > 0
