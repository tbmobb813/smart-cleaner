import shutil
import subprocess
from pathlib import Path

import pytest


def bwrap_available() -> bool:
    return shutil.which("bwrap") is not None


@pytest.mark.skipif(not bwrap_available(), reason="bubblewrap (bwrap) not available on this host")
def test_prototype_bwrap_runs_plugin_worker():
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = repo_root / "scripts" / "prototype_bwrap.sh"
    assert wrapper.exists(), "prototype_bwrap.sh missing"

    proc = subprocess.run(["/bin/bash", str(wrapper), "smartcleaner.plugins.test_isolated_plugin", "TestIsolatedPlugin", "scan"], capture_output=True, text=True)
    assert proc.returncode == 0, f"wrapper failed: {proc.stderr}"
    out = proc.stdout
    idx = None
    for ch in ("[", "{"):
        i = out.find(ch)
        if i != -1:
            idx = i
            break
    assert idx is not None, f"No JSON found in wrapper output: {out!r}"
    import json

    parsed = json.loads(out[idx:])
    assert isinstance(parsed, list)
    assert parsed and parsed[0].get("path") == "/tmp/testfile"
