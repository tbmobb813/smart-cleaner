# Smart Cleaner - GUI skeleton (PyQt6)

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

## Quick start (Linux)

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
python -m smartcleaner
```

## Notes on sudo and privilege escalation

- The code centralizes privilege escalation in `src/smartcleaner/utils/privilege.py`.
- To allow automated sudo runs, set `SMARTCLEANER_ALLOW_SUDO=1` in the environment
  (the CLI/GUI should set this only after explicit user confirmation).

## Contributing

- Run tests locally: `PYTHONPATH=src python -m pytest -q`.
- Avoid direct `sudo` in plugins; use `src/smartcleaner/utils/privilege.py`.
- Add unit tests for any feature that touches system state.

## Command-line interface (CLI)

Smart Cleaner includes a small CLI to inspect and restore operations. You can run it via the package entrypoint:

```bash
python -m smartcleaner
```

Or call the CLI module directly:

```bash
python -m smartcleaner.cli.commands list --db /path/to/smartcleaner.db
python -m smartcleaner.cli.commands show <operation_id> --db /path/to/smartcleaner.db
python -m smartcleaner.cli.commands restore <operation_id> --db /path/to/smartcleaner.db
```

Key `restore` options:
- `--dry-run`: show what would be restored without changing files.
- `--yes`: skip interactive confirmation.
- `--conflict-policy`: `rename` (default), `overwrite`, or `skip` when the destination path already exists.

Backup retention (gc):

Use the `gc` command to prune backup directories created by the undo system. It supports `--keep-last N` and `--older-than-days D` and prompts before deleting unless `--yes` is used.

Example:

```bash
python -m smartcleaner.cli.commands gc --keep-last 10 --yes
```

See `docs/GC.md` for examples of scheduling GC via systemd timers or cron.
