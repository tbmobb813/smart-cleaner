"""Systemd journal logs cleaner plugin.

Cleans old systemd journal logs to free up disk space.
"""
from pathlib import Path
from typing import List, Dict, Any, TYPE_CHECKING
import re

from ..utils import privilege
from .base import BasePlugin

if TYPE_CHECKING:
    from ..managers.cleaner_manager import CleanableItem, SafetyLevel  # noqa: F401


class SystemdJournalsCleaner(BasePlugin):
    """Cleans old systemd journal logs."""

    def __init__(self, keep_days: int = 30):
        """Initialize the journal cleaner.

        Args:
            keep_days: Keep journal logs for this many days (default: 30).
        """
        self.keep_days = keep_days
        self.journal_dir = Path('/var/log/journal')

    def get_name(self) -> str:
        return "Systemd Journal Logs"

    def get_description(self) -> str:
        return f"Old systemd journal logs (keeps last {self.keep_days} days)."

    def scan(self) -> "List[CleanableItem]":
        items: List = []

        # Use journalctl to get disk usage info
        try:
            result = privilege.run_command(
                ['journalctl', '--disk-usage'],
                sudo=False
            )
            output = str(result.stdout).strip()

            # Parse output like "Archived and active journals take up 512.0M in the file system."
            match = re.search(r'take up ([\d.]+)([KMGT]?)B?', output)
            if match:
                size_value = float(match.group(1))
                size_unit = match.group(2) or ''

                # Convert to bytes
                multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
                size_bytes = int(size_value * multipliers.get(size_unit, 1))

                # Create a single item representing the cleanup operation
                from ..managers.cleaner_manager import CleanableItem, SafetyLevel
                items.append(CleanableItem(
                    path='/var/log/journal',
                    size=size_bytes,
                    description=f"Systemd journal logs (>{self.keep_days} days old)",
                    safety=SafetyLevel.CAUTION
                ))

        except Exception:
            # journalctl not available or permission denied
            pass

        return items

    def clean(self, items: "List[CleanableItem]") -> Dict[str, Any]:
        result: Dict[str, Any] = {
            'success': False,
            'cleaned_count': 0,
            'total_size': 0,
            'errors': []
        }

        if not items:
            result['success'] = True
            return result

        try:
            # Use journalctl --vacuum-time to clean old logs
            privilege.run_command(
                ['journalctl', f'--vacuum-time={self.keep_days}d'],
                sudo=True
            )

            # Estimate cleaned size (approximate)
            result['success'] = True
            result['cleaned_count'] = len(items)
            result['total_size'] = sum(item.size for item in items)

        except PermissionError as e:
            result['errors'].append(f"Permission denied: {e}")
        except Exception as e:
            result['errors'].append(f"Failed to clean journals: {e}")

        return result

    def is_available(self) -> bool:
        """Check if journalctl is available."""
        try:
            privilege.run_command(['which', 'journalctl'], sudo=False)
            return True
        except Exception:
            return False

    def supports_dry_run(self) -> bool:
        return True

    def clean_dry_run(self, items: "List[CleanableItem]") -> Dict[str, Any]:
        return {
            'success': True,
            'cleaned_count': len(items),
            'total_size': sum(item.size for item in items),
            'errors': [],
            'dry_run': True
        }

    def get_priority(self) -> int:
        """Lower priority since journal logs are system-critical."""
        return 70
