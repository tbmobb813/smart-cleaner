import subprocess


def test_cli_module_list(tmp_path):
    db_path = tmp_path / "cli_int.db"
    # Call the CLI module directly via the python -m entrypoint
    cmd = ["/usr/bin/python3", "-m", "smartcleaner.cli.commands", "list", "--db", str(db_path)]
    env = {**dict(PATH="/usr/bin"), "PYTHONPATH": "src"}
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # The command should run and exit 0 even with an empty DB
    assert res.returncode == 0
    assert "Operations" in res.stdout or "No operations" in res.stdout or res.stdout == ""
