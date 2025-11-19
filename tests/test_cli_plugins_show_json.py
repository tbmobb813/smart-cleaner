import json

from click.testing import CliRunner

from smartcleaner.cli.commands import cli
from smartcleaner.managers.cleaner_manager import CleanerManager


def test_cli_plugins_show_json_output():
    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if not factories:
        return

    factory = factories[0]
    runner = CliRunner()
    result = runner.invoke(cli, ['plugins', 'show', factory, '--json'])
    assert result.exit_code == 0
    # Validate that output is valid JSON and contains expected keys
    data = json.loads(result.output)
    assert data.get('factory_key') == factory
    assert 'plugin_info' in data
    assert 'class' in data
    assert 'constructor' in data
