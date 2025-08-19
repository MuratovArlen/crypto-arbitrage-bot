from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

CSV_PATH = Path("trades.csv")

HEADER = "ts,symbol,direction,amount,price_buy,price_sell,fee_buy,fee_sell,pnl\n"

def ensure_file() -> None:
    if not CSV_PATH.exists():
        CSV_PATH.write_text(HEADER, encoding="utf-8")

def append_trade(row: Dict[str, Any]) -> None:
    ensure_file()
    line = ",".join([
        row["ts"],
        row["symbol"],
        row["direction"],
        f'{row["amount"]}',
        f'{row["price_buy"]}',
        f'{row["price_sell"]}',
        f'{row.get("fee_buy", 0)}',
        f'{row.get("fee_sell", 0)}',
        f'{row.get("pnl", 0)}',
    ]) + "\n"
    with CSV_PATH.open("a", encoding="utf-8") as f:
        f.write(line)

def read_last_trades(limit: int = 50) -> List[Dict[str, Any]]:
    ensure_file()
    rows = []
    with CSV_PATH.open("r", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    if len(lines) <= 1:
        return []
    head = lines[0].split(",")
    data = lines[1:]
    for line in data[-limit:]:
        parts = line.split(",")
        if len(parts) != len(head):
            continue
        rows.append({
            "ts": parts[0],
            "symbol": parts[1],
            "direction": parts[2],
            "amount": float(parts[3]),
            "price_buy": float(parts[4]),
            "price_sell": float(parts[5]),
            "fee_buy": float(parts[6]),
            "fee_sell": float(parts[7]),
            "pnl": float(parts[8]),
        })
    return rows[::-1]

def pnl_summary(limit: int | None = None):
    rows = read_last_trades(limit=limit or 10_000)
    total = 0.0
    by_symbol = defaultdict(float)
    for r in rows:
        total += r["pnl"]
        by_symbol[r["symbol"]] += r["pnl"]
    return {"total": round(total, 6),
            "by_symbol": {k: round(v, 6) for k, v in by_symbol.items()},
            "count": len(rows)}
