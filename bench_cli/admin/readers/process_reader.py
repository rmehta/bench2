from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bench_cli.config.bench_config import BenchConfig


@dataclass
class ProcessInfo:
    name: str
    status: str  # 'running' | 'stopped' | 'error' | 'unknown'
    pid: int | None
    uptime: str | None
    log_file: Path


class ProcessReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def read_all(self) -> list[ProcessInfo]:
        config = BenchConfig.from_file(self._bench_root / "bench.yml")
        if config.process_manager == "supervisor":
            return self._read_supervisor()
        return self._read_honcho()

    def _read_supervisor(self) -> list[ProcessInfo]:
        supervisor_conf = self._bench_root / "config" / "supervisor.conf"
        result = subprocess.run(
            ["supervisorctl", "-c", str(supervisor_conf), "status"],
            capture_output=True,
            text=True,
        )
        processes = []
        for line in result.stdout.splitlines():
            info = self._parse_supervisor_line(line)
            if info is not None:
                processes.append(info)
        return processes

    def _parse_supervisor_line(self, line: str) -> ProcessInfo | None:
        parts = line.split()
        if len(parts) < 2:
            return None

        name = parts[0]
        raw_status = parts[1].lower()
        status = self._normalize_supervisor_status(raw_status)

        pid: int | None = None
        uptime: str | None = None

        if status == "running" and len(parts) >= 6:
            for i, part in enumerate(parts):
                if part == "pid":
                    try:
                        pid = int(parts[i + 1].rstrip(","))
                    except (IndexError, ValueError):
                        pass
                if part == "uptime":
                    try:
                        uptime = parts[i + 1]
                    except IndexError:
                        pass

        log_file = self._bench_root / "logs" / f"{name}.log"
        return ProcessInfo(name=name, status=status, pid=pid, uptime=uptime, log_file=log_file)

    def _normalize_supervisor_status(self, raw: str) -> str:
        mapping = {
            "running": "running",
            "stopped": "stopped",
            "fatal": "error",
            "error": "error",
            "starting": "running",
            "stopping": "stopped",
            "exited": "stopped",
            "backoff": "error",
        }
        return mapping.get(raw, "unknown")

    def _read_honcho(self) -> list[ProcessInfo]:
        pids_dir = self._bench_root / "pids"
        if not pids_dir.exists():
            return []

        processes = []
        for pid_file in sorted(pids_dir.glob("*.pid")):
            name = pid_file.stem
            info = self._read_honcho_process(name, pid_file)
            processes.append(info)
        return processes

    def _read_honcho_process(self, name: str, pid_file: Path) -> ProcessInfo:
        log_file = self._bench_root / "logs" / f"{name}.log"
        try:
            pid = int(pid_file.read_text().strip())
        except (ValueError, OSError):
            return ProcessInfo(name=name, status="unknown", pid=None, uptime=None, log_file=log_file)

        try:
            os.kill(pid, 0)
            status = "running"
        except OSError:
            status = "stopped"

        return ProcessInfo(name=name, status=status, pid=pid, uptime=None, log_file=log_file)
