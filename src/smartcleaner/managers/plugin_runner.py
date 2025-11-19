"""PluginRunner: run plugin methods in a subprocess for isolation.

This module provides a small helper to run a plugin method (scan/clean) in a separate
Python process and capture its JSON-serializable result via stdout. The runner is
deliberately small and unopinionated; integration into the manager should be done
carefully and allow toggling isolation per-plugin.
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from importlib import import_module
from typing import Any


def _call_plugin_method(plugin_dotted: str, class_name: str, method: str) -> Any:
    """Import plugin class and call method, returning a JSON-serializable value.

    plugin_dotted: dotted module path (e.g. smartcleaner.plugins.temp_files)
    class_name: class name inside the module
    method: method to call (scan/clean/is_available)
    """
    mod = import_module(plugin_dotted)
    cls = getattr(mod, class_name)
    inst = cls()
    fn = getattr(inst, method)
    return fn()


def run_subprocess(plugin_dotted: str, class_name: str, method: str, timeout: int | None = None) -> Any:
    """Run a plugin method in a subprocess and return the parsed JSON result.

    The subprocess invokes this module with `--worker` mode.
    """
    cmd = [sys.executable, "-m", "smartcleaner.managers.plugin_runner", "--worker", plugin_dotted, class_name, method]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"Plugin worker failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def _worker_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin_dotted")
    parser.add_argument("class_name")
    parser.add_argument("method")
    args = parser.parse_args(argv[1:])

    try:
        result = _call_plugin_method(args.plugin_dotted, args.class_name, args.method)
        print(json.dumps(result))
    except Exception as exc:  # pragma: no cover - isolated runtime
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    # Worker entrypoint
    if "--worker" in sys.argv:
        raise SystemExit(_worker_main(sys.argv))
    # Module used as library otherwise
