Smart Cleaner - GUI skeleton (PyQt6)
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
python -m smartcleaner
```

Notes on sudo and privilege escalation:

- The code centralizes privilege escalation in `src/smartcleaner/utils/privilege.py`.
- To allow automated sudo runs, set `SMARTCLEANER_ALLOW_SUDO=1` in the environment
	(the CLI/GUI should set this only after explicit user confirmation).

````
