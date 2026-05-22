from __future__ import annotations

import time
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class LogFileInfo:
    filename: str
    size_bytes: int
    last_modified: datetime
    process_name: str


_MAX_STREAM_LINES = 5000


class LogReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def list_logs(self) -> list[LogFileInfo]:
        logs_dir = self._bench_root / "logs"
        if not logs_dir.exists():
            return []

        result = []
        for log_path in sorted(logs_dir.glob("*.log")):
            stat = log_path.stat()
            result.append(LogFileInfo(
                filename=log_path.name,
                size_bytes=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                process_name=log_path.stem,
            ))
        return result

    def read_tail(self, filename: str, lines: int = 200) -> list[str]:
        log_path = self._validated_path(filename)
        if not log_path.exists():
            raise FileNotFoundError(f"Log file not found: {filename}")
        all_lines = log_path.read_text(errors="replace").splitlines()
        return all_lines[-lines:]

    def stream_tail(self, filename: str) -> Generator[str, None, None]:
        log_path = self._validated_path(filename)
        log_path.touch()
        yielded = 0

        with open(log_path, "r", errors="replace") as file_handle:
            file_handle.seek(0, 2)  # seek to end
            while yielded < _MAX_STREAM_LINES:
                line = file_handle.readline()
                if line:
                    yield line.rstrip("\n")
                    yielded += 1
                else:
                    time.sleep(0.2)

    def _validated_path(self, filename: str) -> Path:
        if "/" in filename or "\\" in filename:
            raise ValueError(f"Invalid filename: {filename!r}")
        logs_dir = (self._bench_root / "logs").resolve()
        resolved = (self._bench_root / "logs" / filename).resolve()
        if resolved.parent != logs_dir:
            raise ValueError(f"Path traversal detected in filename: {filename!r}")
        return resolved
