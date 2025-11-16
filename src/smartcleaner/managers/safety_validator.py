from typing import Optional
from .cleaner_manager import CleanableItem, SafetyLevel


class SafetyValidator:
    """Simple safety validator for CleanableItem instances.

    This is intentionally small — it centralizes the comparison logic and
    makes it easier to evolve safety policies later (whitelists, blacklists,
    path patterns, time-based rules, etc.).
    """

    def __init__(self, max_level: Optional[SafetyLevel] = None):
        self.max_level = max_level if max_level is not None else SafetyLevel.CAUTION

    def is_allowed(self, item: CleanableItem) -> bool:
        """Return True if the item is allowed to be cleaned under current policy."""
        return item.safety <= self.max_level

    def set_max_level(self, level: SafetyLevel):
        self.max_level = level
