from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bench_cli.config.bench_config import BenchConfig


@dataclass
class BenchSummary:
    name: str
    python_version: str
    process_manager: str
    app_count: int
    site_count: int


class BenchReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def config(self) -> BenchConfig:
        return BenchConfig.from_file(self._bench_root / "bench.yml")

    def summary(self) -> BenchSummary:
        config = self.config()
        return BenchSummary(
            name=config.name,
            python_version=config.python_version,
            process_manager=config.process_manager,
            app_count=len(config.apps),
            site_count=len(config.sites),
        )
