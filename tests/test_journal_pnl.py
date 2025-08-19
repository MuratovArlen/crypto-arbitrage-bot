from storage.journal_csv import append_trade, pnl_summary


def test_pnl_summary_runs():
    append_trade({
        "ts": "2025-01-01T00:00:00",
        "symbol": "BTC/USDT",
        "direction": "test",
        "amount": 0.001,
        "price_buy": 100.0,
        "price_sell": 100.2,
        "fee_buy": 0,
        "fee_sell": 0,
        "pnl": 0.0002,
    })
    s = pnl_summary()
    assert "total" in s and "by_symbol" in s
