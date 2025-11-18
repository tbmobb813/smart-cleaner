
from smartcleaner.config import get_keep_kernels


def test_keep_kernels_from_xdg(tmp_path, monkeypatch):
    cfg_dir = tmp_path
    # Write config under XDG_CONFIG_HOME/smartcleaner/config.toml
    monkeypatch.setenv('XDG_CONFIG_HOME', str(cfg_dir))
    cfg_path = cfg_dir / 'smartcleaner'
    cfg_path.mkdir()
    toml = cfg_path / 'config.toml'
    toml.write_text('keep_kernels = 5\n')

    # Ensure our helper reads the value
    assert get_keep_kernels() == 5


def test_env_overrides_config(tmp_path, monkeypatch):
    cfg_dir = tmp_path
    monkeypatch.setenv('XDG_CONFIG_HOME', str(cfg_dir))
    cfg_path = cfg_dir / 'smartcleaner'
    cfg_path.mkdir()
    toml = cfg_path / 'config.toml'
    toml.write_text('keep_kernels = 2\n')

    monkeypatch.setenv('SMARTCLEANER_KEEP_KERNELS', '7')
    assert get_keep_kernels() == 7
