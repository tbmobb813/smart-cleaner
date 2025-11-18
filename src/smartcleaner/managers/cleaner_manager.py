from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import IntEnum
import logging

from .plugin_registry import PluginRegistry, get_default_registry
from .safety_validator import SafetyValidator
from .undo_manager import UndoManager
from ..db.operations import DatabaseManager

logger = logging.getLogger(__name__)


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
    """Orchestrates scanning and cleaning operations across all registered plugins.

    The CleanerManager uses a PluginRegistry to discover available plugins,
    SafetyValidator to enforce safety policies, and UndoManager to support
    undo/restore operations.
    """

    def __init__(
        self,
        plugin_registry: Optional[PluginRegistry] = None,
        safety_validator: Optional[SafetyValidator] = None,
        undo_manager: Optional[UndoManager] = None,
        db_manager: Optional[DatabaseManager] = None
    ):
        """Initialize the CleanerManager.

        Args:
            plugin_registry: Registry of plugins (uses default if None).
            safety_validator: Safety validator (creates default if None).
            undo_manager: Undo manager for backup/restore (creates default if None).
            db_manager: Database manager (creates default if None).
        """
        self.registry = plugin_registry or get_default_registry()
        self.safety_validator = safety_validator or SafetyValidator()
        self.db = db_manager or DatabaseManager()
        self.undo_manager = undo_manager or UndoManager(db=self.db)

    def scan_all(self, safety_filter: Optional[SafetyLevel] = None) -> Dict[str, List[CleanableItem]]:
        """Scan all available plugins and return cleanable items.

        Args:
            safety_filter: Maximum safety level to include (None = all items).

        Returns:
            Dictionary mapping plugin names to lists of CleanableItem instances.
        """
        results = {}

        # Get only available plugins
        plugins = self.registry.get_available_plugins()
        logger.info(f"Scanning with {len(plugins)} available plugins")

        for plugin in plugins:
            try:
                logger.debug(f"Scanning plugin: {plugin.get_name()}")
                items = plugin.scan()

                # Apply safety filter if provided
                if safety_filter is not None:
                    items = [item for item in items if item.safety <= safety_filter]

                # Only include plugins that found items
                if items:
                    results[plugin.get_name()] = items
                    total_size = sum(item.size for item in items)
                    logger.info(
                        f"Plugin '{plugin.get_name()}' found {len(items)} items "
                        f"({self._format_size(total_size)})"
                    )

            except Exception as e:
                logger.error(f"Error scanning plugin '{plugin.get_name()}': {e}")
                # Continue with other plugins even if one fails

        return results

    def scan_plugin(self, plugin_name: str, safety_filter: Optional[SafetyLevel] = None) -> List[CleanableItem]:
        """Scan a specific plugin by name.

        Args:
            plugin_name: Name of the plugin to scan.
            safety_filter: Maximum safety level to include (None = all items).

        Returns:
            List of CleanableItem instances from the plugin.

        Raises:
            ValueError: If the plugin is not found or not available.
        """
        plugin = self.registry.get_plugin(plugin_name)
        if plugin is None:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        if not plugin.is_available():
            raise ValueError(f"Plugin '{plugin_name}' is not available on this system")

        items = plugin.scan()

        # Apply safety filter
        if safety_filter is not None:
            items = [item for item in items if item.safety <= safety_filter]

        return items

    def clean_selected(
        self,
        items_by_plugin: Dict[str, List[CleanableItem]],
        dry_run: bool = False,
        enforce_safety: bool = True
    ) -> Dict[str, Dict]:
        """Clean selected items across multiple plugins.

        Args:
            items_by_plugin: Dictionary mapping plugin names to lists of items to clean.
            dry_run: If True, don't actually clean (just report what would happen).
            enforce_safety: If True, apply safety validator checks.

        Returns:
            Dictionary mapping plugin names to result dictionaries with keys:
                - success: bool
                - cleaned_count: int
                - total_size: int
                - errors: List[str]
                - dry_run: bool (only if dry_run=True)
        """
        results = {}

        for plugin_name, items in items_by_plugin.items():
            plugin = self.registry.get_plugin(plugin_name)
            if plugin is None:
                logger.error(f"Plugin '{plugin_name}' not found")
                results[plugin_name] = {
                    'success': False,
                    'cleaned_count': 0,
                    'total_size': 0,
                    'errors': [f"Plugin '{plugin_name}' not found"]
                }
                continue

            # Apply safety validation if enforced
            if enforce_safety:
                allowed_items = [item for item in items if self.safety_validator.is_allowed(item)]
                filtered_count = len(items) - len(allowed_items)
                if filtered_count > 0:
                    logger.warning(
                        f"Filtered {filtered_count} items from '{plugin_name}' "
                        f"due to safety policy"
                    )
                items = allowed_items

            # Skip if no items remain
            if not items:
                results[plugin_name] = {
                    'success': True,
                    'cleaned_count': 0,
                    'total_size': 0,
                    'errors': []
                }
                continue

            # Perform cleaning
            try:
                if dry_run and plugin.supports_dry_run():
                    result = plugin.clean_dry_run(items)
                elif dry_run:
                    # Plugin doesn't support dry-run, simulate it
                    result = {
                        'success': True,
                        'cleaned_count': len(items),
                        'total_size': sum(item.size for item in items),
                        'errors': [],
                        'dry_run': True
                    }
                else:
                    # Backup items before cleaning (via UndoManager)
                    operation_id = self.undo_manager.log_operation(plugin_name, items)
                    logger.info(f"Created backup operation {operation_id} for '{plugin_name}'")

                    # Perform actual cleaning
                    result = plugin.clean(items)

                    # Log to database
                    self.db.log_clean_operation(
                        plugin_name=plugin_name,
                        items_count=result.get('cleaned_count', 0),
                        size_freed=result.get('total_size', 0),
                        success=result.get('success', False),
                        error_message='; '.join(result.get('errors', []))
                    )

                results[plugin_name] = result
                logger.info(
                    f"Cleaned {result['cleaned_count']} items from '{plugin_name}' "
                    f"({self._format_size(result['total_size'])})"
                )

            except Exception as e:
                logger.error(f"Error cleaning with plugin '{plugin_name}': {e}")
                results[plugin_name] = {
                    'success': False,
                    'cleaned_count': 0,
                    'total_size': 0,
                    'errors': [str(e)]
                }

        return results

    def set_safety_level(self, level: SafetyLevel) -> None:
        """Set the maximum safety level allowed by the safety validator.

        Args:
            level: The new maximum safety level.
        """
        self.safety_validator.set_max_level(level)
        logger.info(f"Safety level set to: {level.name}")

    def get_available_plugins(self) -> List[str]:
        """Get names of all available plugins.

        Returns:
            List of plugin names that are available on this system.
        """
        return [p.get_name() for p in self.registry.get_available_plugins()]

    def _format_size(self, bytes_val: int) -> str:
        """Format byte size as human-readable string."""
        val = float(bytes_val)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if val < 1024.0:
                return f"{val:.2f} {unit}"
            val /= 1024.0
        return f"{val:.2f} PB"
