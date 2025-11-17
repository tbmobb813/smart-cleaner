# Plugin configuration and JSON form schema

This document describes how per-plugin configuration is stored and how to
export a small JSON "form spec" derived from each plugin's `PLUGIN_INFO`.

Overview
--------

- Per-plugin configuration is stored in your XDG config file:
  `$XDG_CONFIG_HOME/smartcleaner/config.toml` (or `~/.config/smartcleaner/config.toml`).
- Plugin-scoped values live under the `plugins` table keyed by the plugin
  module path, for example:

```toml
[plugins."smartcleaner.plugins.kernels"]
keep_kernels = 3
```

- The CLI provides `config plugin set` and `config plugin get` which validate
  values against the plugin's declared `PLUGIN_INFO['config']` schema before
  persisting. This ensures types, min/max, choices, etc. are enforced.

Why export a form spec?
-----------------------
A JSON form schema (or a small UI form spec) allows GUI frontends or external
tools to render precise input widgets without hard-coding plugin details.
We generate the form spec directly from `PLUGIN_INFO` (the module-level
metadata each plugin provides).

How to generate a simple JSON form spec
--------------------------------------
The following minimal Python snippet prints a JSON object that contains the
`config` schema and `constructor` metadata from `PLUGIN_INFO`.

```python
# scripts/export_plugin_form.py
import json
from importlib import import_module


def export_plugin_form(module_name: str):
    mod = import_module(module_name)
    info = getattr(mod, 'PLUGIN_INFO', {}) or {}
    form = {
        'module': module_name,
        'name': info.get('name'),
        'description': info.get('description'),
        'config': info.get('config', {}),
        'constructor': info.get('constructor', {}),
    }
    print(json.dumps(form, indent=2, default=str))


if __name__ == '__main__':
    # example: replace with any discovered plugin module
    export_plugin_form('smartcleaner.plugins.kernels')
```

Sample output (abridged) for `smartcleaner.plugins.kernels`:

```json
{
  "module": "smartcleaner.plugins.kernels",
  "name": "Old Kernels Cleaner",
  "description": "Detects installed linux-image packages and offers to purge older kernels while keeping the running and recent ones.",
  "config": {
    "keep_kernels": {
      "type": "int",
      "code_default": 2,
      "description": "How many recent kernels to retain (the running kernel is always kept).",
      "min": 0,
      "max": 50
    }
  },
  "constructor": {
    "keep": {
      "type": "int",
      "default": null,
      "description": "How many recent kernels to keep; if null the code default is used",
      "required": false,
      "annotation": "Optional[int]",
      "min": 0,
      "max": 50
    }
  }
}
```

Using the form spec in a UI
--------------------------
- Map `type` to widget types (int -> number input, path -> file picker, list[path] -> list of file pickers, bool -> checkbox).
- Use `min`/`max` for numeric ranges and validation.
- Use `choices` to render a select/dropdown when present.
- Use `required` to decide whether to mark fields mandatory.
- Use `annotation` as a hint for showing types in tooltips.

Persisting typed values
-----------------------
- The CLI's `config plugin set` validates the input and stores typed values in
  TOML. Paths are stored as strings, lists as TOML arrays, booleans/ints as
  TOML scalars.
- We prefer `tomli-w` as the TOML writer for deterministic round-tripping
  and nice formatting. If not available the code falls back to a safe writer
  that writes plugin tables and arrays.

Extending / exporting richer JSON Schema
---------------------------------------
If you want a full JSON Schema (for form libraries such as react-jsonschema-form)
we can implement a converter that maps our small `PLUGIN_INFO` schema to JSON
Schema draft-07/2019-09. This is straightforward because our schema already
contains the necessary keys (type/min/max/choices/required).

If you'd like, I can:
- Add a small command `smartcleaner plugins export-form <factory_key> --json` to
  emit the form spec for a single plugin, or
- Add an export that emits a full JSON Schema for all discovered plugins.


---

File location: `docs/PLUGIN_CONFIG.md` — you can edit this file or ask me to
generate the JSON form exports or add a CLI command that emits the form spec.
