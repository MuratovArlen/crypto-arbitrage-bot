from datetime import datetime
from pathlib import Path
import csv


HEDGE_CSV = Path("storage/hedges.csv")
HEDGE_HEADERS = [
    "ts","symbol","budget_usdt","spot_px","spot_qty",
    "perp_px","perp_qty","funding_8h","est_funding_apr","note"
]


def _ensure():
    HEDGE_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not HEDGE_CSV.exists():
        with HEDGE_CSV.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=HEDGE_HEADERS).writeheader()


def _apr_from_funding8h(f8h: float) -> float:
    return f8h * 3 * 365


def simulate_open(symbol: str, budget_usdt: float, spot_px: float, perp_px: float,
                  funding_8h: float = 0.0001, hedge_ratio: float = 1.0) -> dict:
    _ensure()
    spot_qty = budget_usdt / spot_px
    perp_qty = - hedge_ratio * (budget_usdt / perp_px)


    rec = {
        "ts": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "budget_usdt": budget_usdt,
        "spot_px": spot_px,
        "spot_qty": round(spot_qty, 6),
        "perp_px": perp_px,
        "perp_qty": round(perp_qty, 6),
        "funding_8h": funding_8h,
        "est_funding_apr": _apr_from_funding8h(funding_8h),
        "note": "dry-run hedge open",
    }
    with HEDGE_CSV.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=HEDGE_HEADERS).writerow(rec)
    return {"ok": True, "hedge": rec}
