from click.testing import CliRunner
from smartcleaner.cli.commands import cli


def test_clean_apt_cache_dry_run_and_clean(tmp_path, monkeypatch):
    cache_dir = tmp_path / 'apt' / 'archives'
    partial = cache_dir / 'partial'
    partial.mkdir(parents=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    f1 = cache_dir / 'package1.deb'
    f1.write_bytes(b'0' * 1024 * 5)
    p1 = partial / 'incomplete.part'
    p1.write_bytes(b'0' * 200)

    runner = CliRunner()
    # Dry-run should only report items
    result = runner.invoke(cli, ['clean', 'apt-cache', '--cache-dir', str(cache_dir), '--dry-run'])
    assert result.exit_code == 0
    assert 'Found' in result.output
    assert 'Dry-run' in result.output

    # Monkeypatch run_command to simulate apt-get clean
    def fake_run(cmd, sudo=False, **kwargs):
        class CP:
            stdout = ''
            returncode = 0

        return CP()

    monkeypatch.setattr('smartcleaner.utils.privilege.run_command', fake_run)

    result = runner.invoke(cli, ['clean', 'apt-cache', '--cache-dir', str(cache_dir), '--yes'])
    assert result.exit_code == 0
    assert 'Cleaned' in result.output
