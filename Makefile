.PHONY: run test lint fmt type docker-build docker-up docker-down docker-logs kill-8000

PYTHONPATH ?= .

# Локальный запуск
run:
	PYTHONPATH=$(PYTHONPATH) python main.py

# Тесты
test:
	PYTHONPATH=$(PYTHONPATH) pytest -q

# Линтеры
lint:
	ruff check .

fmt:
	ruff format .

type:
	mypy .

# Docker
docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# Убить процессы на порту 8000 (если висят)
kill-8000:
	sudo fuser -k 8000/tcp || true
