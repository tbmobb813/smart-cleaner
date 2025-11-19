from smartcleaner.plugins.apt_cache import APTCacheCleaner


def test_apt_cache_scan_and_clean(tmp_path, monkeypatch):
    # Create fake cache dir
    cache_dir = tmp_path / "apt" / "archives"
    partial = cache_dir / "partial"
    partial.mkdir(parents=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    f1 = cache_dir / "package1.deb"
    f1.write_bytes(b"0" * 1024 * 5)
    p1 = partial / "incomplete.part"
    p1.write_bytes(b"0" * 200)

    plugin = APTCacheCleaner(cache_dir=cache_dir)
    items = plugin.scan()
    assert any("package1.deb" in it.path for it in items)
    assert any("incomplete.part" in it.path for it in items)

    # Monkeypatch run_command to simulate apt-get clean
    def fake_run(cmd, sudo=False, **kwargs):
        class CP:
            stdout = ""
            returncode = 0

        return CP()

    monkeypatch.setattr("smartcleaner.utils.privilege.run_command", fake_run)

    res = plugin.clean(items)
    assert res["success"]
    assert res["cleaned_count"] == len(items)
