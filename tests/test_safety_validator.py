from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel
from smartcleaner.managers.safety_validator import SafetyValidator


def test_validator_allows_under_limit():
    validator = SafetyValidator(max_level=SafetyLevel.CAUTION)
    item_safe = CleanableItem(path="/tmp/a", size=100, description="a", safety=SafetyLevel.SAFE)
    item_caution = CleanableItem(path="/tmp/b", size=200, description="b", safety=SafetyLevel.CAUTION)
    item_adv = CleanableItem(path="/tmp/c", size=300, description="c", safety=SafetyLevel.ADVANCED)

    assert validator.is_allowed(item_safe)
    assert validator.is_allowed(item_caution)
    assert not validator.is_allowed(item_adv)
