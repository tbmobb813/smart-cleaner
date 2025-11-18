# Smart Cleaner

![CI](https://github.com/tbmobb813/smart-cleaner/actions/workflows/ci.yml/badge.svg)

Version: 0.2.0-dev

Smart Cleaner is a modular Linux system cleaning toolkit with a focus on safety, transparency, and undo capabilities.

## Features

### 🔌 Plugin-Based Architecture

- **6 Built-in Plugins**: APT cache, old kernels, browser cache, temporary files, thumbnails, systemd journals
- **Extensible Design**: Easy to add new cleaning plugins
- **Safety Levels**: Every item tagged with safety level (SAFE, CAUTION, ADVANCED, DANGEROUS)
- **Dry-Run Support**: Preview what will be cleaned before making changes
- **Auto-Discovery**: Plugins automatically registered and available

### 🛡️ Safety First

- Safety validator enforces policies before cleaning
- Automatic backup/undo system for file operations
- Database logging of all operations
- Interactive confirmations for destructive actions
- Privilege escalation warnings (SMARTCLEANER_ALLOW_SUDO)

### 🖥️ Multiple Interfaces

- **CLI**: Full-featured command-line interface with scan, clean, restore, gc commands
- **GUI**: PyQt6 graphical interface (functional, works with all plugins)
- **Library**: Use as a Python library in your own code

### 📊 Comprehensive CLI

```bash
# Scan for cleanable items
smartcleaner scan                    # Scan all plugins
smartcleaner scan --plugin "APT Package Cache"  # Scan specific plugin
smartcleaner scan --safety SAFE      # Only show SAFE items

# Clean items
smartcleaner clean                   # Clean with confirmation
smartcleaner clean --dry-run         # Preview without cleaning
smartcleaner clean --yes             # Skip confirmation
smartcleaner clean --safety ADVANCED # Clean up to ADVANCED level

# View operation history
smartcleaner list                    # Recent operations
smartcleaner show 123                # Details for operation 123

# Restore from backups
smartcleaner restore 123             # Restore operation 123
smartcleaner restore 123 --dry-run   # Preview restore

# Prune old backups
smartcleaner gc --keep-last 5        # Keep 5 most recent
smartcleaner gc --older-than-days 30 # Remove backups >30 days old
```

Features: Color-coded output, safety indicators, human-readable sizes, logging controls (`--verbose`, `--quiet`)

## Quick Start (Linux)

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
# For development:
pip install -r requirements-dev.txt
# For GUI (optional):
pip install PyQt6
```

### 3. Run tests

```bash
PYTHONPATH=src python -m pytest -q
```

### 4. Install and run

```bash
# Install package (editable mode)
pip install -e .

# Use CLI
smartcleaner --help
smartcleaner scan
smartcleaner clean --dry-run

# Run GUI (requires PyQt6)
python -m smartcleaner.gui.main_window
```

## Available Plugins

| Plugin | Description | Safety Level | Requires Sudo |
|--------|-------------|--------------|---------------|
| **APT Package Cache** | Cached .deb files from APT | SAFE | Yes |
| **Old Kernels** | Old kernel packages (keeps current + 1) | SAFE | Yes |
| **Browser Cache** | Firefox, Chrome, Chromium, Brave, Edge | SAFE | No |
| **Temporary Files** | Old files from /tmp and ~/.cache | SAFE-CAUTION | No |
| **Thumbnail Cache** | Cached thumbnails | SAFE | No |
| **Systemd Journals** | Old systemd logs (keeps 30 days) | CAUTION | Yes |

## Architecture

smartcleaner/
├── plugins/          # Cleaning plugins (inherit from BasePlugin)
│   ├── base.py       # BasePlugin abstract class
│   ├── apt_cache.py
│   ├── kernels.py
│   ├── browser_cache.py
│   ├── temp_files.py
│   ├── thumbnails.py
│   └── systemd_journals.py
├── managers/         # Core orchestration
│   ├── cleaner_manager.py  # Main orchestrator
│   ├── plugin_registry.py  # Plugin discovery
│   ├── undo_manager.py     # Backup/restore
│   └── safety_validator.py # Safety enforcement
├── cli/              # Command-line interface
├── gui/              # PyQt6 GUI
├── db/               # SQLite operations
└── utils/            # Logging, privilege escalation

See `docs/ARCHITECTURE.md` for detailed architecture overview and design decisions.

## Safety and Privilege Escalation

Privilege escalation is centralized in `src/smartcleaner/utils/privilege.py`.

To allow automated sudo for system operations (APT, kernels, journals):

```bash
export SMARTCLEANER_ALLOW_SUDO=1
smartcleaner clean  # Will use sudo when needed
```

**Warning**: Only set this after reviewing what will be cleaned and understanding the implications.

## Contributing

- Run tests locally: `PYTHONPATH=src python -m pytest -q`
- Use development dependencies: `pip install -r requirements-dev.txt`
- Run type checking: `mypy src --show-error-codes --ignore-missing-imports`
- Run linter: `ruff check .`
- Avoid direct `sudo` in plugins; use `src/smartcleaner/utils/privilege.py`
- Add unit tests for any new feature
- All plugins should inherit from `BasePlugin`

## Development Roadmap

See `docs/ROADMAP.md` for planned features and implementation priorities.

Completed in v0.2.0:

- ✅ Plugin system and registry
- ✅ 4 new cleaning plugins
- ✅ Dry-run support
- ✅ Enhanced CLI (scan/clean commands)
- ✅ Structured logging

Upcoming:

- Progress indicators for CLI (using rich library)
- Additional plugins (Docker, Snap cache)
- Coverage reporting
- Distribution packaging (deb, rpm)

## Documentation

- `docs/ARCHITECTURE.md` - Architecture overview and design decisions
- `docs/ROADMAP.md` - Development roadmap and priorities
- `docs/GC.md` - Backup garbage collection and scheduling

## License

See `LICENSE` file.
