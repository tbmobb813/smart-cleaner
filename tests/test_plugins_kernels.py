from smartcleaner.plugins.kernels import KernelCleaner
from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel


def test_kernel_scan_and_clean(monkeypatch):
    kc = KernelCleaner()

    # Fake outputs for uname and dpkg --list and dpkg-query
    def fake_run(cmd, sudo=False, **kwargs):
        class CP:
            def __init__(self, out):
                self.stdout = out
        if cmd[:2] == ['uname', '-r']:
            return CP('5.4.0-50-generic')
        if cmd[:2] == ['dpkg', '--list']:
            # provide two installed kernel package lines
            out = '\n'.join([
                'ii  linux-image-5.4.0-50-generic  5.4.0-50  amd64  ...',
                'ii  linux-image-5.4.0-42-generic  5.4.0-42  amd64  ...',
                'ii  linux-image-4.15.0-20-generic  4.15.0-20  amd64  ...',
            ])
            return CP(out)
        if cmd[0] == 'dpkg-query':
            return CP('102400')
        # fallback
        return CP('')

    monkeypatch.setattr('smartcleaner.utils.privilege.run_command', fake_run)

    items = kc.scan()
    # Should find the oldest kernel (4.15) as removable
    assert any('4.15.0-20' in it.description for it in items)

    # Monkeypatch purge/autoremove to be successful
    def fake_run_ok(cmd, sudo=False, **kwargs):
        class CP:
            stdout = ''
            returncode = 0
        return CP()

    monkeypatch.setattr('smartcleaner.utils.privilege.run_command', fake_run_ok)

    res = kc.clean(items)
    assert res['success']
    assert res['cleaned_count'] == len(items)
