.PHONY: help install dev test lint clean

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make dev      - Run in development mode"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linter"
	@echo "  make clean    - Clean up generated files"

install:
	uv sync

dev:
	PYTHONPATH=src uv run python src/main.py

test:
	@echo "Running tests..."
	PYTHONPATH=src uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

