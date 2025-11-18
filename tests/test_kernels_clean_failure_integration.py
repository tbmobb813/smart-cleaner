from smartcleaner.plugins.kernels import KernelCleaner
from smartcleaner.managers.cleaner_manager import CleanerManager


def test_kernel_clean_failure_does_not_log(monkeypatch):
    # Prepare a KernelCleaner instance and fake dpkg/uname outputs for scan
    packages = [
        'linux-image-6.8.0-86-generic',
        'linux-image-6.8.0-85-generic',
        'linux-image-6.8.0-84-generic',
    ]

    def fake_run_scan(cmd, sudo=False, **kwargs):
        class CP:
            def __init__(self, out):
                self.stdout = out

        if cmd[:2] == ['uname', '-r']:
            return CP('6.8.0-86-generic')
        if cmd[:2] == ['dpkg', '--list']:
            out = '\n'.join([f"ii  {p}  {p.split('linux-image-')[-1]}  amd64  ..." for p in packages])
            return CP(out)
        if cmd[0] == 'dpkg-query':
            return CP('512')
        return CP('')

    monkeypatch.setattr('smartcleaner.utils.privilege.run_command', fake_run_scan)

    plugin = KernelCleaner()
    items = plugin.scan()

    # Now simulate a failure for apt-get purge by raising an exception
    def fake_run_fail(cmd, sudo=False, **kwargs):
        if cmd and cmd[0] == 'apt-get' and 'purge' in cmd:
            raise Exception('apt purge failed')
        # reuse scan behavior for other commands
        return fake_run_scan(cmd, sudo=sudo, **kwargs)

    monkeypatch.setattr('smartcleaner.utils.privilege.run_command', fake_run_fail)

    # Replace UndoManager implementation with a fake that records calls at class-level
    class FakeUndo:
        logged = []

        def __init__(self, db=None):
            pass

        def log_operation(self, plugin_name, items):
            FakeUndo.logged.append((plugin_name, items))
            return 123

    # Patch the actual undo_manager module where CleanerManager imports from
    monkeypatch.setattr('smartcleaner.managers.undo_manager.UndoManager', FakeUndo)

    mgr = CleanerManager()
    # ensure manager uses our plugin instance (to avoid re-instantiation)
    mgr.plugins[plugin.get_name()] = plugin

    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)
    res = results.get(plugin.get_name(), {})

    assert res.get('success') is False
    # Ensure FakeUndo did not record any log (log only happens on success)
    assert FakeUndo.logged == []
