from click.testing import CliRunner

from smartcleaner.cli.commands import cli


def test_cli_clean_kernels_passes_keep_flag(monkeypatch):
    # Fake KernelCleaner to capture the keep parameter and provide deterministic scan/clean
    class FakeKernel:
        last_instance = None
        created_keeps = []

        def __init__(self, keep=None):
            FakeKernel.last_instance = self
            self.keep = keep
            FakeKernel.created_keeps.append(keep)

        def get_name(self):
            return 'Old Kernels'

        def scan(self):
            from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel
            return [
                CleanableItem(
                    path='linux-image-1',
                    size=1024,
                    description='Old kernel: 1',
                    safety=SafetyLevel.SAFE,
                )
            ]

        def clean(self, items):
            return {'success': True, 'cleaned_count': len(items), 'total_size': sum(i.size for i in items)}

    monkeypatch.setattr('smartcleaner.plugins.kernels.KernelCleaner', FakeKernel)

    runner = CliRunner()
    result = runner.invoke(cli, ['clean', 'kernels', '--keep-kernels', '3', '--dry-run'])
    assert result.exit_code == 0
    assert FakeKernel.last_instance is not None
    # CleanerManager may instantiate KernelCleaner() during discovery (keep=None). Ensure at least
    # one instantiation received the requested keep value.
    assert 3 in FakeKernel.created_keeps
