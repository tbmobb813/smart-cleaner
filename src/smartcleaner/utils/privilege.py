"""Privilege helper utilities.

Provide a centralized place to run commands that may require elevation.
Plugins should call `run_command(...)` instead of embedding 'sudo' themselves.

Safety design choices:
- By default we do not escalate unless the environment variable
  SMARTCLEANER_ALLOW_SUDO is set to a truthy value. This prevents tests or
  accidental runs from invoking sudo. The manager/UI should explicitly ask
  for elevation and set the env variable when appropriate.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Sequence


def _allow_sudo_from_env() -> bool:
    return os.environ.get('SMARTCLEANER_ALLOW_SUDO', '') not in ('', '0', 'false', 'False')


def run_command(cmd: Sequence[str], sudo: bool = False, check: bool = True, capture_output: bool = True, text: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a command, optionally via sudo.

    Security: we only prepend 'sudo' when `sudo` is True and the environment
    variable SMARTCLEANER_ALLOW_SUDO is set. This ensures callers cannot
    accidentally escalate privileges during tests.

    Returns the CompletedProcess.
    Raises subprocess.CalledProcessError if check=True and the process fails.
    """
    cmd_list = list(cmd)
    if sudo:
        if not _allow_sudo_from_env():
            raise PermissionError("Sudo not allowed: set SMARTCLEANER_ALLOW_SUDO=1 to permit elevation")
        # Prepend sudo in a safe manner
        cmd_list = ['sudo', '-n'] + cmd_list

    # Use subprocess.run directly
    return subprocess.run(cmd_list, check=check, capture_output=capture_output, text=text, env=env)


def render_command(cmd: Sequence[str], sudo: bool = False) -> str:
    """Return a shell-safe string representation of the command for logging or dry-run."""
    prefix = ['sudo', '-n'] if sudo else []
    return ' '.join(shlex.quote(p) for p in (prefix + list(cmd)))
