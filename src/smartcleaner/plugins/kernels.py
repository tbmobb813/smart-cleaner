import re
from typing import List, Tuple

from ..managers.cleaner_manager import CleanableItem, SafetyLevel
from ..utils import privilege
from typing import Any, Dict


class KernelCleaner:
    """Removes old Linux kernels, keeping the current and most recent."""

    KERNELS_TO_KEEP = 2

    def __init__(self):
        pass

    def get_name(self) -> str:
        return "Old Kernels"

    def get_description(self) -> str:
        return "Removes old kernel packages while keeping the current and recent backups."

    def get_current_kernel(self) -> str:
        cp: Any = privilege.run_command(['uname', '-r'], sudo=False)
        return str(cp.stdout).strip()

    def get_installed_kernels(self) -> List[dict]:
        result: Any = privilege.run_command(['dpkg', '--list'], sudo=False)
        kernels: list[dict] = []
        current = self.get_current_kernel()

        for line in str(result.stdout).split('\n'):
            if 'linux-image-' in line and line.startswith('ii'):
                parts = line.split()
                package_name = parts[1]
                version_match = re.search(r'linux-image-(.+)', package_name)
                if version_match:
                    kernel_version = version_match.group(1)
                    # Try to get installed size via dpkg-query
                    try:
                        size_cp: Any = privilege.run_command(['dpkg-query', '-W', '-f=${Installed-Size}', package_name], sudo=False)
                        size_kb = int(str(size_cp.stdout).strip() or "0")
                        size_bytes = size_kb * 1024
                    except Exception:
                        size_bytes = 0

                    kernels.append({
                        'package': package_name,
                        'version': kernel_version,
                        'size': size_bytes,
                        'is_current': kernel_version in current
                    })

        return kernels

    def scan(self) -> List[CleanableItem]:
        items: List[CleanableItem] = []
        try:
            kernels = self.get_installed_kernels()
            # Sort by version (newest first) using packaging.version
            # Sort by numeric components extracted from the version string (best-effort)
            def _numeric_key(v: str) -> Tuple[int, ...]:
                nums = re.findall(r"\d+", v)
                return tuple(int(n) for n in nums)

            kernels.sort(key=lambda k: _numeric_key(k['version']), reverse=True)

            kept = 0
            for kernel in kernels:
                if kernel['is_current']:
                    kernel['keep'] = True
                    kept += 1
                elif kept < self.KERNELS_TO_KEEP:
                    kernel['keep'] = True
                    kept += 1
                else:
                    kernel['keep'] = False

            for kernel in kernels:
                if not kernel.get('keep', False):
                    items.append(CleanableItem(path=kernel['package'], size=kernel['size'], description=f"Old kernel: {kernel['version']}", safety=SafetyLevel.SAFE,))

        except Exception:
            # On error, return empty list
            return []

        return items

    def clean(self, items: List[CleanableItem]) -> dict:
        result: Dict[str, Any] = {'success': True, 'cleaned_count': 0, 'total_size': 0, 'errors': []}
        for item in items:
            try:
                privilege.run_command(['apt-get', 'purge', '-y', item.path], sudo=True)
                result['cleaned_count'] += 1
                result['total_size'] += item.size
            except Exception as e:
                result['errors'].append(str(e))
                result['success'] = False

        try:
            privilege.run_command(['apt-get', 'autoremove', '-y'], sudo=True)
        except Exception:
            pass

        return result
