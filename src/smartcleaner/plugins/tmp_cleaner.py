from pathlib import Path
from typing import Optional, TYPE_CHECKING
from .base import BasePlugin
import shutil

if TYPE_CHECKING:
    from ..managers.cleaner_manager import CleanableItem, SafetyLevel  # noqa: F401


class TmpCleaner(BasePlugin):
    """Cleans temporary directories like /tmp or a provided base path."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path('/tmp')

    def get_name(self) -> str:
        return "Temporary Files"

    def get_description(self) -> str:
        return "Temporary files under /tmp or a provided directory."

    def scan(self):
        items = []
        if not self.base_dir.exists():
            return items
        for p in self.base_dir.iterdir():
            try:
                if p.is_file():
                    from ..managers.cleaner_manager import CleanableItem, SafetyLevel
                    items.append(CleanableItem(path=str(p), size=int(p.stat().st_size), description=f"Temp file: {p.name}", safety=SafetyLevel.SAFE))
                elif p.is_dir():
                    # include directory sizes as approximate (sum children)
                    size: int = 0
                    for sub in p.rglob('*'):
                        try:
                            if sub.is_file():
                                size += int(sub.stat().st_size)
                        except Exception:
                            continue
                    from ..managers.cleaner_manager import CleanableItem, SafetyLevel
                    items.append(CleanableItem(path=str(p), size=size, description=f"Temp dir: {p.name}", safety=SafetyLevel.SAFE))
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
                    # remove tree
                    shutil.rmtree(p)
                    result['cleaned_count'] += 1
                else:
                    continue
            except Exception as e:
                result['errors'].append(str(e))
                result['success'] = False
        return result


    PLUGIN_INFO = {
        'name': 'Temporary Files Cleaner',
        'description': 'Cleans temporary files and directories (e.g., /tmp).',
        'module': 'smartcleaner.plugins.tmp_cleaner',
        'class': 'TmpCleaner',
        'config': {
            'base_dir': {
                'type': 'path',
                'description': 'Base temporary directory to scan',
                'example': '/tmp'
            }
        },
        'constructor': {
            'base_dir': {
                'type': 'path',
                'default': '/tmp',
                'description': 'Base temporary directory to scan',
                'required': False,
                'annotation': 'Optional[pathlib.Path]'
            }
        },
    }
