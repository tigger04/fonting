# ABOUTME: Build targets for the gaelic-fonts collection.
# ABOUTME: Provides mark-gaelic, test, install, and sync targets.

VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

.PHONY: help venv mark-gaelic test clean sync

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: $(VENV)/bin/activate ## Create Python virtual environment

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

mark-gaelic: venv ## Mark all fonts with Gaelic metadata
	$(PYTHON) mark_gaelic.py .

test: venv ## Run tests
	$(PYTEST) test_mark_gaelic.py -v

clean: ## Remove virtual environment and caches
	rm -rf $(VENV) __pycache__ .pytest_cache

sync: ## Git add, commit, pull, push
	git add --all
	git commit -m "sync: update gaelic-fonts"
	git pull --rebase
	git push
