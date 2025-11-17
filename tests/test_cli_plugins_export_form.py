from click.testing import CliRunner
import json

from smartcleaner.cli.commands import cli
from smartcleaner.managers.cleaner_manager import CleanerManager


def test_cli_plugins_export_form_generates_schema_for_kernels():
    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if not factories:
        return

    # try to find the kernels factory if available
    kernels_factory = None
    for f in factories:
        if f.startswith('smartcleaner.plugins.kernels'):
            kernels_factory = f
            break

    # fallback to first factory
    factory = kernels_factory or factories[0]

    runner = CliRunner()
    result = runner.invoke(cli, ['plugins', 'export-form', factory, '--json'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # ensure schema has properties mapping
    assert isinstance(data, dict)
    assert data.get('type') == 'object'
    props = data.get('properties', {})
    assert isinstance(props, dict)

