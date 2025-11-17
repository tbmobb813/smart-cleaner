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

## CLI

The project includes a small Click-based CLI at `src/smartcleaner/cli/commands.py`.

- `list` — list recent clean operations stored in the DB.
- `show <operation_id>` — show operation details and undo items.
- `restore <operation_id>` — restore backed-up files for an operation.
  - Options: `--dry-run`, `--yes` (skip confirmation), and `--conflict-policy` (rename|overwrite|skip).
- `gc` — prune old backup directories with `--keep-last` and `--older-than-days`.

The CLI uses the same `DatabaseManager` and `UndoManager` APIs as the programmatic API and is safe-by-default (asks for confirmation before destructive actions).

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
  - Current behavior: move backup back to original. If move fails (cross-filesystem) we fallback to `shutil.copy2()` then remove the backup. Ownership is attempted via `os.chown()` if recorded at backup time; failures are recorded in the DB's `restore_error` field but do not abort the restore.
- Add more plugin implementations and tests for browsers, thumbnails, temp files.
- Add strict linting and type checking (ruff + mypy) in CI.

## Backup retention

Backups are stored under the configured `backup_dir` (default: `~/.local/share/smartcleaner/backups`) in directories named like `op_<id>_<timestamp>`. The `UndoManager.prune_backups()` method (exposed via the CLI `gc` command) can remove old backups. The pruning logic uses the timestamp suffix in the directory name; adjust accordingly if you change the naming scheme.
