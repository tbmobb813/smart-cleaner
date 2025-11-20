#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: regenerate-constraints.sh [--quick|--pip-compile] [--venv PATH]

Options:
  --quick         Quick method: create venv, install dev extras, pip freeze & filter
  --pip-compile   Recommended: use pip-tools (requires a requirements-dev.in file)
  --venv PATH     Path to venv to use/create (default: .venv)

Examples:
  ./scripts/regenerate-constraints.sh --quick
  ./scripts/regenerate-constraints.sh --pip-compile --venv .venv
USAGE
}

MODE=quick
VENV=.venv

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)
      MODE=quick
      shift
      ;;
    --pip-compile)
      MODE=pip-compile
      shift
      ;;
    --venv)
      VENV=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      usage
      exit 2
      ;;
  esac
done

echo "Using venv: $VENV"

if [ "$MODE" = "quick" ]; then
  echo "Running quick regenerate via pip freeze..."
  if [ ! -d "$VENV" ]; then
    python -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
  python -m pip install --upgrade pip
  echo "Installing dev extras (editable)"
  pip install -e ".[dev]"

  echo "Generating requirements-dev-constraints.txt (filtered)..."
  pip freeze | grep -E '^(black|ruff|mypy|pre-commit|pytest|pytest-cov|pytest-mock|click|tomli|tomli_w|tomlkit|rich|packaging)' > requirements-dev-constraints.txt

  echo "Done. Written requirements-dev-constraints.txt"
  deactivate || true
  exit 0
fi

if [ "$MODE" = "pip-compile" ]; then
  echo "Running pip-compile method..."
  if [ ! -f requirements-dev.in ]; then
    echo "ERROR: requirements-dev.in not found. Create it with top-level dev tools (one per line)."
    exit 2
  fi
  if [ ! -d "$VENV" ]; then
    python -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
  python -m pip install --upgrade pip
  pip install pip-tools
  pip-compile --output-file=requirements-dev-constraints.txt requirements-dev.in
  echo "Done. Written requirements-dev-constraints.txt via pip-compile"
  deactivate || true
  exit 0
fi

echo "Unknown mode: $MODE"
usage
exit 2
