from click.testing import CliRunner
from pathlib import Path
import os

from smartcleaner.cli.commands import cli
from smartcleaner.config import _config_file_path, load_config


def test_config_set_writes_file(tmp_path, monkeypatch):
    # Ensure XDG points to our tmp dir
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))

    runner = CliRunner()
    # run set command with --yes to avoid confirmation prompt
    result = runner.invoke(cli, ['config', 'set', 'keep_kernels', '9', '--yes'])
    assert result.exit_code == 0

    cfg = load_config()
    assert cfg.get('keep_kernels') == 9
