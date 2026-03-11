.PHONY: up down logs test learn report install

install:
	pip install -e ".[dev]"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	python -m pytest tests/ -v

learn:
	python -m src.learning.loop

report:
	python -m src.learning.report

dev-api:
	uvicorn src.api.app:app --reload --port 8000

dev-worker:
	python -m src.workflow.worker
