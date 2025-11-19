import logging
import os
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from ..db.operations import DatabaseManager
from ..plugins.base import BasePlugin
from .plugin_registry import PluginRegistry, get_default_registry
from .safety_validator import SafetyValidator
from .undo_manager import UndoManager
from .plugin_runner import run_subprocess

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
        for unit in ["B", "KB", "MB", "GB", "TB"]:
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
        plugin_registry: PluginRegistry | None = None,
        safety_validator: SafetyValidator | None = None,
        undo_manager: UndoManager | None = None,
        db_manager: DatabaseManager | None = None,
    ):
        """Initialize the CleanerManager.

        Args:
            plugin_registry: Registry of plugins (uses default if None).
            safety_validator: Safety validator (creates default if None).
            undo_manager: Undo manager for backup/restore (creates default if None).
            db_manager: Database manager (creates default if None).
        """
        self.registry = plugin_registry or get_default_registry()
        # Mirror of plugin instances for easy injection and testability
        self.plugins: dict[str, BasePlugin] = {p.get_name(): p for p in self.registry.get_all_plugins()}
        # mapping of factory keys (module:Class) to class objects when discoverable
        self.plugin_factories: dict[str, type[BasePlugin] | None] = {}
        try:
            # populate plugin_factories lazily from available factories
            for fk in self.list_available_factories():
                module_name, class_name = fk.split(":", 1)
                try:
                    mod = __import__(module_name, fromlist=[class_name])
                    cls = getattr(mod, class_name, None)
                except Exception:
                    cls = None
                self.plugin_factories[fk] = cls
        except Exception:
            # non-fatal: leave mapping empty on any discovery/import errors
            self.plugin_factories = {}
        self.safety_validator = safety_validator or SafetyValidator()
        self.db = db_manager or DatabaseManager()
        self.undo_manager = undo_manager or UndoManager(db=self.db)
        # If True, run plugin scan/clean methods in subprocesses for isolation.
        # Can be enabled via env var SMARTCLEANER_PLUGIN_ISOLATION=1 or by passing
        # plugin_isolation=True to the constructor.
        self.plugin_isolation = bool(
            int(os.environ.get("SMARTCLEANER_PLUGIN_ISOLATION", "0"))
        )

    def scan_all(self, safety_filter: SafetyLevel | None = None) -> dict[str, list[CleanableItem]]:
        """Scan all available plugins and return cleanable items.

        Args:
            safety_filter: Maximum safety level to include (None = all items).

        Returns:
            Dictionary mapping plugin names to lists of CleanableItem instances.
        """
        results = {}

        # Prefer explicitly injected/registered plugin instances in self.plugins
        plugin_instances = list(self.plugins.values()) if self.plugins else self.registry.get_available_plugins()
        logger.info(f"Scanning with {len(plugin_instances)} available plugins")

        for plugin in plugin_instances:
            try:
                logger.debug(f"Scanning plugin: {plugin.get_name()}")
                if self.plugin_isolation:
                    # run scan in subprocess; expect a list of dicts
                    res = run_subprocess(plugin.__class__.__module__, plugin.__class__.__name__, "scan")
                    # convert dicts to CleanableItem
                    items = []
                    for it in res:
                        size = it.get("size") or it.get("size_bytes") or 0
                        safety = it.get("safety", "SAFE")
                        try:
                            safety_lvl = SafetyLevel[safety]
                        except Exception:
                            # fallback to SAFE
                            safety_lvl = SafetyLevel.SAFE
                        items.append(
                            CleanableItem(path=it.get("path", ""), size=int(size), description=it.get("description", ""), safety=safety_lvl)
                        )
                else:
                    items = plugin.scan()

                # Apply safety filter if provided
                if safety_filter is not None:
                    items = [item for item in items if item.safety <= safety_filter]

                # Include plugin in results even if no items were found; callers
                # may expect a mapping of all discovered plugins to their items.
                results[plugin.get_name()] = items
                if items:
                    total_size = sum(item.size for item in items)
                    plugin_name = plugin.get_name()
                    logger.info(f"Plugin '{plugin_name}' found {len(items)} items ({self._format_size(total_size)})")

            except Exception as e:
                logger.error(f"Error scanning plugin '{plugin.get_name()}': {e}")
                # Continue with other plugins even if one fails

        return results

    def refresh_plugins(self) -> None:
        """Refresh the internal `plugins` mapping from the registry."""
        self.plugins = {p.get_name(): p for p in self.registry.get_all_plugins()}

    def list_available_factories(self) -> list[str]:
        """Return a list of available plugin factory module names (e.g., smartcleaner.plugins.kernels).

        This inspects the `smartcleaner.plugins` package for .py files and returns importable module names.
        """
        from pathlib import Path

        pkg_dir = Path(__file__).parent.parent / "plugins"
        keys: list[str] = []
        if not pkg_dir.exists():
            return keys
        for p in pkg_dir.glob("*.py"):
            if p.name in ("__init__.py", "base.py"):
                continue
            module = f"smartcleaner.plugins.{p.stem}"
            # attempt to discover the factory class name: prefer PLUGIN_INFO.class
            try:
                mod = __import__(module, fromlist=["PLUGIN_INFO"])
            except Exception:
                # fall back to module-only listing (no class)
                continue

            cls_name = None
            info = getattr(mod, "PLUGIN_INFO", None)
            if isinstance(info, dict):
                cls_name = info.get("class")

            # try to autodiscover first class inheriting BasePlugin if PLUGIN_INFO missing
            if not cls_name:
                try:
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        try:
                            # avoid importing BasePlugin at module import time too early
                            from ..plugins.base import BasePlugin

                            if isinstance(obj, type) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                                cls_name = obj.__name__
                                break
                        except Exception:
                            continue
                except Exception:
                    cls_name = None

            if cls_name:
                keys.append(f"{module}:{cls_name}")
        return keys

    def get_factories_metadata(self) -> dict[str, dict[str, Any]]:
        """Return metadata about available plugin factories keyed by module name.

        Each entry includes:
            - module
            - class
            - class_obj (if loadable)
            - plugin_info (module.PLUGIN_INFO or None)
            - description
        """
        out: dict[str, dict[str, Any]] = {}
        for factory_key in self.list_available_factories():
            # factory_key is module:Class
            module_name, class_name = factory_key.split(":", 1)
            try:
                mod = __import__(module_name, fromlist=[class_name])
            except Exception:
                out[factory_key] = {
                    "module": module_name,
                    "class": class_name,
                    "class_obj": None,
                    "plugin_info": None,
                    "description": "",
                }
                continue

            plugin_info = getattr(mod, "PLUGIN_INFO", None)
            cls_obj = None
            desc = (getattr(mod, "__doc__", "") or "").strip()

            # prefer PLUGIN_INFO.class when present
            if plugin_info and isinstance(plugin_info, dict):
                cls_name = plugin_info.get("class")
                if cls_name and hasattr(mod, cls_name):
                    cls_obj = getattr(mod, cls_name)
            # otherwise try the provided class_name
            if cls_obj is None:
                try:
                    if hasattr(mod, class_name):
                        cls_obj = getattr(mod, class_name)
                except Exception:
                    cls_obj = None

            out[factory_key] = {
                "module": module_name,
                "class": class_name,
                "class_obj": cls_obj,
                "plugin_info": plugin_info,
                "description": desc,
            }
        return out

    def scan_plugin(self, plugin_name: str, safety_filter: SafetyLevel | None = None) -> list[CleanableItem]:
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

        if self.plugin_isolation:
            res = run_subprocess(plugin.__class__.__module__, plugin.__class__.__name__, "scan")
            items = []
            for it in res:
                size = it.get("size") or it.get("size_bytes") or 0
                safety = it.get("safety", "SAFE")
                try:
                    safety_lvl = SafetyLevel[safety]
                except Exception:
                    safety_lvl = SafetyLevel.SAFE
                items.append(
                    CleanableItem(path=it.get("path", ""), size=int(size), description=it.get("description", ""), safety=safety_lvl)
                )
        else:
            items = plugin.scan()

        # Apply safety filter
        if safety_filter is not None:
            items = [item for item in items if item.safety <= safety_filter]

        return items

    def clean_selected(
        self, items_by_plugin: dict[str, list[CleanableItem]], dry_run: bool = False, enforce_safety: bool = True
    ) -> dict[str, dict]:
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
            # prefer injected/plugin instances in self.plugins (tests may inject fakes)
            plugin = self.plugins.get(plugin_name) or self.registry.get_plugin(plugin_name)
            if plugin is None:
                logger.error(f"Plugin '{plugin_name}' not found")
                results[plugin_name] = {
                    "success": False,
                    "cleaned_count": 0,
                    "total_size": 0,
                    "errors": [f"Plugin '{plugin_name}' not found"],
                }
                continue

            # Apply safety validation if enforced
            if enforce_safety:
                allowed_items = [item for item in items if self.safety_validator.is_allowed(item)]
                filtered_count = len(items) - len(allowed_items)
                if filtered_count > 0:
                    logger.warning(f"Filtered {filtered_count} items from '{plugin_name}' due to safety policy")
                items = allowed_items

            # Skip if no items remain
            if not items:
                results[plugin_name] = {"success": True, "cleaned_count": 0, "total_size": 0, "errors": []}
                continue

            # Perform cleaning
            try:
                if dry_run and plugin.supports_dry_run():
                    if self.plugin_isolation:
                        result = run_subprocess(plugin.__class__.__module__, plugin.__class__.__name__, "clean_dry_run")
                    else:
                        result = plugin.clean_dry_run(items)
                elif dry_run:
                    # Plugin doesn't support dry-run, simulate it
                    result = {
                        "success": True,
                        "cleaned_count": len(items),
                        "total_size": sum(item.size for item in items),
                        "errors": [],
                        "dry_run": True,
                    }
                else:
                    # Perform actual cleaning first; only record operation id on success.
                    if self.plugin_isolation:
                        result = run_subprocess(plugin.__class__.__module__, plugin.__class__.__name__, "clean")
                    else:
                        result = plugin.clean(items)

                    # If cleaning succeeded, create a backup log/operation id
                    try:
                        if result.get("success"):
                            operation_id = self.undo_manager.log_operation(plugin_name, items)
                            result["operation_id"] = operation_id
                            logger.info(f"Created backup operation {operation_id} for '{plugin_name}'")
                    except Exception:
                        # Non-fatal: continue without operation_id
                        pass

                    # Log to database (record whatever result the plugin returned)
                    try:
                        self.db.log_clean_operation(
                            plugin_name=plugin_name,
                            items_count=result.get("cleaned_count", 0),
                            size_freed=result.get("total_size", 0),
                            success=result.get("success", False),
                            error_message="; ".join(result.get("errors", [])),
                        )
                    except Exception:
                        # ignore DB logging failures
                        pass

                results[plugin_name] = result
                size_str = self._format_size(result["total_size"])
                logger.info(f"Cleaned {result['cleaned_count']} items from '{plugin_name}' ({size_str})")

            except Exception as e:
                logger.error(f"Error cleaning with plugin '{plugin_name}': {e}")
                results[plugin_name] = {"success": False, "cleaned_count": 0, "total_size": 0, "errors": [str(e)]}

        return results

    def set_safety_level(self, level: SafetyLevel) -> None:
        """Set the maximum safety level allowed by the safety validator.

        Args:
            level: The new maximum safety level.
        """
        self.safety_validator.set_max_level(level)
        logger.info(f"Safety level set to: {level.name}")

    def get_available_plugins(self) -> list[str]:
        """Get names of all available plugins.

        Returns:
            List of plugin names that are available on this system.
        """
        return [p.get_name() for p in self.registry.get_available_plugins()]

    def _format_size(self, bytes_val: int) -> str:
        """Format byte size as human-readable string."""
        val = float(bytes_val)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if val < 1024.0:
                return f"{val:.2f} {unit}"
            val /= 1024.0
        return f"{val:.2f} PB"
