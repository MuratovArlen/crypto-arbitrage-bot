import sqlite3
from pathlib import Path
from typing import Any, Dict

DB_PATH = Path("trades.sqlite")

DDL = """
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  symbol TEXT NOT NULL,
  direction TEXT NOT NULL,
  amount REAL NOT NULL,
  price_buy REAL NOT NULL,
  price_sell REAL NOT NULL,
  fee_buy REAL DEFAULT 0,
  fee_sell REAL DEFAULT 0,
  pnl REAL DEFAULT 0
);
"""

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(DDL)
    return conn

def insert_trade(row: Dict[str, Any]) -> None:
    with get_conn() as c:
        c.execute(
            """INSERT INTO trades
               (ts, symbol, direction, amount, price_buy, price_sell, fee_buy, fee_sell, pnl)
               VALUES (:ts, :symbol, :direction, :amount, :price_buy, :price_sell, :fee_buy, :fee_sell, :pnl)
            """,
            row,
        )

def export_csv(path: str = "trades.csv") -> str:
    with get_conn() as c, open(path, "w", encoding="utf-8") as f:
        cur = c.execute("SELECT * FROM trades ORDER BY id DESC")
        cols = [d[0] for d in cur.description]
        f.write(",".join(cols) + "\n")
        for r in cur:
            f.write(",".join(map(str, r)) + "\n")
    return path
