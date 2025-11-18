from smartcleaner.plugins import discovery


def test_discovery_wrapper_returns_factories():
    keys = discovery.get_factory_keys()
    assert isinstance(keys, list)
    # should expose at least one factory in the test environment
    assert len(keys) > 0


def test_discovery_metadata_serializable():
    meta = discovery.get_factories_metadata()
    assert isinstance(meta, dict)
    # pick one entry and verify expected keys
    sample_key = next(iter(meta.keys()))
    entry = meta[sample_key]
    assert 'module' in entry
    assert 'class' in entry
    assert 'class_path' in entry
    # plugin_info may be None or dict
