# Smart Cleaner - GUI skeleton (PyQt6)

Version: 0.1.1

===================================

````markdown
Smart Cleaner - GUI skeleton (PyQt6)
===================================

Smart Cleaner is a modular Linux system cleaning toolkit. The project is
organized into plugins (each implements scanning and cleaning), a manager to
orchestrate operations, a small undo/logging layer, and both CLI/GUI front-ends
(the GUI is a minimal PyQt6 skeleton in `src/smartcleaner/gui/main_window.py`).

See `docs/ARCHITECTURE.md` for a developer-focused architecture overview and
design notes.

Quick start (Linux)
---------------------

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install test dependencies (pytest) and optional GUI deps:

```bash
pip install --upgrade pip
pip install pytest
# optional: pip install PyQt6
```

3. Run tests:

```bash
PYTHONPATH=src python -m pytest -q
```

4. Run the GUI skeleton (requires PyQt6):

```bash
# Smart Cleaner

Smart Cleaner is a modular Linux system cleaning toolkit. The project is
organized into plugins (each implements scanning and cleaning), a manager to
orchestrate operations, a small undo/logging layer, and both CLI/GUI front-ends
(the GUI is a minimal PyQt6 skeleton in `src/smartcleaner/gui/main_window.py`).

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md` for developer-focused
architecture and roadmap.
<!-- Badge: CI status -->
![CI](https://github.com/tbmobb813/smart-cleaner/actions/workflows/ci.yml/badge.svg)

# Smart Cleaner

Smart Cleaner is a modular Linux system cleaning toolkit. It provides:

- A small plugin system (each plugin scans and reports items that can be cleaned).
- A manager layer to orchestrate scans/cleans and a safe undo/restore system.
- A CLI and a minimal PyQt6 GUI skeleton (see `src/smartcleaner/gui/main_window.py`).

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md` for developer docs and plans.

## Quick start (Linux)

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install test dependencies (pytest) and optional GUI deps:

```bash
pip install --upgrade pip
pip install -r requirements.txt
# optional: pip install PyQt6
```

3. Run tests:

```bash
PYTHONPATH=src python -m pytest -q
```

4. Run the CLI (module form):

```bash
python -m smartcleaner.cli.commands list --db /path/to/smartcleaner.db
```

Or, after installing the package (editable install):

```bash
pip install -e .
smartcleaner --help
```

## Notes on sudo and privilege escalation

Privilege escalation is centralized in `src/smartcleaner/utils/privilege.py`.
To allow automated sudo runs, set `SMARTCLEANER_ALLOW_SUDO=1` in the environment — only after explicit user confirmation.

## Contributing

- Run tests locally: `PYTHONPATH=src python -m pytest -q`.
- Avoid direct `sudo` in plugins; use `src/smartcleaner/utils/privilege.py`.
- Add unit tests for any feature that touches system state.

## Scheduling GC (backups cleanup)

Use the `gc` command to prune backups. See `docs/GC.md` for systemd and cron examples.
