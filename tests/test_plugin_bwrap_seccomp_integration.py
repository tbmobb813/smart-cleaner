import shutil
import subprocess
import os
from pathlib import Path

import pytest


def bwrap_supports_seccomp() -> bool:
    if shutil.which("bwrap") is None:
        return False
    try:
        out = subprocess.check_output(["bwrap", "--help"], stderr=subprocess.STDOUT, text=True)
        return "--seccomp" in out
    except Exception:
        return False


def bwrap_has_compiled_profile(repo_root: Path) -> bool:
    # We expect a compiled filter at scripts/bwrap-seccomp.bin or via env override
    candidate = Path(os.environ.get("BWRAP_SECCOMP_BIN", repo_root / "scripts" / "bwrap-seccomp.bin"))
    return candidate.is_file()


@pytest.mark.skipif(not bwrap_supports_seccomp() or shutil.which("bwrap") is None, reason="bwrap --seccomp not available on this host")
def test_prototype_bwrap_with_seccomp():
    import os

    repo_root = Path(__file__).resolve().parents[1]
    wrapper = repo_root / "scripts" / "prototype_bwrap.sh"
    assert wrapper.exists(), "prototype_bwrap.sh missing"

    # Only run this test if a compiled seccomp filter is present (or user overrides via BWRAP_SECCOMP_BIN)
    seccomp_bin = os.environ.get("BWRAP_SECCOMP_BIN") or str(repo_root / "scripts" / "bwrap-seccomp.bin")
    if not Path(seccomp_bin).is_file():
        pytest.skip("no compiled seccomp filter found; set BWRAP_SECCOMP_BIN to run this test")

    proc = subprocess.run(["/bin/bash", str(wrapper), "smartcleaner.plugins.test_isolated_plugin", "TestIsolatedPlugin", "scan"], capture_output=True, text=True)
    assert proc.returncode == 0, f"wrapper with seccomp failed: {proc.stderr}"
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
