from smartcleaner.plugins.kernels import version_key


def test_version_key_basic_numeric():
    assert version_key('6.8.0-86-generic') == (6, 8, 0, 86)
    assert version_key('5.4.0-50-generic') == (5, 4, 0, 50)


def test_version_key_with_rc_and_suffixes():
    # rc and other non-numeric parts should be ignored but numeric groups kept
    assert version_key('5.4.0-50-rc1') == (5, 4, 0, 50, 1)
    assert version_key('5.4.0-50-generic') == (5, 4, 0, 50)
    assert version_key('5.4.0_50') == (5, 4, 0, 50)


def test_version_key_sorting_behavior():
    versions = ['6.8.0-80-generic', '6.8.0-86-generic', '6.8.0-84-generic', '6.8.0-85-generic']
    sorted_versions = sorted(versions, key=version_key, reverse=True)
    assert sorted_versions[0] == '6.8.0-86-generic'
    assert sorted_versions[-1] == '6.8.0-80-generic'
