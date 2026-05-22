from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from bench_cli.exceptions import BenchError
from bench_cli.managers.process_manager import ProcessManager

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


class HonchoProcessManager(ProcessManager):
    def __init__(self, bench: "Bench") -> None:
        super().__init__(bench)

    @property
    def procfile_path(self) -> Path:
        return self.bench.config_path / "Procfile"

    @property
    def pid_file(self) -> Path:
        return self.bench.pids_path / "bench.pid"

    def generate_config(self) -> None:
        lines = []
        for process_definition in self._process_definitions():
            lines.append(f"{process_definition.name}: {process_definition.command}\n")
        self.procfile_path.write_text("".join(lines))

    def start(self) -> None:
        from honcho.manager import Manager

        self.pid_file.write_text(str(os.getpid()))
        try:
            manager = Manager()
            for line in self.procfile_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, _, command = line.partition(":")
                manager.add_process(name.strip(), command.strip())
            manager.loop()
        finally:
            self.pid_file.unlink(missing_ok=True)

    def stop(self) -> None:
        if not self.pid_file.exists():
            raise BenchError("Bench is not running (no PID file found at pids/bench.pid).")
        pid = int(self.pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            self.pid_file.unlink(missing_ok=True)
            raise BenchError(f"Process {pid} is not running. Removed stale PID file.")

    def is_running(self) -> bool:
        process_names = [pd.name for pd in self._process_definitions()]
        pattern = "|".join(process_names)
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
        )
        return bool(result.stdout.strip())
