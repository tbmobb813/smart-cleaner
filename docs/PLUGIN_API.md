# Plugin API (short spec)

This document describes the minimal contract and PLUGIN_INFO schema for Smart Cleaner plugins. It is intentionally small and stable; changes to this contract should be treated as an semver-minor/major change and documented in `CHANGELOG.md`.

Required attributes on the plugin module/class

- A plugin must expose a module-level dict named `PLUGIN_INFO` (or a class attribute with the same name) containing the following keys:
  - `name` (string): human-friendly plugin name
  - `version` (string): plugin version (semver-like recommended)
  - `description` (string): short description
  - `safety` (string): one of `SAFE`, `CAUTION`, `ADVANCED`, `DANGEROUS`

Required methods on the plugin class

- `scan(self) -> list[dict]`: return a list of cleanable item objects. Each item should contain at minimum `path` and `size_bytes` keys. The shape above is validated by the JSON Schema in `docs/plugin_schema.json`.
- `clean(self, items: list[dict]) -> dict`: perform cleaning and return a result object with `success: bool`, `cleaned_count: int`, and optional `errors: list[str]`.
- `is_available(self) -> bool`: quick availability check for runtime environment.

Safety notes

- Plugins should avoid direct `sudo` usage. Use the core `privilege` utility to request escalation when necessary.
- Plugins should sanitize any path inputs and never assume global write permissions.

Plugin isolation

- Plugins may run in-process by default. For stronger isolation, maintainers can enable subprocess execution via the `PluginRunner` helper in `smartcleaner.managers.plugin_runner`.

Validation

- Use `scripts/validate-plugin-schema.py` to validate the on-disk plugin modules against the JSON schema before publishing or merging.

Backward compatibility

- Additive changes to `PLUGIN_INFO` are allowed. Removing or renaming required keys is a breaking change and must be communicated in the changelog and release notes.
