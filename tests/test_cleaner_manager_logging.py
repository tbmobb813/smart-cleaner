from smartcleaner.managers.cleaner_manager import CleanableItem, CleanerManager, SafetyLevel


def test_clean_selected_logs_operation(monkeypatch):
    # Prepare a fake plugin that reports success
    class FakePlugin:
        def get_name(self):
            return "Fake Plugin"

        def scan(self):
            return [CleanableItem(path="/tmp/fake", size=1024, description="fake", safety=SafetyLevel.SAFE)]

        def clean(self, items):
            return {"success": True, "cleaned_count": len(items), "total_size": sum(i.size for i in items)}

    plugin = FakePlugin()

    # Capture calls to UndoManager.log_operation
    import smartcleaner.managers.undo_manager as undo_mod

    calls = []

    def fake_log(self, plugin_name, items):
        calls.append((plugin_name, items))
        return 999

    monkeypatch.setattr(undo_mod.UndoManager, "log_operation", fake_log)

    mgr = CleanerManager()
    # Inject our fake plugin instance
    mgr.plugins[plugin.get_name()] = plugin

    items = plugin.scan()
    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)

    # Ensure our fake log was called and operation_id returned
    assert len(calls) == 1
    assert calls[0][0] == plugin.get_name()
    res = results.get(plugin.get_name(), {})
    assert res.get("success") is True
    assert res.get("operation_id") == 999
