# Arbitrage Bot Bybit ↔ Gate плюс News HFT Bithumb "test"

## Цель
Хедж арбитраж между Bybit и Gate с минимальным рыночным риском.  
Дополнительно модуль News HFT для Bithumb реакция на листинги и новости.

## Режимы
• DRY_RUN без реальных ордеров по умолчанию  
• LIVE реальные ордера включается переменной DRY_RUN=false в окружении

---

## Установка и запуск

### Клонирование проекта
```bash
git clone https://github.com/<твой-логин>/<название-репозитория>.git
cd <название-репозитория>

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
