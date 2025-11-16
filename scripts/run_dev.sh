#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
# Activate venv if present
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python -m smartcleaner
