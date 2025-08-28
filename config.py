# app/config.py
import json
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- основные поля проекта ---
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    gate_api_key: str = ""
    gate_api_secret: str = ""

    symbols: List[str] = []
    dry_run: bool = True

    spread_min_bps: int = 30
    slippage_bps: int = 10
    min_notional: float = 50.0
    max_order_usd: float = 100.0
    daily_limit_usd: float = 500.0

    antiflood_seconds: int = 30
    log_level: str = "INFO"
    stop_trading: bool = False
    demo_mode: bool = False
    metrics_port: int = 8000

    # --- HFT Bithumb ---
    hft_enabled: bool = False
    hft_poll_sec: int = 3
    hft_order_usd: float = 50.0
    hft_tickers_whitelist: List[str] = []
    bithumb_api_key: str = ""
    bithumb_api_secret: str = ""
    hft_quote: str = "KRW"
    hft_budget_quote: float = 100000
    news_source_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # поддержка двух форматов SYMBOLS в .env:
    # 1) JSON: '["BTC/USDT","ETH/USDT"]'
    # 2) список: 'BTC/USDT,ETH/USDT' или 'BTCUSDT,ETHUSDT'
    @field_validator("symbols", mode="before")
    @classmethod
    def _parse_symbols(cls, v):
        def _norm_one(s: str) -> str:
            s = s.strip().upper()
            if not s:
                return ""
            if "/" in s:
                return s
            if s.endswith("USDT"):
                return f"{s[:-4]}/USDT"
            if s.endswith("USDC"):
                return f"{s[:-4]}/USDC"
            return s

        if isinstance(v, list):
            return [x for x in (_norm_one(i) for i in v) if x]

        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                try:
                    arr = json.loads(v)
                    if isinstance(arr, list):
                        return [x for x in (_norm_one(i) for i in arr) if x]
                except Exception:
                    pass
            parts = [p for p in (p.strip() for p in v.split(",")) if p]
            return [x for x in (_norm_one(i) for i in parts) if x]

        return v

    @field_validator("hft_tickers_whitelist", mode="before")
    @classmethod
    def _parse_whitelist(cls, v):
        if isinstance(v, str):
            return [x.strip().upper() for x in v.split(",") if x.strip()]
        return v


def load_settings() -> Settings:
    return Settings()
