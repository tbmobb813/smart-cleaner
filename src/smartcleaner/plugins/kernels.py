import re
from typing import TYPE_CHECKING, Any

from ..utils import privilege
from .base import BasePlugin

if TYPE_CHECKING:
    from ..managers.cleaner_manager import CleanableItem, SafetyLevel  # noqa: F401


def version_key(version: str):
    """
    Create a sortable key for kernel version strings by extracting numeric components
    and returning a tuple of (numeric_parts_tuple, original_string) so that
    numeric comparisons are used first and the original string is a tiebreaker.
    """
    nums = tuple(int(x) for x in re.findall(r"\d+", version))
    # Return a flat tuple of numeric components for easy sorting/comparison
    return nums


class KernelCleaner(BasePlugin):
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
        cp: Any = privilege.run_command(["uname", "-r"], sudo=False)
        return str(cp.stdout).strip()

    def get_installed_kernels(self) -> list[dict]:
        result: Any = privilege.run_command(["dpkg", "--list"], sudo=False)
        kernels: list[dict] = []
        current = self.get_current_kernel()

        for line in str(result.stdout).split("\n"):
            if "linux-image-" in line and line.startswith("ii"):
                parts = line.split()
                package_name = parts[1]
                version_match = re.search(r"linux-image-(.+)", package_name)
                if version_match:
                    kernel_version = version_match.group(1)
                    # Try to get installed size via dpkg-query
                    try:
                        size_cp: Any = privilege.run_command(
                            ["dpkg-query", "-W", "-f=${Installed-Size}", package_name], sudo=False
                        )
                        size_kb = int(str(size_cp.stdout).strip() or "0")
                        size_bytes = size_kb * 1024
                    except Exception:
                        size_bytes = 0

                    kernels.append(
                        {
                            "package": package_name,
                            "version": kernel_version,
                            "size": size_bytes,
                            "is_current": kernel_version == current,
                        }
                    )

        return kernels

    def scan(self) -> "list[CleanableItem]":
        items: list = []
        try:
            kernels = self.get_installed_kernels()

            kernels.sort(key=lambda k: version_key(k["version"]), reverse=True)

            # Mark the top kernels_to_keep as kept; always keep the current kernel
            for i, kernel in enumerate(kernels):
                kernel["keep"] = False
                if i < self.kernels_to_keep:
                    kernel["keep"] = True

            # Ensure current kernel is always kept
            for kernel in kernels:
                if kernel.get("is_current"):
                    kernel["keep"] = True

            for kernel in kernels:
                if not kernel.get("keep", False):
                    from ..managers.cleaner_manager import CleanableItem, SafetyLevel

                    items.append(
                        CleanableItem(
                            path=kernel["package"],
                            size=kernel["size"],
                            description=f"Old kernel: {kernel['version']}",
                            safety=SafetyLevel.SAFE,
                        )
                    )

        except Exception:
            # On error, return empty list
            return []

        return items

    def clean(self, items: "list[CleanableItem]") -> dict:
        result: dict[str, Any] = {"success": True, "cleaned_count": 0, "total_size": 0, "errors": []}
        for item in items:
            try:
                # Purge the package name
                privilege.run_command(["apt-get", "purge", "-y", item.path], sudo=True)
                result["cleaned_count"] += 1
                result["total_size"] += item.size
            except Exception as e:
                result["errors"].append(str(e))
                result["success"] = False

        try:
            privilege.run_command(["apt-get", "autoremove", "-y"], sudo=True)
        except Exception:
            pass

        return result

    def is_available(self) -> bool:
        """Check if this plugin is available (requires dpkg and apt-get)."""
        try:
            privilege.run_command(["which", "dpkg"], sudo=False)
            privilege.run_command(["which", "apt-get"], sudo=False)
            return True
        except Exception:
            return False

    def supports_dry_run(self) -> bool:
        """Kernel cleaning supports dry-run mode."""
        return True

    def clean_dry_run(self, items: "list[CleanableItem]") -> dict[str, Any]:
        """Report what would be cleaned without actually cleaning."""
        return {
            "success": True,
            "cleaned_count": len(items),
            "total_size": sum(item.size for item in items),
            "errors": [],
            "dry_run": True,
        }


PLUGIN_INFO = {
    "name": "Old Kernels",
    "description": "Removes old kernel packages while keeping the current and recent backups.",
    "module": "smartcleaner.plugins.kernels",
    "class": "KernelCleaner",
    "config": {
        "keep_kernels": {
            "type": "integer",
            "description": "How many recent kernels to keep",
            "min": 0,
            "max": 50,
            "code_default": 2,
            "required": False,
        }
    },
    "constructor": {
        "keep_kernels": {"type": "integer", "default": 2, "required": False, "annotation": "Optional[int]"}
    },
}
