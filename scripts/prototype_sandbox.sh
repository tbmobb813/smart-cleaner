#!/usr/bin/env bash
set -euo pipefail

# Prototype script: try running the plugin worker in an unprivileged user namespace
# If unavailable, fall back to running the worker normally. Designed for experiments
# on developer machines where user namespaces are permitted.

WORKER_MODULE="smartcleaner.managers.plugin_runner"
PLUGIN_MODULE=${1:-"smartcleaner.plugins.test_isolated_plugin"}
CLASS_NAME=${2:-"TestIsolatedPlugin"}
METHOD=${3:-"scan"}

echo "Prototype sandbox: plugin=${PLUGIN_MODULE} class=${CLASS_NAME} method=${METHOD}"

if command -v unshare >/dev/null 2>&1; then
  echo "unshare found; attempting to run in user namespace"
  # Try to create a user namespace and run the module.
  # map-root-user will map the current user to root inside the namespace.
  # We also create a new mount & pid namespace so mounts and /proc can be isolated.
  set -x
  # Ensure Python can import local package (src/) inside the namespace
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
  unshare --user --map-root-user --mount --pid --fork --mount-proc \
    -- bash -c "${PYTHON:-python3} -m ${WORKER_MODULE} --worker ${PLUGIN_MODULE} ${CLASS_NAME} ${METHOD}"
  set +x
else
  echo "unshare not available; running fallback subprocess (no userns)"
  ${PYTHON:-python3} -m ${WORKER_MODULE} --worker ${PLUGIN_MODULE} ${CLASS_NAME} ${METHOD}
fi
