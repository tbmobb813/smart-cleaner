from pathlib import Path
from typing import List, Any, Dict, Optional
import shutil

from ..managers.cleaner_manager import CleanableItem, SafetyLevel


class BrowserCacheCleaner:
    """Cleans common browser cache directories (Chrome/Chromium/Firefox) under a base cache dir."""

    def __init__(self, base_dirs: Optional[List[Path]] = None):
        if base_dirs is None:
            # common per-user cache locations
            self.base_dirs: List[Path] = [
                Path.home() / '.cache' / 'google-chrome',
                Path.home() / '.cache' / 'chromium',
                Path.home() / '.cache' / 'mozilla',
            ]
        else:
            self.base_dirs = [Path(p) for p in base_dirs]

    def get_name(self) -> str:
        return "Browser Caches"

    def get_description(self) -> str:
        return "Browser cache directories for Chrome, Chromium and Firefox."

    def _iter_cache_items(self):
        items = []
        for base in self.base_dirs:
            if not base.exists():
                continue
            for p in base.rglob('*'):
                try:
                    if p.is_file():
                        items.append(CleanableItem(path=str(p), size=int(p.stat().st_size), description=f"Browser cache: {p.name}", safety=SafetyLevel.SAFE))
                    elif p.is_dir() and not any(p.iterdir()):
                        # empty dir
                        items.append(CleanableItem(path=str(p), size=0, description=f"Empty cache dir: {p.name}", safety=SafetyLevel.SAFE))
                except Exception:
                    continue
        return items

    def scan(self):
        return self._iter_cache_items()

    def clean(self, items):
        result = {'success': True, 'cleaned_count': 0, 'total_size': 0, 'errors': []}
        for it in items:
            p = Path(it.path)
            try:
                if p.is_file():
                    size = p.stat().st_size
                    p.unlink()
                    result['cleaned_count'] += 1
                    result['total_size'] += size
                elif p.is_dir():
                    # remove directory tree
                    shutil.rmtree(p)
                    result['cleaned_count'] += 1
                else:
                    continue
            except Exception as e:
                result['errors'].append(str(e))
                result['success'] = False
        return result
