from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import IntEnum


class SafetyLevel(IntEnum):
    SAFE = 0
    CAUTION = 1
    ADVANCED = 2
    DANGEROUS = 3


@dataclass
class CleanableItem:
    path: str
    size: int
    description: str
    safety: SafetyLevel

    def get_size_human(self) -> str:
        """Return a human-readable size string without mutating self.size."""
        bytes_val = float(self.size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"


class CleanerManager:
    """A small stub of the real CleanerManager used by the GUI skeleton.

    Replace this with the full implementation from your core when wiring the GUI.
    """

    def __init__(self):
        pass

    def scan_all(self, safety_filter: Optional[SafetyLevel] = None) -> Dict[str, List[CleanableItem]]:
        # Return sample data to drive the UI
        results = {
            "APT Package Cache": [
                CleanableItem(path="/var/cache/apt/archives/package1.deb", size=5 * 1024 * 1024, description="Cached package: package1.deb", safety=SafetyLevel.SAFE),
                CleanableItem(path="/var/cache/apt/archives/partial/file.part", size=200 * 1024, description="Partial download: file.part", safety=SafetyLevel.CAUTION),
            ],
            "Old Kernels": [
                CleanableItem(path="linux-image-5.4.0-42-generic", size=350 * 1024 * 1024, description="Old kernel: 5.4.0-42", safety=SafetyLevel.SAFE)
            ]
        }

        # Apply safety filter if provided
        if safety_filter is None:
            return results

        filtered = {}
        for plugin_name, items in results.items():
            allowed = [item for item in items if item.safety <= safety_filter]
            if allowed:
                filtered[plugin_name] = allowed

        return filtered

        if safety_filter is None:
            return items

        # Filter items by safety level (include items with safety <= filter level)
        filtered: Dict[str, List[CleanableItem]] = {}
        for plugin, plugin_items in items.items():
            filtered_items = [it for it in plugin_items if it.safety <= safety_filter]
            if filtered_items:
                filtered[plugin] = filtered_items
        return filtered

    def clean_selected(self, items_by_plugin: Dict[str, List[CleanableItem]], dry_run: bool = False):
        result = {}
        for plugin, items in items_by_plugin.items():
            cleaned_count = len(items)
            total_size = sum(item.size for item in items)
            result[plugin] = {
                'success': True,
                'cleaned_count': cleaned_count,
                'total_size': total_size,
                'errors': []
            }
        return result