from click.testing import CliRunner

from smartcleaner.cli.commands import cli


def test_clean_browser_cache_cli(tmp_path, monkeypatch):
    base = tmp_path / "browser" / "cache"
    d = base / "profile" / "Cache"
    d.mkdir(parents=True)
    f = d / "cache1.bin"
    f.write_bytes(b"x" * 1024)

    runner = CliRunner()
    result = runner.invoke(cli, ["clean", "browser-cache", "--base-dir", str(base), "--dry-run"])
    assert result.exit_code == 0
    assert "Found" in result.output

    result = runner.invoke(cli, ["clean", "browser-cache", "--base-dir", str(base), "--yes"])
    assert result.exit_code == 0
    assert "Cleaned" in result.output


def test_clean_thumbnails_cli(tmp_path, monkeypatch):
    d = tmp_path / "thumbnails"
    d.mkdir(parents=True)
    f = d / "thumb1.png"
    f.write_bytes(b"0" * 512)

    runner = CliRunner()
    result = runner.invoke(cli, ["clean", "thumbnails", "--cache-dir", str(d), "--dry-run"])
    assert result.exit_code == 0
    assert "Found" in result.output

    result = runner.invoke(cli, ["clean", "thumbnails", "--cache-dir", str(d), "--yes"])
    assert result.exit_code == 0
    assert "Cleaned" in result.output


def test_clean_tmp_cli(tmp_path, monkeypatch):
    d = tmp_path / "tmpdir"
    d.mkdir(parents=True)
    f = d / "tempfile"
    f.write_bytes(b"0" * 256)

    runner = CliRunner()
    result = runner.invoke(cli, ["clean", "tmp", "--base-dir", str(d), "--dry-run"])
    assert result.exit_code == 0
    assert "Found" in result.output

    result = runner.invoke(cli, ["clean", "tmp", "--base-dir", str(d), "--yes"])
    assert result.exit_code == 0
    assert "Cleaned" in result.output
