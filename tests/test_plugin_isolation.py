import os
import json

from smartcleaner.managers.plugin_registry import PluginRegistry
from smartcleaner.managers.cleaner_manager import CleanerManager, SafetyLevel


def test_per_plugin_isolation_scan(monkeypatch):
    # Ensure global isolation OFF
    monkeypatch.delenv("SMARTCLEANER_PLUGIN_ISOLATION", raising=False)

    registry = PluginRegistry()
    # Register the test plugin we added in src/smartcleaner/plugins
    from smartcleaner.plugins.test_isolated_plugin import TestIsolatedPlugin

    registry.register_plugin_class(TestIsolatedPlugin)

    manager = CleanerManager(plugin_registry=registry)

    results = manager.scan_all()
    assert "Test Isolated Plugin" in results
    items = results["Test Isolated Plugin"]
    assert len(items) == 1
    item = items[0]
    assert item.path == "/tmp/testfile"
    assert item.size == 1234
    assert item.safety == SafetyLevel.SAFE
