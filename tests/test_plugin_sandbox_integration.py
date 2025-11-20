import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def userns_available() -> bool:
    # Check if `unshare` exists and if creating a userns is allowed
    unshare = shutil.which("unshare")
    if not unshare:
        return False
    try:
        # Try a no-op in a new userns; exit code 0 indicates allowed
        res = subprocess.run([unshare, "--user", "--map-root-user", "true"], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


@pytest.mark.skipif(not userns_available(), reason="user namespaces (unshare) not available on this host")
def test_prototype_sandbox_runs_plugin_worker():
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = repo_root / "scripts" / "prototype_sandbox.sh"
    assert wrapper.exists(), "prototype_sandbox.sh missing"

    # Run the prototype wrapper for the test isolated plugin included in src
    # Invoke via shell interpreter to avoid requiring executable bit
    proc = subprocess.run(["/bin/bash", str(wrapper), "smartcleaner.plugins.test_isolated_plugin", "TestIsolatedPlugin", "scan"], capture_output=True, text=True)
    assert proc.returncode == 0, f"wrapper failed: {proc.stderr}"
    out = proc.stdout
    # extract JSON from output by finding first '[' or '{'
    idx = None
    for ch in ("[", "{"):
        i = out.find(ch)
        if i != -1:
            idx = i
            break
    assert idx is not None, f"No JSON found in wrapper output: {out!r}"
    data = out[idx:]
    # Basic sanity parse
    import json

    parsed = json.loads(data)
    assert isinstance(parsed, list)
    assert parsed and parsed[0].get("path") == "/tmp/testfile"
