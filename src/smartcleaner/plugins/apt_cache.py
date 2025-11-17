from pathlib import Path
from typing import List, Any, Dict

from ..managers.cleaner_manager import CleanableItem, SafetyLevel
from ..utils import privilege


class APTCacheCleaner:
    """Cleans APT package cache located at /var/cache/apt/archives by default."""

    def __init__(self, cache_dir: Path = Path("/var/cache/apt/archives")):
        self.cache_dir = Path(cache_dir)

    def get_name(self) -> str:
        return "APT Package Cache"

    def get_description(self) -> str:
        return "Downloaded package files (.deb) and partial downloads from APT cache."

    def scan(self) -> List[CleanableItem]:
        items: list[CleanableItem] = []
        if not self.cache_dir.exists():
            return items

        partial = self.cache_dir / 'partial'
        if partial.exists() and partial.is_dir():
            for p in partial.iterdir():
                if p.is_file():
                    items.append(CleanableItem(path=str(p), size=p.stat().st_size, description=f"Incomplete download: {p.name}", safety=SafetyLevel.SAFE))

        for deb in self.cache_dir.glob('*.deb'):
            if deb.is_file():
                items.append(CleanableItem(path=str(deb), size=deb.stat().st_size, description=f"Cached package: {deb.name}", safety=SafetyLevel.SAFE))

        return items

    def clean(self, items: List[CleanableItem]) -> dict:
        result: Dict[str, Any] = {'success': False, 'cleaned_count': 0, 'total_size': 0, 'errors': []}
        try:
            # Use apt-get clean via privilege helper; may raise PermissionError if sudo not allowed
            privilege.run_command(['apt-get', 'clean'], sudo=True)
            result['success'] = True
            result['cleaned_count'] = len(items)
            result['total_size'] = sum(i.size for i in items)
        except PermissionError as e:
            result['errors'].append(str(e))
        except Exception as e:
            result['errors'].append(str(e))

        return result


PLUGIN_INFO = {
    'name': 'APT Package Cache Cleaner',
    'description': 'Scans and cleans APT package cache (deb files and partial downloads).',
}
