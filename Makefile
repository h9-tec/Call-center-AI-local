# Makefile for Call Center AI Local

.PHONY: help install install-dev test lint format clean run run-dev build deploy

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean cache and temp files"
	@echo "  make run          - Run application"
	@echo "  make run-dev      - Run in development mode"
	@echo "  make build        - Build Docker image"
	@echo "  make deploy       - Deploy to production"

# Installation
install:
	pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt
	pip install -r requirements-prod.txt

install-dev: install
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v

test-performance:
	locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 30s

# Code quality
lint:
	black --check app/ tests/
	flake8 app/ tests/
	mypy app/
	bandit -r app/ -ll
	safety check

format:
	black app/ tests/
	isort app/ tests/

# Cleaning
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

# Running
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

run-dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

run-prod:
	gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Docker
build:
	docker build -t call-center-ai:latest -f deployments/docker/Dockerfile .

build-prod:
	docker build -t call-center-ai:latest --target runtime -f deployments/docker/Dockerfile .

run-docker:
	docker-compose -f deployments/docker/docker-compose.yml up

run-docker-prod:
	docker-compose -f deployments/docker/docker-compose.prod.yml up -d

stop-docker:
	docker-compose -f deployments/docker/docker-compose.yml down

# Database
db-init:
	python scripts/database/init_db.py

db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

db-reset: db-rollback db-migrate

# Monitoring
monitoring-up:
	docker-compose -f monitoring/docker-compose.monitoring.yml up -d

monitoring-down:
	docker-compose -f monitoring/docker-compose.monitoring.yml down

# Deployment
deploy-staging:
	./scripts/deployment/deploy.sh staging

deploy-production:
	./scripts/deployment/deploy.sh production

rollback:
	./scripts/deployment/rollback.sh

# Development helpers
shell:
	python -i -c "from app.main import app; from app.core.config import settings"

docs:
	mkdocs serve

docs-build:
	mkdocs build

# Security
security-scan:
	trivy image call-center-ai:latest
	grype call-center-ai:latest

generate-secrets:
	python -c "import secrets; print(f'SECRET_KEY={secrets.token_urlsafe(32)}')"
	python -c "import secrets; print(f'JWT_SECRET_KEY={secrets.token_urlsafe(32)}')"

# Performance
profile:
	py-spy record -o profile.svg -- python -m uvicorn app.main:app

benchmark:
	python -m pytest tests/performance/ -v --benchmark-only
