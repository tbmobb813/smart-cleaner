PYTHON ?= python3
VENV ?= .venv

.PHONY: dev-setup regen-constraints lint format test clean

dev-setup:
	# Create venv and install editable package + dev deps
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && $(PYTHON) -m pip install --upgrade pip && \
	. $(VENV)/bin/activate && pip install -e ".[dev]"

regen-constraints:
	# Regenerate pinned dev constraints (quick method)
	./scripts/regenerate-constraints.sh --quick --venv $(VENV)

lint:
	# Run ruff and black checks
	$(VENV)/bin/ruff check --line-length 120 src tests --output-format=github
	$(VENV)/bin/ruff format --check --line-length 120 src tests
	$(VENV)/bin/black --check --line-length 120 src tests

format:
	# Fix formatting locally
	$(VENV)/bin/ruff format --line-length 120 src tests || true
	$(VENV)/bin/black --line-length 120 src tests || true

test:
	PYTHONPATH=src $(VENV)/bin/pytest -v

clean:
	rm -rf $(VENV) .pytest_cache dist build *.egg-info requirements-dev-constraints.txt frozen.txt
