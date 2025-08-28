# Arbitrage Bot: Bybit ↔ Gate + News HFT (Bithumb, demo)

## Цель
- **Арбитражный хедж** между Bybit и Gate: забираем спред с минимальным рыночным риском.
- **News HFT (Bithumb, demo)**: парсим новости, симулируем сделку по сигналу (эндпоинт `/simulate_news`).

## Режимы
- `DRY_RUN=true` — по умолчанию, без реальных ордеров (исполнение симулируется).
- `DRY_RUN=false` — боевой режим (включать только осознанно, при наличии ключей и лимитов!).

---

## Установка и запуск (локально)

```bash
git clone https://github.com/MuratovArlen/crypto-arbitrage-bot.git
cd <REPO>

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# отредактируй .env: ключи, пары, порог спреда и т.п.

# тесты
PYTHONPATH=. python -m pytest -q

# запуск
python main.py


Запуск в Docker  
• docker compose up --build
