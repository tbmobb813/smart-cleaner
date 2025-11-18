from smartcleaner.managers.cleaner_manager import CleanerManager


def test_injected_plugin_is_used(monkeypatch):
    mgr = CleanerManager()

    class FakePlugin:
        def get_name(self):
            return 'Injected Plugin'

        def scan(self):
            return ['marker']

    fake = FakePlugin()
    # Inject the plugin instance directly
    mgr.plugins[fake.get_name()] = fake

    results = mgr.scan_all()

    # Our injected plugin should appear in the results and not be overwritten
    assert 'Injected Plugin' in results
    assert results['Injected Plugin'] == ['marker']
