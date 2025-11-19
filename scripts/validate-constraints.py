#!/usr/bin/env python3
"""Validate pinned dev constraints against a pip freeze output.

Usage:
  python scripts/validate-constraints.py requirements-dev-constraints.txt frozen.txt

Exits non-zero if any pinned package is missing or mismatched in frozen.txt.
"""
from __future__ import annotations

import sys
from pathlib import Path
from packaging.utils import canonicalize_name


def read_lines(path: Path) -> list[str]:
    with path.open() as f:
        return [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: validate-constraints.py <constraints.txt> <frozen.txt>")
        return 2

    constraints_file = Path(argv[1])
    frozen_file = Path(argv[2])

    if not constraints_file.exists():
        print(f"Constraints file not found: {constraints_file}")
        return 2
    if not frozen_file.exists():
        print(f"Frozen file not found: {frozen_file}")
        return 2

    constraints = read_lines(constraints_file)
    frozen = read_lines(frozen_file)

    # Build installed map: canonical name -> frozen line
    installed: dict[str, str] = {}
    for f in frozen:
        if '==' in f:
            name = f.split('==', 1)[0]
            can = canonicalize_name(name)
            installed[can] = f
            # store underscore-normalized variant
            installed[can.replace('-', '_')] = f

    ok = True
    for c in constraints:
        if '==' in c:
            name = c.split('==', 1)[0]
            can = canonicalize_name(name)
            inst = installed.get(can) or installed.get(can.replace('-', '_'))
            if not inst:
                print(f"MISSING: {c} not present in {frozen_file}")
                ok = False
            else:
                if inst.lower() != c.lower():
                    print(f"MISMATCH: constraint {c} != installed {inst}")
                    ok = False

    if not ok:
        print("\nConstraints validation failed. If you intentionally updated dev deps, regenerate requirements-dev-constraints.txt and update the PR.")
        return 1

    print("OK: requirements-dev-constraints.txt matches installed dev versions")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
