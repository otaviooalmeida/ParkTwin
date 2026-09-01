.PHONY: install install-dev test lint check frontend-build

install:
	python -m pip install -r requirements.txt

install-dev:
	python -m pip install -r requirements-dev.txt

test:
	pytest --cov=src --cov-report=term-missing --cov-fail-under=75

lint:
	ruff format --check src scripts tests
	ruff check src scripts tests

frontend-build:
	cd frontend && npm ci && npm audit --audit-level=moderate && npm run build

check: lint test frontend-build
