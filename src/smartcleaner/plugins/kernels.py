import re
from typing import List, Tuple, Any, Dict

from ..managers.cleaner_manager import CleanableItem, SafetyLevel
from ..utils import privilege


PLUGIN_INFO = {
    'name': 'Old Kernels Cleaner',
    'description': 'Detects installed linux-image packages and offers to purge older kernels while keeping the running and recent ones.',
}

def version_key(v: str) -> Tuple[int, ...]:
    """Return a numeric key for a version-like string by extracting integer groups.

    This is a best-effort comparator that ignores non-numeric suffixes (e.g., rc1).
    """
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums)


class KernelCleaner:
    """Removes old Linux kernels, keeping the current and most recent."""

    KERNELS_TO_KEEP = 2

    def __init__(self, keep: int | None = None):
        # allow instance-level override; fall back to class default
        self.kernels_to_keep = int(keep) if keep is not None else self.KERNELS_TO_KEEP


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
                        'is_current': kernel_version == current
                    })

        return kernels

    def scan(self) -> List[CleanableItem]:
        items: List[CleanableItem] = []
        try:
            kernels = self.get_installed_kernels()

            kernels.sort(key=lambda k: version_key(k['version']), reverse=True)

            # Mark the top kernels_to_keep as kept; always keep the current kernel
            for i, kernel in enumerate(kernels):
                kernel['keep'] = False
                if i < self.kernels_to_keep:
                    kernel['keep'] = True

            # Ensure current kernel is always kept
            for kernel in kernels:
                if kernel.get('is_current'):
                    kernel['keep'] = True

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
                # Purge the package name
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
