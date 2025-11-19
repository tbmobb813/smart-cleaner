import json

from click.testing import CliRunner

from smartcleaner.cli.commands import cli
from smartcleaner.managers.cleaner_manager import CleanerManager


def test_kernel_plugin_config_has_min_max():
    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    # find the kernel factory (module:KernelCleaner)
    kernel_factory = None
    for f in factories:
        if f.endswith(":KernelCleaner") or "kernels" in f:
            kernel_factory = f
            break
    if not kernel_factory:
        return

    runner = CliRunner()
    result = runner.invoke(cli, ["plugins", "show", kernel_factory, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    plugin_info = data.get("plugin_info")
    assert isinstance(plugin_info, dict)
    config = plugin_info.get("config")
    assert isinstance(config, dict)
    keep = config.get("keep_kernels")
    assert isinstance(keep, dict)
    # assert min/max and code_default are present
    assert "min" in keep and "max" in keep and "code_default" in keep
    assert keep["min"] == 0
    assert keep["max"] == 50
    assert keep["code_default"] == 2
