"""Plugin registry for automatic plugin discovery and management."""

import logging

from ..plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for managing cleaner plugins.

    The registry maintains a list of available plugins and provides
    methods to discover, register, and retrieve them.
    """

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._plugin_classes: dict[str, type[BasePlugin]] = {}

    def register_plugin(self, plugin: BasePlugin) -> None:
        """Register a plugin instance.

        Args:
            plugin: An instance of a class that inherits from BasePlugin.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        name = plugin.get_name()
        if name in self._plugins:
            logger.warning(f"Plugin '{name}' is already registered. Skipping.")
            return

        self._plugins[name] = plugin
        logger.debug(f"Registered plugin: {name}")

    def register_plugin_class(self, plugin_class: type[BasePlugin], *args, **kwargs) -> None:
        """Register a plugin class and instantiate it.

        Args:
            plugin_class: A class that inherits from BasePlugin.
            *args: Positional arguments to pass to plugin constructor.
            **kwargs: Keyword arguments to pass to plugin constructor.
        """
        try:
            plugin_instance = plugin_class(*args, **kwargs)
            self.register_plugin(plugin_instance)
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {plugin_class.__name__}: {e}")

    def get_plugin(self, name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            name: The name of the plugin (as returned by get_name()).

        Returns:
            The plugin instance, or None if not found.
        """
        return self._plugins.get(name)

    def get_all_plugins(self) -> list[BasePlugin]:
        """Get all registered plugins.

        Returns:
            List of all registered plugin instances.
        """
        return list(self._plugins.values())

    def get_available_plugins(self) -> list[BasePlugin]:
        """Get all plugins that are available on the current system.

        Returns:
            List of plugin instances where is_available() returns True.
        """
        return [p for p in self._plugins.values() if p.is_available()]

    def get_plugin_names(self) -> list[str]:
        """Get names of all registered plugins.

        Returns:
            List of plugin names.
        """
        return list(self._plugins.keys())

    def unregister_plugin(self, name: str) -> bool:
        """Unregister a plugin by name.

        Args:
            name: The name of the plugin to unregister.

        Returns:
            True if the plugin was unregistered, False if not found.
        """
        if name in self._plugins:
            del self._plugins[name]
            logger.debug(f"Unregistered plugin: {name}")
            return True
        return False

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        logger.debug("Cleared all plugins from registry")

    def discover_and_register_default_plugins(self) -> None:
        """Automatically discover and register all built-in plugins."""
        from ..plugins.apt_cache import APTCacheCleaner
        from ..plugins.browser_cache import BrowserCacheCleaner
        from ..plugins.kernels import KernelCleaner
        from ..plugins.systemd_journals import SystemdJournalsCleaner
        from ..plugins.temp_files import TempFilesCleaner
        from ..plugins.thumbnails import ThumbnailCacheCleaner

        # Register built-in plugins
        self.register_plugin_class(APTCacheCleaner)
        self.register_plugin_class(KernelCleaner)
        self.register_plugin_class(BrowserCacheCleaner)
        self.register_plugin_class(TempFilesCleaner)
        self.register_plugin_class(ThumbnailCacheCleaner)
        self.register_plugin_class(SystemdJournalsCleaner)

        logger.info(f"Registered {len(self._plugins)} default plugins")


# Global default registry instance
_default_registry: PluginRegistry | None = None


def get_default_registry() -> PluginRegistry:
    """Get or create the default global plugin registry.

    Returns:
        The global PluginRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = PluginRegistry()
        _default_registry.discover_and_register_default_plugins()
    return _default_registry
