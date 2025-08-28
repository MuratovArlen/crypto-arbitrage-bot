from pathlib import Path
import csv, json
from datetime import datetime

FILE = Path("storage/open_positions.csv")
HEADERS = ["symbol","amount","price_buy","tp_price","sl_price","ts_open","meta_json"]

def _ensure_file():
    FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        with FILE.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()

def save_open_position(
    symbol, amount,
    price_buy=None, *, price_open=None,
    tp_price=None, sl_price=None,
    ts_open=None, meta=None
):
    _ensure_file()
    # бэк-совместимость: если дали price_open — используем его
    if price_buy is None and price_open is not None:
        price_buy = price_open
    if price_buy is None:
        raise TypeError("save_open_position() needs price_buy (or price_open)")

    row = {
        "symbol": symbol,
        "amount": str(amount),
        "price_buy": str(price_buy),
        "tp_price": "" if tp_price is None else str(tp_price),
        "sl_price": "" if sl_price is None else str(sl_price),
        "ts_open": ts_open or datetime.utcnow().isoformat(),
        "meta_json": json.dumps(meta or {}, ensure_ascii=False),
    }
    with FILE.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=HEADERS).writerow(row)
    return row["ts_open"]

def list_open_positions(symbol=None):
    _ensure_file()
    out = []
    with FILE.open("r", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if symbol and row["symbol"] != symbol:
                continue
            out.append(row)
    return out

def find_open_position(symbol):
    items = list_open_positions(symbol)
    return items[0] if items else None

def close_position(symbol):
    _ensure_file()
    rows = list_open_positions(None)
    rows = [r for r in rows if r["symbol"] != symbol]
    with FILE.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        w.writerows(rows)
