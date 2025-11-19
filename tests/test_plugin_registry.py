"""Tests for the plugin registry system."""

from typing import Any

from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel
from smartcleaner.managers.plugin_registry import PluginRegistry
from smartcleaner.plugins.base import BasePlugin


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""

    def get_name(self) -> str:
        return "Mock Plugin"

    def get_description(self) -> str:
        return "A mock plugin for testing"

    def scan(self) -> list[CleanableItem]:
        return [CleanableItem(path="/tmp/test", size=1024, description="Test item", safety=SafetyLevel.SAFE)]

    def clean(self, items: list[CleanableItem]) -> dict[str, Any]:
        return {
            "success": True,
            "cleaned_count": len(items),
            "total_size": sum(item.size for item in items),
            "errors": [],
        }


def test_registry_creation():
    """Test creating a new registry."""
    registry = PluginRegistry()
    assert len(registry.get_all_plugins()) == 0


def test_register_plugin():
    """Test registering a plugin instance."""
    registry = PluginRegistry()
    plugin = MockPlugin()
    registry.register_plugin(plugin)

    assert len(registry.get_all_plugins()) == 1
    assert registry.get_plugin("Mock Plugin") == plugin


def test_register_plugin_class():
    """Test registering a plugin class."""
    registry = PluginRegistry()
    registry.register_plugin_class(MockPlugin)

    assert len(registry.get_all_plugins()) == 1
    assert registry.get_plugin("Mock Plugin") is not None


def test_get_available_plugins():
    """Test getting available plugins."""
    registry = PluginRegistry()
    registry.register_plugin_class(MockPlugin)

    available = registry.get_available_plugins()
    assert len(available) == 1


def test_unregister_plugin():
    """Test unregistering a plugin."""
    registry = PluginRegistry()
    registry.register_plugin_class(MockPlugin)

    assert len(registry.get_all_plugins()) == 1

    success = registry.unregister_plugin("Mock Plugin")
    assert success
    assert len(registry.get_all_plugins()) == 0


def test_clear_registry():
    """Test clearing all plugins from registry."""
    registry = PluginRegistry()
    registry.register_plugin_class(MockPlugin)
    registry.register_plugin_class(MockPlugin)

    registry.clear()
    assert len(registry.get_all_plugins()) == 0


def test_discover_default_plugins():
    """Test automatic discovery of default plugins."""
    registry = PluginRegistry()
    registry.discover_and_register_default_plugins()

    # Should register APT, Kernels, Browser, Temp, Thumbnails, Journals
    assert len(registry.get_all_plugins()) == 6

    plugin_names = registry.get_plugin_names()
    assert "APT Package Cache" in plugin_names
    assert "Old Kernels" in plugin_names
    assert "Browser Cache" in plugin_names
    assert "Temporary Files" in plugin_names
    assert "Thumbnail Cache" in plugin_names
    assert "Systemd Journal Logs" in plugin_names
