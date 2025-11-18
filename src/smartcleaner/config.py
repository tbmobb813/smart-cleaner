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


# Prefer tomli_w (tomli-w) for round-trip writing when available, else tomlkit
try:
    import tomli_w  # type: ignore
except Exception:
    tomli_w = None  # type: ignore


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
        # Prefer tomli_w (tomli-w) for writing if available (simple, round-trip)
        if tomli_w is not None:
            try:
                dumped = tomli_w.dumps(cfg)
                with p.open('w', encoding='utf8') as f:
                    f.write(dumped)
                return True
            except Exception:
                # fall through to other methods
                pass

        if tomlkit is not None:
            # Use tomlkit to preserve structure and comments where possible
            doc = tomlkit.document()
            for k, v in cfg.items():
                doc[k] = v
            with p.open('w', encoding='utf8') as f:
                f.write(tomlkit.dumps(doc))
            return True

        # Fallback: write simple scalar TOML
        def _toml_scalar(val: Any) -> str:
            # simple TOML scalar serializer for fallback path
            if isinstance(val, bool):
                return 'true' if val else 'false'
            if isinstance(val, int):
                return str(val)
            if isinstance(val, float):
                return str(val)
            if isinstance(val, (list, tuple)):
                items = []
                for it in val:
                    if isinstance(it, bool):
                        items.append('true' if it else 'false')
                    elif isinstance(it, int):
                        items.append(str(it))
                    else:
                        s = str(it).replace('"', '\\"')
                        items.append('"' + s + '"')
                return '[' + ', '.join(items) + ']'
            # fallback to quoted string
            s = str(val).replace('"', '\\"')
            return '"' + s + '"'

        with p.open('w', encoding='utf8') as f:
            for k, v in cfg.items():
                # support nested dicts as TOML tables (only one level deep expected)
                if isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if isinstance(sub_v, dict):
                            # write a table for nested dict under key
                            f.write(f"[{k}.\"{sub_k}\"]\n")
                            for kk, vv in sub_v.items():
                                f.write(f"{kk} = {_toml_scalar(vv)}\n")
                            f.write('\n')
                        else:
                            f.write(f"{k}.{sub_k} = {_toml_scalar(sub_v)}\n")
                else:
                    f.write(f"{k} = {_toml_scalar(v)}\n")
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
        cast_v: Any
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
            # import KernelCleaner to discover class-level default
            from .plugins.kernels import KernelCleaner

            eff_default = getattr(KernelCleaner, 'KERNELS_TO_KEEP', eff_default)
        except Exception:
            pass

    # compute effective precedence env > config > code_default
    effective: Any
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


def _parse_value_by_type(type_name: str, raw_value: Any):
    """Parse raw_value according to a small set of supported type names.

    Supported types: int, str, bool, path, list[path], list[str]
    Returns the parsed/converted value or raises ValueError on parse error.
    """
    from pathlib import Path

    if raw_value is None:
        return None

    t = type_name.strip().lower()
    if t == 'int' or t == 'integer':
        try:
            return int(raw_value)
        except Exception as e:
            raise ValueError(f"Invalid int value: {raw_value}") from e
    if t == 'str' or t == 'string':
        return str(raw_value)
    if t == 'bool' or t == 'boolean':
        if isinstance(raw_value, bool):
            return raw_value
        s = str(raw_value).strip().lower()
        if s in ('1', 'true', 'yes', 'on'):
            return True
        if s in ('0', 'false', 'no', 'off'):
            return False
        raise ValueError(f"Invalid boolean value: {raw_value}")
    if t == 'path':
        return Path(str(raw_value))
    if t.startswith('list'):
        # forms: list[path], list[str]
        inner = t[t.find('[') + 1:t.find(']')] if '[' in t and ']' in t else 'str'
        if isinstance(raw_value, (list, tuple)):
            items = list(raw_value)
        else:
            # accept comma-separated string
            items = [s.strip() for s in str(raw_value).split(',') if s.strip()]
        if inner == 'path':
            return [Path(i) for i in items]
        return [str(i) for i in items]

    # Unknown type, return as-is
    return raw_value


def validate_plugin_config(module_name: str, key: str, raw_value: Any):
    """Validate and parse a plugin config value according to PLUGIN_INFO schema.

    module_name: module path (e.g., 'smartcleaner.plugins.kernels')
    key: config key defined in PLUGIN_INFO['config']
    raw_value: value to validate (string or typed)

    Returns the parsed value on success. Raises ValueError on validation error.
    """
    try:
        mod = __import__(module_name, fromlist=['PLUGIN_INFO'])
    except Exception as e:
        raise ValueError(f"Could not import module {module_name}: {e}") from e

    info = getattr(mod, 'PLUGIN_INFO', None)
    if not info or not isinstance(info, dict):
        raise ValueError(f"Module {module_name} has no PLUGIN_INFO")

    cfg = info.get('config') or {}
    if key not in cfg:
        raise ValueError(f"Config key '{key}' not defined for plugin {module_name}")

    schema = cfg[key]
    # schema is expected to be a dict with 'type' and optional constraints
    expected_type = schema.get('type', 'str')
    parsed = _parse_value_by_type(expected_type, raw_value)

    # numeric bounds
    # treat 'int' and 'integer' as equivalent in schema
    if expected_type in ('int', 'integer'):
        mn = schema.get('min')
        mx = schema.get('max')
        try:
            ival = int(parsed)
        except Exception:
            raise ValueError(f"Value for {key} is not an integer: {raw_value}")
        if mn is not None and ival < mn:
            raise ValueError(f"Value for {key} ({ival}) is less than minimum {mn}")
        if mx is not None and ival > mx:
            raise ValueError(f"Value for {key} ({ival}) is greater than maximum {mx}")

    # choices
    choices = schema.get('choices')
    if choices is not None:
        # support lists of strings or ints
        if parsed not in choices:
            raise ValueError(f"Value for {key} ({parsed}) not in allowed choices {choices}")

    return parsed


def set_plugin_config(module_name: str, key: str, raw_value: Any) -> bool:
    """Validate and persist a plugin-scoped config value under the XDG config.

    The value is validated/parsed via validate_plugin_config and then stored
    under the TOML `[plugins.<module_name>]` table. Returns True on success.
    """
    parsed = validate_plugin_config(module_name, key, raw_value)

    # serialize types for TOML
    def _serialize(v: Any):
        from pathlib import Path

        if v is None:
            return None
        if isinstance(v, Path):
            return str(v)
        if isinstance(v, list):
            # convert inner Paths to strings
            return [_serialize(i) for i in v]
        return v

    cfg = load_config() or {}
    plugins = cfg.get('plugins') or {}
    # ensure nested dicts are plain dicts
    if not isinstance(plugins, dict):
        plugins = {}
    plugin_cfg = plugins.get(module_name) or {}
    if not isinstance(plugin_cfg, dict):
        plugin_cfg = {}

    plugin_cfg[key] = _serialize(parsed)
    plugins[module_name] = plugin_cfg
    cfg['plugins'] = plugins

    return save_config(cfg)


def get_plugin_config(module_name: str, key: str):
    """Return the stored plugin config value (parsed) or None if absent."""
    cfg = load_config() or {}
    plugins = cfg.get('plugins') or {}
    plugin_cfg = plugins.get(module_name) or {}
    return plugin_cfg.get(key)
