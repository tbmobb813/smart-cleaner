from click.testing import CliRunner

from smartcleaner.cli.commands import cli
from smartcleaner.managers.cleaner_manager import CleanerManager


def test_cli_plugin_config_set_get(tmp_path):
    # Use temporary XDG_CONFIG_HOME to avoid touching user config
    env = { 'XDG_CONFIG_HOME': str(tmp_path) }
    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if not factories:
        return
    # pick kernel factory
    factory = next((f for f in factories if f.endswith(':KernelCleaner') or 'kernels' in f), factories[0])

    runner = CliRunner(env=env)
    # set keep_kernels to 3
    r = runner.invoke(cli, ['config', 'plugin', 'set', factory, 'keep_kernels', '3', '--yes'])
    assert r.exit_code == 0
    # get it back
    r2 = runner.invoke(cli, ['config', 'plugin', 'get', factory, 'keep_kernels'])
    assert r2.exit_code == 0
    assert '3' in r2.output


def test_cli_plugin_config_set_validation_error(tmp_path):
    env = { 'XDG_CONFIG_HOME': str(tmp_path) }
    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if not factories:
        return
    factory = next((f for f in factories if f.endswith(':KernelCleaner') or 'kernels' in f), factories[0])

    runner = CliRunner(env=env)
    # set keep_kernels to invalid -1
    # pass '--' before a negative positional to avoid Click treating it as an option
    r = runner.invoke(cli, ['config', 'plugin', 'set', factory, 'keep_kernels', '--yes', '--', '-1'])
    # should not be success
    assert r.exit_code == 0
    assert 'Validation error' in r.output
