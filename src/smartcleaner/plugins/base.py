"""Base plugin interface for Smart Cleaner plugins.

All plugins should inherit from BasePlugin to ensure a consistent interface.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..managers.cleaner_manager import CleanableItem


class BasePlugin(ABC):
    """Abstract base class for all cleaner plugins."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the display name of this plugin.

        Example: "APT Package Cache" or "Browser Cache"
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return a user-friendly description of what this plugin cleans.

        Example: "Downloaded package files (.deb) and partial downloads from APT cache."
        """
        pass

    @abstractmethod
    def scan(self) -> List[CleanableItem]:
        """Scan for cleanable items and return a list of CleanableItem instances.

        This method should not modify any files, only identify what can be cleaned.

        Returns:
            List of CleanableItem instances representing items that can be cleaned.
        """
        pass

    @abstractmethod
    def clean(self, items: List[CleanableItem]) -> Dict[str, Any]:
        """Clean the specified items.

        Args:
            items: List of CleanableItem instances to clean (typically from a previous scan).

        Returns:
            A dictionary with keys:
                - success: bool indicating overall success
                - cleaned_count: int number of items successfully cleaned
                - total_size: int total bytes freed
                - errors: list of error messages (empty if no errors)
        """
        pass

    def supports_dry_run(self) -> bool:
        """Return True if this plugin supports dry-run mode.

        Dry-run mode means the plugin can report what it would do without
        actually modifying any files.

        Default implementation returns False.
        """
        return False

    def clean_dry_run(self, items: List[CleanableItem]) -> Dict[str, Any]:
        """Perform a dry-run clean operation.

        This should report what would be cleaned without actually cleaning.
        Only called if supports_dry_run() returns True.

        Args:
            items: List of CleanableItem instances that would be cleaned.

        Returns:
            Same structure as clean() method.
        """
        return {
            'success': True,
            'cleaned_count': len(items),
            'total_size': sum(item.size for item in items),
            'errors': [],
            'dry_run': True
        }

    def is_available(self) -> bool:
        """Return True if this plugin is available on the current system.

        For example, an APT plugin would return False on non-Debian systems.

        Default implementation returns True.
        """
        return True

    def get_priority(self) -> int:
        """Return the execution priority for this plugin (lower = earlier).

        Useful for ordering plugins when scanning or cleaning.
        Default is 50 (medium priority).

        Returns:
            Integer priority value (0-100).
        """
        return 50
