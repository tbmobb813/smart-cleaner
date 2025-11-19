"""Lightweight discovery wrapper for external tools and GUIs.

This module exposes small helpers that wrap `CleanerManager` discovery so
consumers don't need to instantiate the manager directly.
"""
from typing import Any

from smartcleaner.managers.cleaner_manager import CleanerManager


def get_factories_metadata() -> dict[str, dict[str, Any]]:
    """Return metadata for available plugin factories.

    The returned mapping is factory_key -> metadata with serializable values:
    - module: module path
    - class: class name
    - class_path: fully-qualified class path (module.Class) or None
    - plugin_info: PLUGIN_INFO dict from module if present
    - description: short description string
    """
    mgr = CleanerManager()
    meta = mgr.get_factories_metadata()
    out: dict[str, dict[str, Any]] = {}
    for key, v in meta.items():
        cls = v.get('class_obj')
        class_path: str | None = None
        try:
            if cls is not None:
                class_path = f"{cls.__module__}.{cls.__name__}"
        except Exception:
            class_path = None

        out[key] = {
            'module': v.get('module'),
            'class': v.get('class'),
            'class_path': class_path,
            'plugin_info': v.get('plugin_info'),
            'description': v.get('description'),
        }

    return out


def get_factory_keys() -> list[str]:
    """Return a list of available factory keys."""
    mgr = CleanerManager()
    return mgr.list_available_factories()


def get_plugin_info(factory_key: str) -> dict[str, Any] | None:
    """Return module-level PLUGIN_INFO for a factory key, or None.

    The factory_key may be the form 'module:Class' or just a module.
    """
    module_name = factory_key.split(':', 1)[0]
    try:
        mod = __import__(module_name, fromlist=['PLUGIN_INFO'])
    except Exception:
        return None
    return getattr(mod, 'PLUGIN_INFO', None)
