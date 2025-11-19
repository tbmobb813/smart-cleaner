from __future__ import annotations

from typing import Any


def _map_type(t: str) -> dict[str, Any]:
    t = t.strip().lower()
    if t == 'int' or t == 'integer':
        return {'type': 'integer'}
    if t in ('str', 'string'):
        return {'type': 'string'}
    if t in ('bool', 'boolean'):
        return {'type': 'boolean'}
    if t == 'path':
        # paths are strings in JSON Schema; GUI can map to file-picker
        return {'type': 'string', 'format': 'path'}
    if t.startswith('list'):
        # list[path] or list[str]
        inner = 'string'
        if '[' in t and ']' in t:
            inner = t[t.find('[') + 1:t.find(']')].strip()
        item_schema = _map_type(inner)
        return {'type': 'array', 'items': item_schema}
    # fallback
    return {'type': 'string'}


def plugin_info_to_json_schema(module_name: str) -> dict[str, Any]:
    """Convert a plugin's PLUGIN_INFO into a JSON Schema (draft-like dict).

    The returned schema describes plugin-config keys (PLUGIN_INFO['config']).
    Constructor metadata is included under the `x_constructor` vendor extension.
    """
    try:
        mod = __import__(module_name, fromlist=['PLUGIN_INFO'])
    except Exception as e:
        raise ImportError(f"Cannot import module {module_name}: {e}") from e

    info = getattr(mod, 'PLUGIN_INFO', {}) or {}
    title = info.get('name') or module_name
    description = info.get('description', '')

    schema: dict[str, Any] = {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'title': title,
        'description': description,
        'type': 'object',
        'properties': {},
        'required': [],
    }

    config = info.get('config', {}) or {}
    for key, spec in config.items():
        if not isinstance(spec, dict):
            # skip malformed
            continue
        prop = _map_type(spec.get('type', 'string'))
        # defaults: prefer code_default then default
        if 'code_default' in spec:
            prop['default'] = spec.get('code_default')
        elif 'default' in spec:
            prop['default'] = spec.get('default')

        if 'description' in spec:
            prop['description'] = spec.get('description')

        if 'min' in spec and prop.get('type') in ('integer', 'number'):
            prop['minimum'] = spec.get('min')
        if 'max' in spec and prop.get('type') in ('integer', 'number'):
            prop['maximum'] = spec.get('max')
        if 'choices' in spec:
            prop['enum'] = spec.get('choices')

        schema['properties'][key] = prop
        if spec.get('required'):
            schema['required'].append(key)

    # attach constructor metadata as vendor extension
    schema['x_constructor'] = info.get('constructor', {})

    # tidy required
    if not schema['required']:
        schema.pop('required')

    return schema
