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
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
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


def _extract_json_from_output(output: str) -> Any:
    """Find the first JSON array/object in output and parse it.

    Prototype scripts may print diagnostic lines before the JSON result; this
    helper locates the first `[` or `{` and attempts to parse from there.
    """
    idx = None
    for ch in ("[", "{"):
        i = output.find(ch)
        if i != -1:
            idx = i
            break
    if idx is None:
        raise ValueError("No JSON found in output")
    return json.loads(output[idx:])


def run_subprocess(
    plugin_dotted: str,
    class_name: str,
    method: str,
    timeout: int | None = None,
    isolation: str | None = None,
) -> Any:
    """Run a plugin method in a subprocess and return the parsed JSON result.

    isolation: None | 'subprocess' | 'userns' | 'container' -- when 'userns', the
    prototype sandbox script will be used if available.
    """
    repo_root = Path(__file__).resolve().parents[3]
    repo_src = str(Path(__file__).resolve().parents[2])
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = repo_src + (":" + existing if existing else "")

    if isolation == "userns":
        # Use the prototype sandbox wrapper script if present
        wrapper = repo_root / "scripts" / "prototype_sandbox.sh"
        if wrapper.exists():
            cmd = [str(wrapper), plugin_dotted, class_name, method]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if proc.returncode != 0:
                raise RuntimeError(f"Plugin worker failed: {proc.stderr.strip()}")
            return _extract_json_from_output(proc.stdout)

    if isolation in ("bwrap", "bubblewrap"):
        wrapper = repo_root / "scripts" / "prototype_bwrap.sh"
        if wrapper.exists():
            cmd = [str(wrapper), plugin_dotted, class_name, method]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if proc.returncode != 0:
                raise RuntimeError(f"Plugin worker failed: {proc.stderr.strip()}")
            return _extract_json_from_output(proc.stdout)

    # Default: run module worker directly
    cmd = [sys.executable, "-m", "smartcleaner.managers.plugin_runner", "--worker", plugin_dotted, class_name, method]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
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
        # Remove the --worker marker and pass the remaining args to the worker
        idx = sys.argv.index("--worker")
        worker_args = [sys.argv[0]] + sys.argv[idx + 1 :]
        raise SystemExit(_worker_main(worker_args))
    # Module used as library otherwise
