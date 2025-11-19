from click.testing import CliRunner

from smartcleaner.cli.commands import cli
from smartcleaner.managers.cleaner_manager import CleanerManager


def test_cli_plugins_show_first_factory():
    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if not factories:
        # Nothing to assert in minimal test env
        return

    factory = factories[0]
    runner = CliRunner()
    result = runner.invoke(cli, ["plugins", "show", factory])
    assert result.exit_code == 0
    # output may include the class name rather than the factory key; assert at least
    # the class short name is present
    class_name = factory.split(":", 1)[-1]
    assert class_name in result.output
