#!/usr/bin/env python3
"""Validate detected plugins against the plugin schema.

Usage:
  python scripts/validate-plugin-schema.py [path/to/plugins/package]

If no path provided, the script will look under `src/smartcleaner/plugins`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except Exception:  # pragma: no cover - optional dev dep
    print("Please install jsonschema to run this validator: pip install jsonschema")
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLUGINS_PATH = ROOT / "src" / "smartcleaner" / "plugins"
SCHEMA_PATH = ROOT / "docs" / "plugin_schema.json"


def discover_plugins(dirpath: Path) -> list[Path]:
    if not dirpath.exists():
        return []
    return [p for p in dirpath.glob("*.py") if p.is_file() and not p.name.startswith("__")]


def load_module_from_path(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str]) -> int:
    plugins_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_PLUGINS_PATH
    schema = json.loads(SCHEMA_PATH.read_text())

    problems = 0
    plugins = discover_plugins(plugins_dir)
    if not plugins:
        print(f"No plugin modules found in {plugins_dir}")
        return 0

    for p in plugins:
        print(f"Validating {p.name}...")
        try:
            mod = load_module_from_path(p)
        except Exception as exc:
            print(f"  ERROR: failed to import {p.name}: {exc}")
            problems += 1
            continue

        # Build a minimal dict to validate
        candidate = {}
        if hasattr(mod, "PLUGIN_INFO"):
            candidate["PLUGIN_INFO"] = getattr(mod, "PLUGIN_INFO")
        else:
            print(f"  MISSING: PLUGIN_INFO in {p.name}")
            problems += 1
            continue

        try:
            jsonschema.validate(instance=candidate, schema=schema)
        except Exception as exc:
            print(f"  SCHEMA ERROR: {exc}")
            problems += 1
            continue

        print("  OK")

    if problems:
        print(f"Validation finished: {problems} problem(s) found")
        return 1
    print("Validation finished: all plugins OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
