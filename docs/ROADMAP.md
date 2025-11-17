# Roadmap & Implementation Plan

This roadmap outlines prioritized implementation milestones for Smart Cleaner. Items are ordered from highest to lower priority; each item includes a short acceptance criteria and related tests.

## Phase 1 — Safety, Undo, and Privilege Flow (current focus)

1. Undo restore implementation
   - Add `UndoManager.restore_operation(operation_id)` that attempts to restore files from backups, preserving permissions and timestamps when possible.
   - Tests: unit test that creates temporary file, logs operation (which moves file to backup), calls restore and asserts file content and metadata are restored.
   - Acceptance: tests pass and restore returns success flag and logs.

2. CLI privilege flow
   - Implement `cli/commands.py` with `scan`, `clean`, and `undo` commands.
   - Add interactive confirmation before setting `SMARTCLEANER_ALLOW_SUDO=1` for privileged operations.
   - Support `--yes` and `--dry-run` flags.
   - Tests: run CLI commands in dry-run mode and ensure no privileged actions executed.

3. SafetyValidator enforcement
   - Integrate `SafetyValidator` into `CleanerManager` to consistently enforce safety levels.
   - Tests: ensure cleaning honors safety levels.

## Phase 2 — Plugin Ecosystem & Sandboxing

1. Additional plugins
   - Implement `browser_cache.py`, `temp_files.py`, `thumbnails.py` under `src/smartcleaner/plugins/`.
   - Provide unit tests with filesystem mocks.

2. Plugin sandboxing
   - Add a dry-run mode for plugins where they report file lists and commands without executing them.
   - Provide a plugin API to declare whether the plugin supports dry-run and undo.

## Phase 3 — Packaging, CI & Quality

1. Packaging
   - Add `pyproject.toml` metadata (already present) and ensure `console_scripts` entry points for CLI.
   - Provide packaging scripts and instructions for building a wheel.

2. CI & Quality gates
   - Expand CI to run ruff with strict rules and mypy.
   - Add coverage reporting and a badge to README.

## Phase 4 — UX, Scheduler, and Distribution

1. GUI polish
   - Implement progressive scan UI, pagination, and selection of individual items.
   - Support theme and accessibility improvements.

2. Scheduler
   - Provide an optional systemd timer or cron setup to run scheduled cleanups with user consent.

3. Distribution
   - Create distro-specific packaging (deb, rpm) or a Flatpak for easy installation.

## Contributor guidelines

- Run tests locally: `PYTHONPATH=src python -m pytest -q`.
- Add unit tests for every plugin and manager change.
- Avoid direct `sudo` in plugins; use `src/smartcleaner/utils/privilege.py`.
