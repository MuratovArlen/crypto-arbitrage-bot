from pathlib import Path
from datetime import datetime
import csv, json

FILE = Path("storage/open_positions.csv")
HEADERS = ["symbol","amount","price_buy","ts_open","meta_json"]

def _ensure_file():
    FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        with FILE.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()

def save_open_position(*, symbol: str, amount: float, price_open: float,
                       tp_price: float | None = None, sl_price: float | None = None) -> str:
    """Сохраняет открытую позицию и возвращает ts_open"""
    _ensure_file()
    ts_open = datetime.utcnow().isoformat()
    meta = {}
    if tp_price is not None: meta["tp_price"] = tp_price
    if sl_price is not None: meta["sl_price"] = sl_price
    row = {
        "symbol": symbol,
        "amount": str(amount),
        "price_buy": str(price_open),
        "ts_open": ts_open,
        "meta_json": json.dumps(meta, ensure_ascii=False),
    }
    with FILE.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=HEADERS).writerow(row)
    return ts_open

def list_open_positions(symbol: str | None = None):
    _ensure_file()
    out = []
    with FILE.open("r", newline="") as f:
        for row in csv.DictReader(f):
            if symbol and row["symbol"] != symbol:
                continue
            out.append(row)
    return out

def find_open_position(symbol: str):
    items = list_open_positions(symbol)
    return items[0] if items else None

def close_position(symbol: str):
    _ensure_file()
    rows = list_open_positions(None)
    rows = [r for r in rows if r["symbol"] != symbol]
    with FILE.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS); w.writeheader(); w.writerows(rows)
