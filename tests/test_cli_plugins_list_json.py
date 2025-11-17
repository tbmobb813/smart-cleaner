from click.testing import CliRunner
import json

from smartcleaner.cli.commands import cli
from smartcleaner.managers.cleaner_manager import CleanerManager


def test_cli_plugins_list_json_contains_expected_fields():
    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if not factories:
        return

    runner = CliRunner()
    result = runner.invoke(cli, ['plugins', 'list', '--json'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    # pick one factory key from manager and ensure it's present in output
    sample = factories[0]
    assert sample in data
    entry = data[sample]
    assert 'module' in entry
    assert 'class' in entry
    assert 'description' in entry

