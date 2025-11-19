# Contributing to Smart Cleaner

Thank you for your interest in contributing to Smart Cleaner! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Contributing to Smart Cleaner](#contributing-to-smart-cleaner)
  - [Table of Contents](#table-of-contents)
  - [Code of Conduct](#code-of-conduct)
  - [Getting Started](#getting-started)
  - [Development Environment Setup](#development-environment-setup)
    - [Prerequisites](#prerequisites)
    - [Setup Steps](#setup-steps)
  - [Making Changes](#making-changes)
    - [Branch Naming](#branch-naming)
    - [Code Style](#code-style)
    - [Type Hints](#type-hints)
  - [Testing](#testing)
    - [Running Tests](#running-tests)
    - [Writing Tests](#writing-tests)
  - [Code Quality](#code-quality)
    - [Pre-commit Checks](#pre-commit-checks)
    - [Optional: Pre-commit Hooks](#optional-pre-commit-hooks)
  - [Submitting Changes](#submitting-changes)
    - [Commit Messages](#commit-messages)
    - [Pull Request Process](#pull-request-process)
    - [PR Template](#pr-template)
  - [Plugin Development](#plugin-development)
    - [Creating a New Plugin](#creating-a-new-plugin)
    - [Plugin Guidelines](#plugin-guidelines)
  - [Questions?](#questions)

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment (see below)
4. Create a new branch for your feature or bugfix
5. Make your changes
6. Submit a pull request

## Development Environment Setup

### Prerequisites

- Python 3.10, 3.11, or 3.12
- Linux environment (Ubuntu 22.04+, Debian 12+, or similar)
- Git

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/YOUR-USERNAME/smart-cleaner.git
cd smart-cleaner

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package in editable mode with dev dependencies
pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt

# Optional: Install GUI dependencies
pip install PyQt6

# Verify installation
smartcleaner --help
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-docker-plugin` - for new features
- `fix/apt-cache-permission` - for bug fixes
- `docs/update-readme` - for documentation
- `refactor/plugin-base-class` - for refactoring

### Code Style

We follow PEP 8 with some modifications defined in `pyproject.toml`:

```bash
# Format code
black src tests

# Check linting
ruff check src tests

# Auto-fix linting issues
ruff check --fix src tests
```

### Type Hints

- Add type hints to all new functions
- Use `mypy` to check types:

```bash
mypy src --show-error-codes --pretty
```

## Testing

### Running Tests

```bash
# Run all tests
PYTHONPATH=src pytest -v

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_plugin_registry.py -v

# Run specific test
pytest tests/test_plugin_registry.py::test_register_plugin -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies (filesystem, network, sudo)

Example test structure:

```python
def test_plugin_scans_correctly():
    """Test that the plugin correctly identifies cleanable items."""
    # Arrange
    plugin = MyPlugin()

    # Act
    items = plugin.scan()

    # Assert
    assert len(items) > 0
    assert all(isinstance(item, CleanableItem) for item in items)
```

## Code Quality

### Pre-commit Checks

Before committing, ensure:

```bash
# 1. All tests pass
pytest -v

# 2. Linting passes
ruff check src tests

# 3. Type checking passes
mypy src --show-error-codes

# 4. Code is formatted
black src tests

# 5. No import errors
python -c "from smartcleaner.managers.cleaner_manager import CleanerManager; print('OK')"
```

### Optional: Pre-commit Hooks

Install pre-commit hooks to automate checks:

```bash
pip install pre-commit
pre-commit install
```

## Regenerating pinned dev constraints

When bumping development tools (black, ruff, mypy, pre-commit, pytest, etc.), regenerate `requirements-dev-constraints.txt` so CI uses exact pinned versions.

Two options:

- Quick (works without extra tools): create a fresh venv, install the dev extras, and write a filtered `pip freeze` output containing the dev tools you want pinned.

```bash
# create a fresh venv
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip

# install dev extras in editable mode
pip install -e ".[dev]"

# produce a constraints file with the common dev tools (adjust the grep list to your needs)
pip freeze | grep -E '^(black|ruff|mypy|pre-commit|pytest|pytest-cov|pytest-mock|click|tomli|tomli_w|tomlkit|rich|packaging)' > requirements-dev-constraints.txt

# Deactivate and commit the file
deactivate
git add requirements-dev-constraints.txt
git commit -m "chore(dev): regenerate pinned dev constraints"
```

- Recommended (more robust): use `pip-tools` to compile a constraints file from a minimal `requirements-dev.in` input.

```bash
# install pip-tools into your venv
pip install pip-tools

# create requirements-dev.in with the top-level dev tools, for example:
# black
# ruff
# mypy
# pre-commit
# pytest

# then compile to a pinned constraints file
pip-compile --output-file=requirements-dev-constraints.txt requirements-dev.in

# Commit the updated file
git add requirements-dev-constraints.txt
git commit -m "chore(dev): regenerate pinned dev constraints via pip-compile"
```

Note: After updating `requirements-dev-constraints.txt`, open a PR and ensure CI passes; the `validate-constraints` job will confirm the pinned versions match what CI installs.

## Submitting Changes

### Commit Messages

Write clear, descriptive commit messages:

feat: add Docker container cleanup plugin

- Implement DockerCleaner plugin for unused containers
- Add tests for container scanning
- Update plugin registry to include Docker
- Add documentation for Docker plugin

Format:

- First line: `<type>: <short description>` (50 chars or less)
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Body: Detailed explanation (optional, use bullet points)

### Pull Request Process

1. **Update documentation**: If you added features, update README.md and docs/
2. **Add tests**: Ensure new code has test coverage
3. **Update CHANGELOG**: Add entry under "Unreleased" section
4. **Run CI locally**: Ensure all tests and checks pass
5. **Create PR**: Use descriptive title and description
6. **Address reviews**: Respond to feedback promptly

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] All tests pass locally
- [ ] Added tests for new functionality
- [ ] Tested manually on Ubuntu 22.04

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Plugin Development

### Creating a New Plugin

1. **Create plugin file**: `src/smartcleaner/plugins/my_plugin.py`

```python
from pathlib import Path
from typing import List, Dict, Any

from ..managers.cleaner_manager import CleanableItem, SafetyLevel
from .base import BasePlugin


class MyPluginCleaner(BasePlugin):
    """Description of what this plugin cleans."""

    def get_name(self) -> str:
        return "My Plugin Name"

    def get_description(self) -> str:
        return "Detailed description of what this cleans"

    def scan(self) -> List[CleanableItem]:
        """Scan and return cleanable items."""
        items = []
        # Your scanning logic here
        return items

    def clean(self, items: List[CleanableItem]) -> Dict[str, Any]:
        """Clean the specified items."""
        result = {
            'success': True,
            'cleaned_count': 0,
            'total_size': 0,
            'errors': []
        }
        # Your cleaning logic here
        return result

    def is_available(self) -> bool:
        """Check if plugin is available on this system."""
        # Return True if plugin can run on this system
        return True

    def supports_dry_run(self) -> bool:
        """Whether plugin supports dry-run mode."""
        return True
```

1. **Register plugin**: Add to `src/smartcleaner/managers/plugin_registry.py`

```python
from ..plugins.my_plugin import MyPluginCleaner

# In discover_and_register_default_plugins():
self.register_plugin_class(MyPluginCleaner)
```

1. **Add tests**: Create `tests/test_my_plugin.py`

2. **Update documentation**: Add plugin to README.md table

### Plugin Guidelines

- **Safety First**: Use appropriate SafetyLevel (SAFE, CAUTION, ADVANCED, DANGEROUS)
- **No Direct Sudo**: Use `privilege.run_command()` instead
- **Error Handling**: Return errors in the result dict, don't raise exceptions
- **Dry-Run Support**: Implement `supports_dry_run()` and `clean_dry_run()`
- **Availability Check**: Implement `is_available()` to detect if plugin can run
- **Testing**: Mock all filesystem/system operations in tests

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues and PRs before creating new ones
- Be patient and respectful in discussions

Thank you for contributing to Smart Cleaner! 🎉
