from click.testing import CliRunner

from smartcleaner.cli.commands import cli


def test_cli_uses_config_when_flag_missing(monkeypatch):
    # Make config return a specific keep value
    monkeypatch.setattr('smartcleaner.config.get_keep_kernels', lambda: 4)

    # Fake KernelCleaner to capture the keep parameter
    class FakeKernel:
        created = []

        def __init__(self, keep=None):
            FakeKernel.created.append(keep)

        def get_name(self):
            return 'Old Kernels'

        def scan(self):
            from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel

            return [CleanableItem(path='linux-image-1', size=1024, description='Old kernel: 1', safety=SafetyLevel.SAFE)]

        def clean(self, items):
            return {'success': True, 'cleaned_count': len(items), 'total_size': sum(i.size for i in items)}

    monkeypatch.setattr('smartcleaner.plugins.kernels.KernelCleaner', FakeKernel)

    runner = CliRunner()
    result = runner.invoke(cli, ['clean', 'kernels', '--dry-run'])
    assert result.exit_code == 0
    # At least one instance should have been created with keep==4
    assert 4 in FakeKernel.created
