from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel


def test_get_size_human_purity():
    item = CleanableItem(path="/tmp/foo", size=1536, description="x", safety=SafetyLevel.SAFE)
    human = item.get_size_human()
    assert human == "1.50 KB"
    # original size must remain unchanged
    assert item.size == 1536


def test_safetylevel_ordering():
    assert SafetyLevel.SAFE < SafetyLevel.CAUTION
    assert SafetyLevel.CAUTION < SafetyLevel.ADVANCED
    assert SafetyLevel.ADVANCED < SafetyLevel.DANGEROUS
