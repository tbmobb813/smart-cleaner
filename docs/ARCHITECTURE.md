# Smart Cleaner — Architecture Overview

This document summarizes the architecture, design decisions, and developer guidance for the Smart Cleaner project.

## High-level overview

The application is structured into the following layers:

- User Interfaces
  - CLI: `src/smartcleaner/cli` (planned)
  - GUI: `src/smartcleaner/gui/main_window.py` (PyQt6 skeleton)

- Application Layer
  - `CleanerManager` orchestrates plugins, scanning, and cleaning.
  - `SafetyValidator` enforces safety policies.
  - `UndoManager` and `DatabaseManager` provide logging and undo capability.

- Core Engine / Plugins
  - `src/smartcleaner/plugins/` contains individual cleaners (APT, kernels, etc.).
  - Plugins implement `scan()` and `clean(items)` and return `CleanableItem` instances.

- Utilities
  - `src/smartcleaner/utils/privilege.py` centralizes privilege escalation.

## Key design decisions

- Safety-first: every item has a `SafetyLevel` (IntEnum). The UI and CLI use a safety filter before allowing destructive actions.
- Centralized privilege escalation: plugins call the privilege helper instead of embedding `sudo` directly. `SMARTCLEANER_ALLOW_SUDO=1` must be set to allow sudo in automated contexts.
- Undo capability: the `UndoManager` attempts to back up files to a configured backup directory and records operations in SQLite. Undo is best-effort and has limitations (packages, config changes).
- Tests and CI: tests run with `PYTHONPATH=src`. A GitHub Actions workflow runs pytest and a basic linter (ruff).

## Important file locations

- Core manager: `src/smartcleaner/managers/cleaner_manager.py`
- Plugins: `src/smartcleaner/plugins/` (examples: `apt_cache.py`, `kernels.py`)
- Privilege helper: `src/smartcleaner/utils/privilege.py`
- DB ops: `src/smartcleaner/db/operations.py`
- Undo manager: `src/smartcleaner/managers/undo_manager.py`
- GUI skeleton: `src/smartcleaner/gui/main_window.py`

## How to run tests locally

From the project root:

```bash
# ensure dependencies (pytest) are installed in your environment
PYTHONPATH=src python3 -m pytest -q
```

## Developer notes

- When adding plugins:
  - Use `CleanableItem` for returned scan items.
  - Avoid calling `sudo` directly; instead call `privilege.run_command([...], sudo=True)`.

- Undo considerations:
  - For file deletions, `UndoManager` moves files to the backup directory and records `backup_path` in the DB.
  - Implement `restore_operation(operation_id)` to enable user-driven restores.

## Next improvements

- Implement CLI privilege flow (prompt and set SMARTCLEANER_ALLOW_SUDO securely).
- Harden `UndoManager` restore behavior: preserve permissions, owner, timestamps.
- Add more plugin implementations and tests for browsers, thumbnails, temp files.
- Add strict linting and type checking (ruff + mypy) in CI.
