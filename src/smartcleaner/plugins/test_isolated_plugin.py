"""Test plugin used by unit tests to exercise plugin isolation."""
from __future__ import annotations

PLUGIN_INFO = {
    "name": "Test Isolated Plugin",
    "version": "0.0.1",
    "description": "A plugin used by tests to validate subprocess isolation",
    "safety": "SAFE",
    "isolate": True,
    "class": "TestIsolatedPlugin",
}


class TestIsolatedPlugin:
    def get_name(self) -> str:
        return "Test Isolated Plugin"

    def is_available(self) -> bool:
        return True

    def scan(self):
        # Return a JSON-serializable list of dicts; plugin_runner will print it
        return [{"path": "/tmp/testfile", "size_bytes": 1234, "description": "test", "safety": "SAFE"}]

    def supports_dry_run(self) -> bool:
        return True

    def clean_dry_run(self, items):
        return {"success": True, "cleaned_count": len(items), "total_size": sum(it.get("size_bytes", 0) for it in items)}

    def clean(self, items):
        return {"success": True, "cleaned_count": len(items), "total_size": sum(it.get("size_bytes", 0) for it in items)}
