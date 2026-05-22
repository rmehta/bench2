from __future__ import annotations

import os
import signal
import subprocess
from typing import TYPE_CHECKING, List, Tuple

import click

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


class KillOrphanedCommand:
    def __init__(self, bench: "Bench", skip_confirm: bool = False) -> None:
        self.bench = bench
        self.skip_confirm = skip_confirm

    def run(self) -> None:
        orphaned = self._find_orphaned()

        if not orphaned:
            click.echo("No orphaned bench processes found.")
            return

        click.echo(f"Found {len(orphaned)} orphaned process(es):")
        for pid, cmdline in orphaned:
            click.echo(f"  [{pid}] {cmdline[:120]}")

        if not self.skip_confirm:
            click.confirm("Kill all?", abort=True)

        killed = 0
        for pid, _ in orphaned:
            try:
                os.kill(pid, signal.SIGTERM)
                killed += 1
            except ProcessLookupError:
                pass

        self._clean_stale_pid_files()
        click.echo(f"Killed {killed} process(es).")

    def _find_orphaned(self) -> List[Tuple[int, str]]:
        bench_path = str(self.bench.path.resolve())
        own_pid = os.getpid()

        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise click.ClickException("ps command not found — cannot scan for orphaned processes.")

        orphaned = []
        for line in result.stdout.splitlines()[1:]:  # skip header
            if bench_path not in line:
                continue
            parts = line.split(None, 10)
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            if pid == own_pid:
                continue
            cmdline = parts[10] if len(parts) > 10 else line
            orphaned.append((pid, cmdline.strip()))

        return orphaned

    def _clean_stale_pid_files(self) -> None:
        for name in ("bench.pid", "admin.pid", "admin.port"):
            pid_file = self.bench.pids_path / name
            if not pid_file.exists():
                continue
            if name.endswith(".port"):
                pid_file.unlink(missing_ok=True)
                continue
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
            except (ProcessLookupError, ValueError):
                pid_file.unlink(missing_ok=True)
