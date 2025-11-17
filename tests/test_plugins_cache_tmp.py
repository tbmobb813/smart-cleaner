from pathlib import Path
from smartcleaner.plugins.browser_cache import BrowserCacheCleaner
from smartcleaner.plugins.thumbnails import ThumbnailCacheCleaner
from smartcleaner.plugins.tmp_cleaner import TmpCleaner


def test_browser_cache_scans_and_cleans(tmp_path):
    base = tmp_path / 'browser' / 'cache'
    d = base / 'profile' / 'Cache'
    d.mkdir(parents=True)
    f = d / 'cache1.bin'
    f.write_bytes(b'x' * 1024)

    plugin = BrowserCacheCleaner(base_dirs=[base])
    items = plugin.scan()
    assert any('cache1.bin' in it.path for it in items)

    res = plugin.clean(items)
    assert res['success']
    assert not f.exists()


def test_thumbnails_scans_and_cleans(tmp_path):
    d = tmp_path / 'thumbnails'
    d.mkdir(parents=True)
    f = d / 'thumb1.png'
    f.write_bytes(b'0' * 512)

    plugin = ThumbnailCacheCleaner(cache_dir=d)
    items = plugin.scan()
    assert any('thumb1.png' in it.path for it in items)

    res = plugin.clean(items)
    assert res['success']
    assert not f.exists()


def test_tmp_cleaner_scans_and_cleans(tmp_path):
    d = tmp_path / 'tmpdir'
    d.mkdir(parents=True)
    f = d / 'tempfile'
    f.write_bytes(b'0' * 256)

    plugin = TmpCleaner(base_dir=d)
    items = plugin.scan()
    assert any('tempfile' in it.path for it in items)

    res = plugin.clean(items)
    assert res['success']
    assert not f.exists()
