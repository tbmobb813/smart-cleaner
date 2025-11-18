"""Tests for the updated CleanerManager with plugin orchestration."""
import pytest
from smartcleaner.managers.cleaner_manager import CleanerManager, SafetyLevel, CleanableItem
from smartcleaner.managers.plugin_registry import PluginRegistry
from smartcleaner.plugins.base import BasePlugin
from typing import List, Dict, Any


class TestPlugin(BasePlugin):
    """Test plugin for CleanerManager tests."""

    def __init__(self, name: str = "Test Plugin", items_count: int = 3):
        self.name = name
        self.items_count = items_count
        self.scan_called = False
        self.clean_called = False

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return f"Test plugin: {self.name}"

    def scan(self) -> List[CleanableItem]:
        self.scan_called = True
        return [
            CleanableItem(
                path=f"/tmp/test_{i}",
                size=1024 * (i + 1),
                description=f"Test item {i}",
                safety=SafetyLevel.SAFE
            )
            for i in range(self.items_count)
        ]

    def clean(self, items: List[CleanableItem]) -> Dict[str, Any]:
        self.clean_called = True
        return {
            'success': True,
            'cleaned_count': len(items),
            'total_size': sum(item.size for item in items),
            'errors': []
        }

    def supports_dry_run(self) -> bool:
        return True


def test_cleaner_manager_creation():
    """Test creating a CleanerManager."""
    manager = CleanerManager()
    assert manager is not None
    assert manager.registry is not None
    assert manager.safety_validator is not None


def test_scan_all_with_plugins():
    """Test scanning all plugins."""
    registry = PluginRegistry()
    plugin1 = TestPlugin("Plugin 1", 2)
    plugin2 = TestPlugin("Plugin 2", 3)
    registry.register_plugin(plugin1)
    registry.register_plugin(plugin2)

    manager = CleanerManager(plugin_registry=registry)
    results = manager.scan_all()

    assert len(results) == 2
    assert "Plugin 1" in results
    assert "Plugin 2" in results
    assert len(results["Plugin 1"]) == 2
    assert len(results["Plugin 2"]) == 3
    assert plugin1.scan_called
    assert plugin2.scan_called


def test_scan_with_safety_filter():
    """Test scanning with safety level filter."""
    registry = PluginRegistry()

    class MixedSafetyPlugin(BasePlugin):
        def get_name(self) -> str:
            return "Mixed Safety"

        def get_description(self) -> str:
            return "Plugin with mixed safety levels"

        def scan(self) -> List[CleanableItem]:
            return [
                CleanableItem("/tmp/safe", 100, "Safe item", SafetyLevel.SAFE),
                CleanableItem("/tmp/caution", 200, "Caution item", SafetyLevel.CAUTION),
                CleanableItem("/tmp/advanced", 300, "Advanced item", SafetyLevel.ADVANCED),
            ]

        def clean(self, items: List[CleanableItem]) -> Dict[str, Any]:
            return {'success': True, 'cleaned_count': len(items), 'total_size': 0, 'errors': []}

    registry.register_plugin(MixedSafetyPlugin())
    manager = CleanerManager(plugin_registry=registry)

    # Filter to SAFE only
    results = manager.scan_all(safety_filter=SafetyLevel.SAFE)
    assert len(results["Mixed Safety"]) == 1

    # Filter to CAUTION
    results = manager.scan_all(safety_filter=SafetyLevel.CAUTION)
    assert len(results["Mixed Safety"]) == 2


def test_scan_specific_plugin():
    """Test scanning a specific plugin by name."""
    registry = PluginRegistry()
    plugin = TestPlugin("Specific Plugin", 5)
    registry.register_plugin(plugin)

    manager = CleanerManager(plugin_registry=registry)
    items = manager.scan_plugin("Specific Plugin")

    assert len(items) == 5
    assert plugin.scan_called


def test_scan_missing_plugin():
    """Test scanning a non-existent plugin raises error."""
    manager = CleanerManager(plugin_registry=PluginRegistry())

    with pytest.raises(ValueError, match="not found"):
        manager.scan_plugin("Nonexistent Plugin")


def test_clean_selected():
    """Test cleaning selected items."""
    registry = PluginRegistry()
    plugin = TestPlugin("Clean Test", 3)
    registry.register_plugin(plugin)

    manager = CleanerManager(plugin_registry=registry)
    items = manager.scan_plugin("Clean Test")

    results = manager.clean_selected(
        {"Clean Test": items},
        dry_run=False,
        enforce_safety=False
    )

    assert results["Clean Test"]["success"]
    assert results["Clean Test"]["cleaned_count"] == 3
    assert plugin.clean_called


def test_clean_dry_run():
    """Test dry-run cleaning."""
    registry = PluginRegistry()
    plugin = TestPlugin("Dry Run Test", 2)
    registry.register_plugin(plugin)

    manager = CleanerManager(plugin_registry=registry)
    items = manager.scan_plugin("Dry Run Test")

    results = manager.clean_selected(
        {"Dry Run Test": items},
        dry_run=True
    )

    assert results["Dry Run Test"]["success"]
    assert results["Dry Run Test"].get("dry_run") is True
    # Clean should not be called in dry-run mode for plugins with dry_run support
    # (it will call clean_dry_run instead, which is not tracked by clean_called)


def test_set_safety_level():
    """Test setting safety level."""
    manager = CleanerManager()
    manager.set_safety_level(SafetyLevel.ADVANCED)
    assert manager.safety_validator.max_level == SafetyLevel.ADVANCED


def test_get_available_plugins():
    """Test getting list of available plugin names."""
    registry = PluginRegistry()
    registry.register_plugin(TestPlugin("Plugin A"))
    registry.register_plugin(TestPlugin("Plugin B"))

    manager = CleanerManager(plugin_registry=registry)
    available = manager.get_available_plugins()

    assert len(available) == 2
    assert "Plugin A" in available
    assert "Plugin B" in available
