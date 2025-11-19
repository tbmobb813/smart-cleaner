from pathlib import Path

import pytest

from smartcleaner.config import validate_plugin_config


def test_validate_kernel_keep_kernels_valid():
    val = validate_plugin_config("smartcleaner.plugins.kernels", "keep_kernels", "3")
    assert isinstance(val, int)
    assert val == 3


def test_validate_kernel_keep_kernels_too_small():
    with pytest.raises(ValueError):
        validate_plugin_config("smartcleaner.plugins.kernels", "keep_kernels", "-1")


def test_validate_kernel_keep_kernels_too_large():
    with pytest.raises(ValueError):
        validate_plugin_config("smartcleaner.plugins.kernels", "keep_kernels", "100")


def test_validate_apt_cache_cache_dir():
    val = validate_plugin_config("smartcleaner.plugins.apt_cache", "cache_dir", "/tmp")
    assert isinstance(val, Path)
    assert str(val) == "/tmp"
