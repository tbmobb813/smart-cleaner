from pathlib import Path
from typing import List, Any, Dict, Optional
import shutil

from ..managers.cleaner_manager import CleanableItem, SafetyLevel


class ThumbnailCacheCleaner:
    """Cleans the GNOME/thumbnail cache at ~/.cache/thumbnails by default."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.cache' / 'thumbnails'

    def get_name(self) -> str:
        return "Thumbnail Cache"

    def get_description(self) -> str:
        return "User thumbnail cache (~/.cache/thumbnails)."

    def scan(self):
        items = []
        if not self.cache_dir.exists():
            return items
        for p in self.cache_dir.rglob('*'):
            try:
                if p.is_file():
                    items.append(CleanableItem(path=str(p), size=int(p.stat().st_size), description=f"Thumbnail: {p.name}", safety=SafetyLevel.SAFE))
                elif p.is_dir():
                    items.append(CleanableItem(path=str(p), size=0, description=f"Thumbnail dir: {p.name}", safety=SafetyLevel.SAFE))
            except Exception:
                continue
        return items

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
                    shutil.rmtree(p)
                    result['cleaned_count'] += 1
            except Exception as e:
                result['errors'].append(str(e))
                result['success'] = False
        return result


    PLUGIN_INFO = {
        'name': 'Thumbnail Cache Cleaner',
        'description': 'Scans and cleans user thumbnail cache (~/.cache/thumbnails).',
        'module': 'smartcleaner.plugins.thumbnails',
        'class': 'ThumbnailCacheCleaner',
        'config': {
            'cache_dir': {
                'type': 'path',
                'description': 'Thumbnail cache directory',
                'example': str(Path.home() / '.cache' / 'thumbnails')
            }
        },
        'constructor': {
            'cache_dir': {
                'type': 'path',
                'default': str(Path.home() / '.cache' / 'thumbnails'),
                'description': 'Thumbnail cache directory',
                'required': False,
                'annotation': 'Optional[pathlib.Path]'
            }
        },
    }
