from smartcleaner.utils.json_schema import plugin_info_to_json_schema


def test_kernels_json_schema_contains_keep_kernels():
    schema = plugin_info_to_json_schema('smartcleaner.plugins.kernels')
    props = schema.get('properties', {})
    assert 'keep_kernels' in props
    keep = props['keep_kernels']
    assert keep.get('type') == 'integer'
    assert keep.get('minimum') == 0
    assert keep.get('maximum') == 50
    # default comes from code_default
    assert keep.get('default') == 2


def test_apt_cache_schema_cache_dir_is_string():
    schema = plugin_info_to_json_schema('smartcleaner.plugins.apt_cache')
    props = schema.get('properties', {})
    assert 'cache_dir' in props
    assert props['cache_dir'].get('type') == 'string'
