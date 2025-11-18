from smartcleaner.plugins.kernels import KernelCleaner


def _make_fake_run(current_kernel, packages):
    def fake_run(cmd, sudo=False, **kwargs):
        class CP:
            def __init__(self, out):
                self.stdout = out

        if cmd[:2] == ['uname', '-r']:
            return CP(current_kernel)
        if cmd[:2] == ['dpkg', '--list']:
            out = '\n'.join([f"ii  {p}  {p.split('linux-image-')[-1]}  amd64  ..." for p in packages])
            return CP(out)
        if cmd[0] == 'dpkg-query':
            return CP('512')
        return CP('')

    return fake_run


def test_kernel_retention_keeps_top_n_and_current(monkeypatch):
    kc = KernelCleaner()

    packages = [
        'linux-image-6.8.0-86-generic',
        'linux-image-6.8.0-85-generic',
        'linux-image-6.8.0-84-generic',
        'linux-image-6.8.0-80-generic',
    ]

    # current is newest
    monkeypatch.setattr('smartcleaner.utils.privilege.run_command', _make_fake_run('6.8.0-86-generic', packages))

    items = kc.scan()

    # Expect removable kernels are 6.8.0-84 and 6.8.0-80
    found_versions = [it.description.split(':')[-1].strip() for it in items]
    assert '6.8.0-84-generic' in found_versions
    assert '6.8.0-80-generic' in found_versions


def test_kernel_retention_keeps_current_even_if_not_top(monkeypatch):
    kc = KernelCleaner()

    packages = [
        'linux-image-6.8.0-86-generic',
        'linux-image-6.8.0-85-generic',
        'linux-image-6.8.0-84-generic',
        'linux-image-6.8.0-80-generic',
    ]

    # current is older (6.8.0-80), ensure it's kept in addition to top N
    monkeypatch.setattr('smartcleaner.utils.privilege.run_command', _make_fake_run('6.8.0-80-generic', packages))

    items = kc.scan()

    # Expect removable kernels: only 6.8.0-84-generic (86,85 and current 80 kept)
    found_versions = [it.description.split(':')[-1].strip() for it in items]
    assert '6.8.0-84-generic' in found_versions
    assert '6.8.0-86-generic' not in found_versions
    assert '6.8.0-85-generic' not in found_versions
    assert '6.8.0-80-generic' not in found_versions
