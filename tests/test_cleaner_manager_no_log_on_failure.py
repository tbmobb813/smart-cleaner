from smartcleaner.managers.cleaner_manager import CleanerManager, CleanableItem, SafetyLevel


def test_clean_selected_does_not_log_on_failure(monkeypatch):
    # Prepare a fake plugin that reports failure
    class FailPlugin:
        def get_name(self):
            return "Fail Plugin"

        def scan(self):
            return [CleanableItem(path="/tmp/fail", size=512, description="fail", safety=SafetyLevel.SAFE)]

        def clean(self, items):
            return {'success': False, 'errors': ['simulated failure']}

    plugin = FailPlugin()

    # Capture calls to UndoManager.log_operation
    import smartcleaner.managers.undo_manager as undo_mod

    calls = []

    def fake_log(self, plugin_name, items):
        calls.append((plugin_name, items))
        return 123

    monkeypatch.setattr(undo_mod.UndoManager, 'log_operation', fake_log)

    mgr = CleanerManager()
    mgr.plugins[plugin.get_name()] = plugin

    items = plugin.scan()
    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)

    # Ensure no log calls happened and operation_id is absent
    assert len(calls) == 0
    res = results.get(plugin.get_name(), {})
    assert res.get('success') is False
    assert 'operation_id' not in res
