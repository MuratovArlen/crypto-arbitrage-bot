# scripts/demo_bot.py
import time
import json
import urllib.request
import urllib.parse

BASE = "http://127.0.0.1:8001"

def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    print("Demo-bot started. Press Ctrl+C to stop.")
    while True:
        try:
            # 1) «Новость» => открываем позицию (hold)
            js = get("/simulate_news?ticker=BTC&quote=KRW&budget=5000000&mode=hold")
            if not js.get("ok"):
                print("[OPEN ERR]", js)
                time.sleep(3)
                continue

            sym = js["symbol"]
            px_buy = js["price_buy"]
            print(f"[OPEN] {sym} buy={px_buy}")

            # 2) Проверим, что позиция появилась
            pos = get("/positions")
            print("[POSITIONS]", pos)

            # 3) Закроем позицию по +1%
            px_sell = px_buy * 1.01
            path = "/close_position?" + urllib.parse.urlencode({"symbol": sym, "price": px_sell})
            js2 = get(path)
            print(f"[CLOSE] {sym} sell={px_sell} ->", js2)

            # 4) Посмотрим журнал и pnl
            trades = get("/trades?limit=5&sort=pnl_desc")
            pnl = get("/pnl")
            print("[TRADES]", trades)
            print("[PNL]", pnl)

        except Exception as e:
            print("[ERROR]", e)

        time.sleep(5)

if __name__ == "__main__":
    main()
