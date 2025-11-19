from smartcleaner.managers.cleaner_manager import CleanerManager


def test_scan_returns_plugins_dict():
    mgr = CleanerManager()
    results = mgr.scan_all()
    assert isinstance(results, dict)
    assert "APT Package Cache" in results
    assert "Old Kernels" in results


def test_clean_selected_frees_size():
    mgr = CleanerManager()
    results = mgr.scan_all()
    res = mgr.clean_selected(results, dry_run=True)
    assert isinstance(res, dict)
    total = sum(r["total_size"] for r in res.values())
    assert total > 0
