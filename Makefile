# Makefile
.PHONY: run test lint fmt type docker-build docker-up docker-down kill-8000

PYTHONPATH ?= .

run:
	python main.py

test:
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q

lint:
	ruff check .

fmt:
	ruff format .

type:
	mypy .

docker-build:
	docker compose build

docker-up:
	docker compose up

docker-down:
	docker compose down

kill-8000:
	sudo fuser -k 8000/tcp || true
