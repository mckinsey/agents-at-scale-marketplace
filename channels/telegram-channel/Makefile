-include .env
export

.PHONY: init dev test build help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

init: ## Install dependencies
	uv sync

dev: ## Run locally (needs TELEGRAM_BOT_TOKEN and kubeconfig)
	uv run python -m telegram_channel

test: ## Run tests
	uv run python -m pytest tests/ -v

build: ## Build Docker image
	docker build -t telegram-channel:latest .
