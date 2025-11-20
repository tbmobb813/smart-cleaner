#!/usr/bin/env bash
set -euo pipefail

# Prototype bubblewrap wrapper: run a plugin worker inside bubblewrap (bwrap)
# Falls back to normal subprocess if bwrap is not available.

WORKER_MODULE="smartcleaner.managers.plugin_runner"
PLUGIN_MODULE=${1:-"smartcleaner.plugins.test_isolated_plugin"}
CLASS_NAME=${2:-"TestIsolatedPlugin"}
METHOD=${3:-"scan"}

echo "Prototype bubblewrap: plugin=${PLUGIN_MODULE} class=${CLASS_NAME} method=${METHOD}"

if ! command -v bwrap >/dev/null 2>&1; then
  echo "bubblewrap (bwrap) not available; falling back to normal subprocess"
  ${PYTHON:-python3} -m ${WORKER_MODULE} --worker ${PLUGIN_MODULE} ${CLASS_NAME} ${METHOD}
  exit 0
fi

# Resolve repo root and ensure src in PYTHONPATH inside container
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Build bwrap command:
# - new user namespace and PID namespace implicitly handled by bwrap's --unshare-* options
# - create minimal writable /tmp, mount /proc, bind repo src for imports
# - restrict access to most of the host via read-only binds for /usr and /lib

set -x

# Determine whether this bwrap supports --map-user (not all versions do)
MAPUSER_FLAG=""
if bwrap --help 2>&1 | grep -q -- "--map-user"; then
  MAPUSER_FLAG="--map-user"
fi

# Determine whether this bwrap supports --seccomp and whether we have a profile
SECCOMP_FLAG=""
# bwrap expects a compiled seccomp filter (not raw JSON). By default we look for
# a precompiled binary filter at scripts/bwrap-seccomp.bin. You can override
# this by setting the env var BWRAP_SECCOMP_BIN to point to a compiled filter.
SECCOMP_FILE="${BWRAP_SECCOMP_BIN:-$REPO_ROOT/scripts/bwrap-seccomp.bin}"
if bwrap --help 2>&1 | grep -q -- "--seccomp" && [ -f "$SECCOMP_FILE" ]; then
  SECCOMP_FLAG="--seccomp $SECCOMP_FILE"
fi

# Ensure minimal init (may fail on some systems, ignore non-fatal failures)
bwrap \
  --unshare-user ${MAPUSER_FLAG} \
  --unshare-pid --proc /proc \
  --dev-bind /dev /dev \
  --ro-bind /usr /usr \
  --ro-bind /lib /lib \
  --ro-bind /lib64 /lib64 ${SECCOMP_FLAG} || true

# Use bwrap to run a shell that sets PYTHONPATH and invokes the worker
bwrap \
  --unshare-user ${MAPUSER_FLAG} \
  --unshare-pid --proc /proc \
  --bind "$REPO_ROOT/src" /app/src \
  --dir /tmp \
  --tmpfs /tmp \
  --ro-bind /usr /usr \
  --ro-bind /lib /lib \
  --ro-bind /lib64 /lib64 \
  --setenv PYTHONPATH /app/src${PYTHONPATH:+:$PYTHONPATH} \
  --setenv PATH /usr/bin:/bin \
  ${SECCOMP_FLAG} \
  -- bash -c "${PYTHON:-python3} -m ${WORKER_MODULE} --worker ${PLUGIN_MODULE} ${CLASS_NAME} ${METHOD}"
