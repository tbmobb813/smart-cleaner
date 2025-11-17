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

## Configuration

Smart Cleaner reads configuration from the XDG configuration directory. By default

the config file is expected at:

  $XDG_CONFIG_HOME/smartcleaner/config.toml


If `XDG_CONFIG_HOME` is not set, the fallback path is:

  ~/.config/smartcleaner/config.toml

Supported configuration keys (TOML):

- `keep_kernels` (integer): default number of recent kernels to keep when
  running `clean kernels` (CLI flags override this value).
- `db_path` (string): default path to the sqlite DB used for undo/logging.

Environment variables override config values:

- `SMARTCLEANER_KEEP_KERNELS` overrides `keep_kernels`.
- `SMARTCLEANER_DB_PATH` overrides `db_path`.

The CLI also accepts runtime flags which take precedence over both config and
environment variables. Example:

```bash
smartcleaner clean kernels --keep-kernels 3 --yes
```

## Example output: plugins show

The `plugins show <module:ClassName>` command prints available metadata and the
constructor signature. Example output (abridged):

```
PLUGIN_INFO:
  name: APT Package Cache Cleaner
  description: Scans and cleans APT package cache (deb files and partial downloads).
Class: smartcleaner.plugins.apt_cache.APTCacheCleaner
Doc: Cleans APT package cache located at /var/cache/apt/archives by default.
Constructor:
  cache_dir: pathlib.Path = PosixPath('/var/cache/apt/archives')
```

This helps discover which plugin factories are available and what constructor
arguments they accept.

Additional sample outputs:

```
PLUGIN_INFO:
  name: Browser Cache Cleaner
  description: Scans common browser cache directories (Chrome/Chromium/Firefox) and removes cached files and empty dirs.
Class: smartcleaner.plugins.browser_cache.BrowserCacheCleaner
Doc: Cleans common browser cache directories (Chrome/Chromium/Firefox) under a base cache dir.
Constructor:
  base_dirs: typing.Optional[list[pathlib.Path]] = None
```

```
PLUGIN_INFO:
  name: Thumbnail Cache Cleaner
  description: Scans and cleans user thumbnail cache (~/.cache/thumbnails).
Class: smartcleaner.plugins.thumbnails.ThumbnailCacheCleaner
Doc: Cleans the GNOME/thumbnail cache at ~/.cache/thumbnails by default.
Constructor:
  cache_dir: typing.Optional[pathlib.Path] = None
```

## Per-plugin configuration

Smart Cleaner supports per-plugin persistent configuration stored under the
XDG config file (`$XDG_CONFIG_HOME/smartcleaner/config.toml`). Plugin-specific
settings are stored under the `plugins` table using the plugin module name as
the table key. Example:

```toml
[plugins."smartcleaner.plugins.kernels"]
keep_kernels = 3
```

Use the `config plugin` CLI to manage per-plugin values. Values are validated
against each plugin's `PLUGIN_INFO['config']` schema before being written.

Examples:

```bash
# Set the keep_kernels value for the kernels plugin (validated)
smartcleaner config plugin set smartcleaner.plugins.kernels keep_kernels 3 --yes

# Read a plugin-scoped value
smartcleaner config plugin get smartcleaner.plugins.kernels keep_kernels

# Get it as JSON for programmatic consumption
smartcleaner config plugin get smartcleaner.plugins.kernels keep_kernels --json
```

Notes:
- The CLI will validate values (min/max/choices/type) using the plugin's
  declared schema and will refuse invalid inputs.
- For TOML writing we prefer `tomli-w` (installed via `requirements.txt`) to
  ensure round-trip friendly, deterministic output. If `tomli-w` is not
  available the code falls back to a safe scalar TOML writer that still
  preserves plugin tables and basic array types.


