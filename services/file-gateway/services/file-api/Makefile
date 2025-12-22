.PHONY: help init dev test lint build upload clean

help:
	@echo "Available targets:"
	@echo "  init   - Install dependencies with uv"
	@echo "  dev    - Run service in development mode"
	@echo "  test   - Run tests"
	@echo "  lint   - Run linting (placeholder)"
	@echo "  build  - Build Docker image"
	@echo "  upload - Build and upload image to minikube"
	@echo "  clean  - Remove generated files"

init:
	uv sync

dev:
	uv run python -m file_api

test:
	uv run pytest

lint:
	@echo "Linting not configured yet"

build:
	docker build -t file-api:latest .

upload: build
	minikube image load file-api:latest

clean:
	rm -rf .venv
	rm -rf src/**/__pycache__
	rm -rf .pytest_cache
