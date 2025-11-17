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

# Optionally use tomlkit for writing richer TOML with comments/order preserved
try:
    import tomlkit  # type: ignore
except Exception:
    tomlkit = None  # type: ignore


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


_ALLOWED_KEYS = {
    'keep_kernels': int,
    'db_path': str,
}


def save_config(cfg: dict[str, Any]) -> bool:
    """Save a flat config dict to the XDG config TOML file.

    Only supports simple scalar types (int, str, bool). Returns True on
    success, False otherwise.
    """
    p = _config_file_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if tomlkit is not None:
            # Use tomlkit to preserve structure and comments where possible
            doc = tomlkit.document()
            for k, v in cfg.items():
                doc[k] = v
            with p.open('w', encoding='utf8') as f:
                f.write(tomlkit.dumps(doc))
            return True

        # Fallback: write simple scalar TOML
        with p.open('w', encoding='utf8') as f:
            for k, v in cfg.items():
                if isinstance(v, bool):
                    val = 'true' if v else 'false'
                elif isinstance(v, int):
                    val = str(v)
                else:
                    s = str(v).replace('"', '\\"')
                    val = '"' + s + '"'
                f.write(f"{k} = {val}\n")
        return True
    except Exception:
        return False


def set_config_value(key: str, value: Any) -> bool:
    """Set a single config key (with validation) and persist it.

    Returns True on success, False on validation or IO errors.
    """
    if key not in _ALLOWED_KEYS:
        return False
    expected = _ALLOWED_KEYS[key]
    try:
        if expected is int:
            cast_v = int(value)
        elif expected is str:
            cast_v = str(value)
        else:
            cast_v = value
    except Exception:
        return False

    cfg = load_config() or {}
    cfg[key] = cast_v
    return save_config(cfg)


def get_allowed_keys() -> dict:
    return _ALLOWED_KEYS.copy()


def get_effective_value(key: str, code_default: Any = None) -> dict[str, Any] | None:
    """Return a dict with env/config/code default/effective for a key.

    Returns None if key is not allowed.
    """
    if key not in _ALLOWED_KEYS:
        return None

    env = os.getenv('SMARTCLEANER_' + key.upper())
    cfg = load_config() or {}
    cfg_val = cfg.get(key)

    # derive code default if not provided
    eff_default = code_default
    # special-case known keys
    if key == 'keep_kernels' and eff_default is None:
        try:
            # import KernelCleaner to discover default
            from . import __path__ as _p  # noqa: F401
        except Exception:
            pass

    # compute effective precedence env > config > code_default
    if env is not None:
        try:
            effective = int(env) if _ALLOWED_KEYS[key] is int else env
        except Exception:
            effective = env
    elif cfg_val is not None:
        effective = cfg_val
    else:
        effective = eff_default

    return {'env': env, 'config': cfg_val, 'code_default': eff_default, 'effective': effective}
