.PHONY: help install dev deploy test lint clean

NAMESPACE ?= ark-system

help:
	@echo "Available commands:"
	@echo "  make install  - Install python dependencies (uv sync)"
	@echo "  make dev      - devspace dev into $(NAMESPACE)"
	@echo "  make deploy   - devspace deploy into $(NAMESPACE)"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Type-check with pyright"
	@echo "  make clean    - Remove caches and build artifacts"

install:
	uv sync

# -n bypasses the default-namespace safety prompt; namespace is context state in
# devspace, so it can't be pinned in devspace.yaml itself.
dev:
	devspace dev -n $(NAMESPACE)

deploy:
	devspace deploy -n $(NAMESPACE)

test:
	uv run pytest tests/ -v

lint:
	uv run --extra dev pyright src

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
