import storage.journal_csv as jc
from pathlib import Path

def test_append_and_summary(tmp_path: Path):
    # перенаправим CSV в tmp
    old = jc.CSV_PATH
    try:
        jc.CSV_PATH = tmp_path / "trades.csv"

        # записываем 2 сделки
        jc.append_trade({
            "ts": "2025-01-01T00:00:00",
            "symbol": "BTC/USDT",
            "direction": "test",
            "amount": 0.01,
            "price_buy": 100.0,
            "price_sell": 100.5,
            "fee_buy": 0, "fee_sell": 0,
            "pnl": 0.005,
        })
        jc.append_trade({
            "ts": "2025-01-01T00:01:00",
            "symbol": "ETH/USDT",
            "direction": "test",
            "amount": 0.1,
            "price_buy": 10.0,
            "price_sell": 9.9,
            "fee_buy": 0, "fee_sell": 0,
            "pnl": -0.01,
        })

        # читаем последние и сводку
        rows = jc.read_last_trades(limit=10)
        s = jc.pnl_summary()

        assert len(rows) == 2
        assert abs(s["total"] - (-0.005)) < 1e-9
        assert "BTC/USDT" in s["by_symbol"]
        assert "ETH/USDT" in s["by_symbol"]
    finally:
        jc.CSV_PATH = old
