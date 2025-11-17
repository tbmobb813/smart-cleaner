# Scheduled GC (garbage collection) for SmartCleaner backups

You can schedule periodic garbage collection (pruning old backups) using a systemd timer or cron.

Quick summary

- The `UndoManager.prune_backups()` method (and the CLI `gc` command) can remove old backup directories created under the configured `backup_dir`.
- Backups are stored in directories named like `op_<id>_<timestamp>` under the backup dir. The pruning logic parses the trailing timestamp.

Example systemd unit and timer (user service)

Drop the following files under `~/.config/systemd/user/`.

smartcleaner-gc.service

[Unit]
Description=SmartCleaner GC

[Service]
Type=oneshot
ExecStart=/usr/bin/env python3 -m smartcleaner.cli.commands gc --keep-last 30 --yes

smartcleaner-gc.timer

[Unit]
Description=Run SmartCleaner GC daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=default.target

Enable and start (user service):

```bash
systemctl --user enable --now smartcleaner-gc.timer
```

Cron example

If you prefer cron, add a line to your crontab (daily at 3am):

```cron
0 3 * * * PYTHONPATH=/path/to/repo/src /usr/bin/env python3 -m smartcleaner.cli.commands gc --keep-last 30 --yes
```

Retention policy

Decide on either or both policies:

- Keep the N most recent backups: `--keep-last N`.
- Remove backups older than D days: `--older-than-days D`.

Adjust the `--keep-last` / `--older-than-days` arguments to match your retention needs. The `gc` command prompts for confirmation by default; use `--yes` to run non-interactively.
