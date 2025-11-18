"""Smart Cleaner plugin system.

All plugins should inherit from BasePlugin and implement the required methods.
"""
from .base import BasePlugin
from .apt_cache import APTCacheCleaner
from .kernels import KernelCleaner
from .browser_cache import BrowserCacheCleaner
from .temp_files import TempFilesCleaner
from .thumbnails import ThumbnailsCleaner
from .systemd_journals import SystemdJournalsCleaner

__all__ = [
    'BasePlugin',
    'APTCacheCleaner',
    'KernelCleaner',
    'BrowserCacheCleaner',
    'TempFilesCleaner',
    'ThumbnailsCleaner',
    'SystemdJournalsCleaner',
]
