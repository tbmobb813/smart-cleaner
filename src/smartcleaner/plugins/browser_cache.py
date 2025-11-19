"""Browser cache cleaner plugin.

Cleans browser cache files from Firefox, Chrome, Chromium, and other common browsers.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import BasePlugin

if TYPE_CHECKING:
    from ..managers.cleaner_manager import CleanableItem, SafetyLevel  # noqa: F401


class BrowserCacheCleaner(BasePlugin):
    """Cleans browser cache from common web browsers."""

    # Common browser cache locations (relative to home directory)
    BROWSER_PATHS = {
        "Firefox": [
            ".mozilla/firefox/*/cache2",
            ".cache/mozilla/firefox/*/cache2",
        ],
        "Chrome": [
            ".config/google-chrome/Default/Cache",
            ".cache/google-chrome/Default/Cache",
        ],
        "Chromium": [
            ".config/chromium/Default/Cache",
            ".cache/chromium/Default/Cache",
        ],
        "Brave": [
            ".config/BraveSoftware/Brave-Browser/Default/Cache",
        ],
        "Edge": [
            ".config/microsoft-edge/Default/Cache",
        ],
    }

    def __init__(self, home_dir: Path = Path.home(), base_dirs: list[Path] | None = None):
        # Accept either a single home_dir or explicit base_dirs (for tests)
        self.home_dir = Path(home_dir)
        self.base_dirs = [Path(d) for d in base_dirs] if base_dirs is not None else None

    def get_name(self) -> str:
        return "Browser Cache"

    def get_description(self) -> str:
        return "Cache files from Firefox, Chrome, Chromium, Brave, and other browsers."

    def scan(self) -> "list[CleanableItem]":
        items: list = []

        # If explicit base_dirs were provided (tests), scan those directories directly
        if self.base_dirs is not None:
            for d in self.base_dirs:
                p = Path(d)
                if p.exists():
                    items.extend(self._scan_directory(p, "Browser"))
            return items

        search_bases = [self.home_dir]

        for base_home in search_bases:
            for browser_name, patterns in self.BROWSER_PATHS.items():
                for pattern in patterns:
                    # Expand glob patterns
                    if "*" in pattern:
                        # Handle wildcards manually
                        base = pattern.split("*")[0]
                        base_path = base_home / base
                        if base_path.exists():
                            # Find all matching directories
                            parent = base_path.parent
                            if parent.exists():
                                for subdir in parent.iterdir():
                                    if subdir.is_dir():
                                        # Check if this matches the pattern
                                        cache_path = subdir / pattern.split("*/")[-1]
                                        if cache_path.exists():
                                            items.extend(self._scan_directory(cache_path, browser_name))
                    else:
                        cache_path = base_home / pattern
                        if cache_path.exists():
                            items.extend(self._scan_directory(cache_path, browser_name))

        return items

    def _scan_directory(self, path: Path, browser_name: str) -> "list[CleanableItem]":
        """Scan a directory and return CleanableItems for all files."""
        items: list = []

        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    try:
                        size = entry.stat().st_size
                        from ..managers.cleaner_manager import CleanableItem, SafetyLevel

                        items.append(
                            CleanableItem(
                                path=str(entry),
                                size=size,
                                description=f"{browser_name} cache: {entry.name}",
                                safety=SafetyLevel.SAFE,
                            )
                        )
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
        except (OSError, PermissionError):
            # Skip directories we can't access
            pass

        return items

    def clean(self, items: "list[CleanableItem]") -> dict[str, Any]:
        result: dict[str, Any] = {"success": True, "cleaned_count": 0, "total_size": 0, "errors": []}

        for item in items:
            try:
                file_path = Path(item.path)
                if file_path.exists():
                    size = file_path.stat().st_size
                    file_path.unlink()
                    result["cleaned_count"] += 1
                    result["total_size"] += size
            except (OSError, PermissionError) as e:
                result["errors"].append(f"Failed to delete {item.path}: {e}")
                result["success"] = False

        return result

    def is_available(self) -> bool:
        """Browser cache cleaning is available if any browser directory exists."""
        for patterns in self.BROWSER_PATHS.values():
            for pattern in patterns:
                # Simple check: if the base directory exists
                base = pattern.split("*")[0] if "*" in pattern else pattern.split("/")[0]
                if (self.home_dir / base).exists():
                    return True
        return False

    def supports_dry_run(self) -> bool:
        return True

    def clean_dry_run(self, items: "list[CleanableItem]") -> dict[str, Any]:
        return {
            "success": True,
            "cleaned_count": len(items),
            "total_size": sum(item.size for item in items),
            "errors": [],
            "dry_run": True,
        }
