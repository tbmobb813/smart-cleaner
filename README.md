Smart Cleaner - GUI skeleton (PyQt6)
===================================

This folder contains a minimal PyQt6-based GUI skeleton for the Smart Cleaner project. It demonstrates the proposed UI layout and how the GUI can interact with a backend `CleanerManager`.

Quick start (Linux)
---------------------

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install pytest to run the included tests (GUI requires PyQt6 to run):

```bash
pip install --upgrade pip
pip install pytest
```

3. Run tests:

```bash
PYTHONPATH=src python -m pytest -q
```

4. To run the GUI (when PyQt6 is installed):

```bash
python -m smartcleaner
```
