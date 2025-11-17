from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import IntEnum
import importlib
from pathlib import Path


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
        # Discover and instantiate built-in plugins. Fall back to sample data
        # when plugins cannot be imported (tests/environment without apt).
        self.plugins: Dict[str, Any] = {}
        # Try to load a set of known built-in plugin modules. Failure to import
        # any plugin is non-fatal (keeps tests and environments lightweight).
        plugin_modules = [
            'smartcleaner.plugins.apt_cache',
            'smartcleaner.plugins.kernels',
            'smartcleaner.plugins.browser_cache',
            'smartcleaner.plugins.thumbnails',
            'smartcleaner.plugins.tmp_cleaner',
        ]

        for mod_name in plugin_modules:
            try:
                mod = importlib.import_module(mod_name)
                # instantiate first class found with a name matching expected pattern
                for attr in dir(mod):
                    cls = getattr(mod, attr)
                    try:
                        # heuristic: class has get_name and scan methods
                        if callable(cls) and hasattr(cls, '__init__'):
                            inst = cls()  # type: ignore[misc]
                            if hasattr(inst, 'get_name') and hasattr(inst, 'scan'):
                                self.plugins[inst.get_name()] = inst
                                break
                    except Exception:
                        # ignore instantiation errors for plugins
                        continue
            except Exception:
                # ignore missing modules
                continue

    def scan_all(self, safety_filter: Optional[SafetyLevel] = None) -> Dict[str, List[CleanableItem]]:
        results: Dict[str, List[CleanableItem]] = {}
        # If we have discovered plugins, use them.
        if self.plugins:
            for name, plugin in self.plugins.items():
                try:
                    items = plugin.scan()
                    if safety_filter is not None:
                        items = [it for it in items if it.safety <= safety_filter]
                    # include plugin even if it finds no items to keep API stable for callers/tests
                    results[name] = items
                except Exception:
                    # ignore plugin errors and continue
                    results[name] = []
            return results

        # Fallback sample data when plugins aren't available
        results = {
            "APT Package Cache": [
                CleanableItem(path="/var/cache/apt/archives/package1.deb", size=5 * 1024 * 1024, description="Cached package: package1.deb", safety=SafetyLevel.SAFE),
                CleanableItem(path="/var/cache/apt/archives/partial/file.part", size=200 * 1024, description="Partial download: file.part", safety=SafetyLevel.CAUTION),
            ],
            "Old Kernels": [
                CleanableItem(path="linux-image-5.4.0-42-generic", size=350 * 1024 * 1024, description="Old kernel: 5.4.0-42", safety=SafetyLevel.SAFE)
            ]
        }

        if safety_filter is None:
            return results

        filtered = {}
        for plugin_name, items in results.items():
            allowed = [item for item in items if item.safety <= safety_filter]
            if allowed:
                filtered[plugin_name] = allowed

        return filtered

    def clean_selected(self, items_by_plugin: Dict[str, List[CleanableItem]], dry_run: bool = False):
        result = {}
        # import here to avoid circular imports at module import time
        from .undo_manager import UndoManager
        undo = UndoManager()

        for plugin_name, items in items_by_plugin.items():
            plugin = self.plugins.get(plugin_name)
            try:
                if dry_run:
                    # Report what would be done
                    result[plugin_name] = {
                        'success': True,
                        'cleaned_count': len(items),
                        'total_size': sum(i.size for i in items),
                        'errors': []
                    }
                else:
                    if plugin is None:
                        # unknown plugin: skip
                        result[plugin_name] = {
                            'success': False,
                            'cleaned_count': 0,
                            'total_size': 0,
                            'errors': ['unknown plugin']
                        }
                    else:
                        res = plugin.clean(items)
                        # If clean succeeded, log operation and backups where appropriate
                        if res.get('success'):
                            try:
                                op_id = undo.log_operation(plugin_name, items)
                                res['operation_id'] = op_id
                            except Exception:
                                pass
                        result[plugin_name] = res
            except Exception as e:
                result[plugin_name] = {
                    'success': False,
                    'cleaned_count': 0,
                    'total_size': 0,
                    'errors': [str(e)]
                }

        return result