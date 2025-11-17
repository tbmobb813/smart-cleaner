import os
from pathlib import Path
from typing import Any, Optional

# tomllib is stdlib in Python 3.11+. Fall back to tomli for older versions.
try:
    import tomllib  # type: ignore
except Exception:  # pragma: no cover - platform dependent
    try:
        import tomli as tomllib  # type: ignore
    except Exception:
        tomllib = None  # type: ignore


def _config_file_path() -> Path:
    xdg = os.getenv('XDG_CONFIG_HOME')
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / '.config'
    return base / 'smartcleaner' / 'config.toml'


def load_config() -> dict[str, Any]:
    """Load TOML configuration from XDG config path. Returns empty dict on error."""
    if tomllib is None:
        return {}
    p = _config_file_path()
    if not p.exists():
        return {}
    try:
        with p.open('rb') as f:
            data = tomllib.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        return {}
    return {}


def get_keep_kernels(default: Optional[int] = None) -> Optional[int]:
    """Return configured keep_kernels value.

    Precedence: environment SMARTCLEANER_KEEP_KERNELS > config file > default
    """
    env = os.getenv('SMARTCLEANER_KEEP_KERNELS')
    if env:
        try:
            return int(env)
        except Exception:
            pass

    cfg = load_config()
    v = cfg.get('keep_kernels') if isinstance(cfg, dict) else None
    if v is not None:
        try:
            return int(v)
        except Exception:
            return default

    return default


def get_db_path(default: Optional[str] = None) -> Optional[str]:
    env = os.getenv('SMARTCLEANER_DB_PATH')
    if env:
        return env
    cfg = load_config()
    return cfg.get('db_path', default) if isinstance(cfg, dict) else default
