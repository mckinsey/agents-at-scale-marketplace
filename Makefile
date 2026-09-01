.DEFAULT_GOAL := help

# --git-common-dir, not --git-path hooks: the latter follows core.hooksPath.
HOOKS_DIR := $(shell git rev-parse --git-common-dir)/hooks
COMMIT_MSG_HOOK := $(HOOKS_DIR)/commit-msg

.PHONY: help
help: # HELP: show available targets
	@awk -F':.*# HELP: ' '/^[a-zA-Z0-9_.-]+:.*# HELP: /{printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: sign-off
sign-off: # HELP: install a commit hook that adds the DCO sign-off
	@test ! -e "$(COMMIT_MSG_HOOK)" || { \
		echo "$(COMMIT_MSG_HOOK) already exists; not overwriting it"; \
		exit 1; \
	}
	@mkdir -p "$(HOOKS_DIR)"
	@printf '%s\n' \
		'#!/bin/sh' \
		'name=$$(git config user.name)' \
		'email=$$(git config user.email)' \
		'test -n "$$name" -a -n "$$email" || { echo "Git user name and email are required" >&2; exit 1; }' \
		'git interpret-trailers --if-exists addIfDifferent --trailer "Signed-off-by: $$name <$$email>" --in-place "$$1"' \
		> "$(COMMIT_MSG_HOOK)"
	@chmod +x "$(COMMIT_MSG_HOOK)"
	@echo "Installed $(COMMIT_MSG_HOOK)"
	@hooks_path=$$(git config --get core.hooksPath); \
	if [ -n "$$hooks_path" ]; then \
		echo "Warning: core.hooksPath is set to $$hooks_path."; \
		echo "Git will run hooks from there; the sign-off hook takes effect only if that path delegates to $(HOOKS_DIR)."; \
	fi
