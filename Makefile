# TECHNOVA OS — developer shortcuts
.PHONY: help install backend frontend build test migrate revision seed lint clean

help:
	@echo "TECHNOVA OS — common tasks:"
	@echo "  make install    Install backend + frontend dependencies"
	@echo "  make backend    Run the API (dev, autoreload) on :8000"
	@echo "  make frontend   Run the Vite dev server on :5173"
	@echo "  make build      Build the frontend and copy it into the backend"
	@echo "  make test       Run the backend test suite"
	@echo "  make migrate    Apply database migrations (alembic upgrade head)"
	@echo "  make revision m='msg'  Autogenerate a new migration"
	@echo "  make clean      Remove caches and build artifacts"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm ci

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build
	rm -rf backend/frontend_dist && cp -r frontend/dist backend/frontend_dist

test:
	cd backend && python -m pytest -q

migrate:
	cd backend && alembic upgrade head

revision:
	cd backend && alembic revision --autogenerate -m "$(m)"

seed:
	cd backend && python -c "from app.seed import seed; seed(reset=True)"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist backend/frontend_dist
