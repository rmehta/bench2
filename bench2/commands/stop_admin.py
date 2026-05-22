from __future__ import annotations

import os
import signal
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from bench2.core.bench import Bench


class StopAdminCommand:
    def __init__(self, bench: "Bench") -> None:
        self.bench = bench

    @property
    def _pid_file(self):
        return self.bench.pids_path / "admin.pid"

    @property
    def _port_file(self):
        return self.bench.pids_path / "admin.port"

    def run(self) -> None:
        if not self._pid_file.exists():
            click.echo("Admin is not running.")
            return

        pid = int(self._pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # Already dead — still clean up state files

        self._pid_file.unlink(missing_ok=True)
        self._port_file.unlink(missing_ok=True)
        click.echo("Admin stopped.")
