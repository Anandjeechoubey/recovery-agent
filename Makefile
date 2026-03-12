.PHONY: up down logs test learn report install dev-api dev-frontend build-frontend

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

# Development: run API + embedded worker (backend)
dev-api:
	uvicorn src.api.app:app --reload --port 8000

# Development: run frontend dev server with hot reload
dev-frontend:
	cd frontend && npm run dev

# Build frontend for production
build-frontend:
	cd frontend && npm run build
