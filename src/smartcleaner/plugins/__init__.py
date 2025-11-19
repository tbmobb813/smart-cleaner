"""Smart Cleaner plugin system.

All plugins should inherit from BasePlugin and implement the required methods.
"""
from .apt_cache import APTCacheCleaner
from .base import BasePlugin
from .browser_cache import BrowserCacheCleaner
from .kernels import KernelCleaner
from .systemd_journals import SystemdJournalsCleaner
from .temp_files import TempFilesCleaner
from .thumbnails import ThumbnailCacheCleaner

__all__ = [
    'BasePlugin',
    'APTCacheCleaner',
    'KernelCleaner',
    'BrowserCacheCleaner',
    'TempFilesCleaner',
    'ThumbnailCacheCleaner',
    'SystemdJournalsCleaner',
]
