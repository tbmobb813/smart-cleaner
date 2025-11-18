# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Added - Version 0.2.0 (In Development)

#### Plugin System & Architecture
- **BasePlugin abstract class**: Consistent interface for all cleaner plugins
- **PluginRegistry system**: Automatic plugin discovery and management
- **Dry-run support**: All plugins support dry-run mode to preview changes
- **Plugin availability checking**: Plugins detect if they're available on the system
- **Plugin priority system**: Control execution order of plugins

#### New Cleaning Plugins
- **BrowserCacheCleaner**: Clean cache from Firefox, Chrome, Chromium, Brave, and Edge
- **TempFilesCleaner**: Clean old temporary files from /tmp and ~/.cache (configurable age threshold)
- **ThumbnailsCleaner**: Clean cached thumbnails from ~/.cache/thumbnails
- **SystemdJournalsCleaner**: Clean old systemd journal logs (keeps last 30 days by default)
- Updated existing APTCacheCleaner and KernelCleaner to use new BasePlugin interface

#### Enhanced CleanerManager
- Complete rewrite from stub to fully functional orchestrator
- Real plugin integration via PluginRegistry
- Safety validation enforcement during all cleaning operations
- Automatic undo/backup integration for all operations
- Support for scanning all plugins or targeting specific ones
- Comprehensive error handling and logging throughout

#### CLI Improvements
- **New `scan` command**: Scan for cleanable items with optional plugin filtering
- **New `clean` command**: Clean items with safety controls, dry-run, and confirmation
- **Safety level control**: `--safety` flag (SAFE, CAUTION, ADVANCED, DANGEROUS)
- **Plugin targeting**: `--plugin` flag to work with specific plugins
- **Dry-run mode**: `--dry-run` flag to preview without making changes
- **Auto-confirm**: `--yes` flag to skip confirmation prompts
- **Logging controls**: `--verbose/-v` and `--quiet/-q` flags
- Color-coded output with safety indicators
- Human-readable size formatting
- Interactive confirmation for destructive operations
- sudo privilege warnings for system operations

#### Logging & Observability
- Structured logging configuration module
- CLI-specific logging with verbosity control
- Logging throughout managers and plugins
- Appropriate log formatting for CLI vs library use

#### Testing & Quality
- Added requirements-dev.txt with development dependencies (pytest, mypy, ruff, black)
- New test suite for PluginRegistry (8 tests)
- New test suite for enhanced CleanerManager (10 tests)
- Tests cover registration, scanning, cleaning, dry-run, safety filtering

#### Architecture Improvements
- Better separation of concerns (registry, manager, validator)
- Consistent plugin interface across all cleaners
- Extensible design for adding new plugins
- Integration with existing undo/restore system
- Database logging for all cleaning operations

### Changed
- CleanerManager completely rewritten (no longer returns stub data)
- GUI automatically works with new CleanerManager (no changes needed)
- Plugin system now uses discovery pattern instead of manual imports

### Files Added/Modified
- **Added**: 8 new Python modules (base.py, 4 plugins, registry, logging_config, __init__)
- **Added**: 2 new test files with 18 tests
- **Added**: requirements-dev.txt
- **Modified**: CleanerManager, CLI commands, existing plugins

This release transforms Smart Cleaner from a skeleton/proof-of-concept into a
fully functional Linux system cleaning toolkit with 6 production-ready plugins.

## 0.1.1 - 2025-11-17

- Make mypy type-checking a required CI step (mypy passes locally).
- Fix various typing and small syntax issues reported by mypy.
- Ensure tests pass locally (17 unit tests).

Patch release published to include CI hardening and various small fixes.
