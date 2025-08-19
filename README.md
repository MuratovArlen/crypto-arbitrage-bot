# Arbitrage Bot (Bybit ↔ Gate) + News-HFT (Bithumb)

## Цель
Хедж-арбитраж между Bybit и Gate: забирать ценовой спред с минимальным рыночным риском.  
Опционально — модуль News-HFT для Bithumb (реакция на листинги/новости).

## Режимы
- **DRY_RUN** — без реальных ордеров (по умолчанию).
- **LIVE** — реальные ордера, включается `DRY_RUN=false` (двойная защита в коде).

## Быстрый старт (локально)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить ключи/пары
python -m pytest -q
python main.py


Запуск в Docker  
• docker compose up --build

Переменные окружения  
• BYBIT_API_KEY BYBIT_API_SECRET  
• GATE_API_KEY GATE_API_SECRET  
• SYMBOLS через запятую, пример BTCUSDT ETHUSDT  
• DRY_RUN true или false  
• SPREAD_MIN_BPS  
• SLIPPAGE_BPS  
• MIN_NOTIONAL  
• MAX_ORDER_USD  
• DAILY_LIMIT_USD  
• LOG_LEVEL

Полезные команды  
• make run  
• make lint  
• make type  
• make test
