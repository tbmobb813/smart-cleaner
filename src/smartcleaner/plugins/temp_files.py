"""Temporary files cleaner plugin.

Cleans temporary files from /tmp and user cache directories that are older
than a configurable threshold.
"""
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta
import time

from ..managers.cleaner_manager import CleanableItem, SafetyLevel
from .base import BasePlugin


class TempFilesCleaner(BasePlugin):
    """Cleans old temporary files from system and user cache directories."""

    def __init__(
        self,
        min_age_days: int = 7,
        home_dir: Path = Path.home(),
        check_system_tmp: bool = True
    ):
        """Initialize the temp files cleaner.

        Args:
            min_age_days: Only clean files older than this many days (default: 7).
            home_dir: User home directory.
            check_system_tmp: Whether to check /tmp (requires appropriate permissions).
        """
        self.min_age_days = min_age_days
        self.home_dir = Path(home_dir)
        self.check_system_tmp = check_system_tmp
        self.cutoff_time = time.time() - (min_age_days * 24 * 60 * 60)

    def get_name(self) -> str:
        return "Temporary Files"

    def get_description(self) -> str:
        return f"Old temporary files (>{self.min_age_days} days) from /tmp and ~/.cache."

    def scan(self) -> List[CleanableItem]:
        items: List[CleanableItem] = []

        # Scan user cache directory
        user_cache = self.home_dir / '.cache'
        if user_cache.exists():
            items.extend(self._scan_directory(user_cache, "User cache"))

        # Scan system /tmp if enabled
        if self.check_system_tmp:
            system_tmp = Path('/tmp')
            if system_tmp.exists():
                items.extend(self._scan_directory(system_tmp, "System temp"))

        return items

    def _scan_directory(self, path: Path, category: str) -> List[CleanableItem]:
        """Scan a directory for old temporary files."""
        items: List[CleanableItem] = []

        try:
            for entry in path.rglob('*'):
                if entry.is_file():
                    try:
                        stat = entry.stat()
                        # Check if file is old enough
                        if stat.st_mtime < self.cutoff_time:
                            # Determine safety level based on location and age
                            age_days = (time.time() - stat.st_mtime) / (24 * 60 * 60)

                            # Files in /tmp that are very old are safer
                            if '/tmp' in str(entry) and age_days > 30:
                                safety = SafetyLevel.SAFE
                            elif age_days > 14:
                                safety = SafetyLevel.SAFE
                            else:
                                safety = SafetyLevel.CAUTION

                            items.append(CleanableItem(
                                path=str(entry),
                                size=stat.st_size,
                                description=f"{category}: {entry.name} ({int(age_days)}d old)",
                                safety=safety
                            ))
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
        except (OSError, PermissionError):
            # Skip directories we can't access
            pass

        return items

    def clean(self, items: List[CleanableItem]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            'success': True,
            'cleaned_count': 0,
            'total_size': 0,
            'errors': []
        }

        for item in items:
            try:
                file_path = Path(item.path)
                if file_path.exists() and file_path.is_file():
                    size = file_path.stat().st_size
                    file_path.unlink()
                    result['cleaned_count'] += 1
                    result['total_size'] += size
            except (OSError, PermissionError) as e:
                result['errors'].append(f"Failed to delete {item.path}: {e}")
                result['success'] = False

        return result

    def is_available(self) -> bool:
        """Temp files cleaning is always available."""
        user_cache = self.home_dir / '.cache'
        system_tmp = Path('/tmp')
        return user_cache.exists() or system_tmp.exists()

    def supports_dry_run(self) -> bool:
        return True

    def clean_dry_run(self, items: List[CleanableItem]) -> Dict[str, Any]:
        return {
            'success': True,
            'cleaned_count': len(items),
            'total_size': sum(item.size for item in items),
            'errors': [],
            'dry_run': True
        }

    def get_priority(self) -> int:
        """Lower priority since temp files are less critical."""
        return 60
