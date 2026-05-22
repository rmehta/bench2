from __future__ import annotations

from bench_cli.core.bench import Bench
from bench_cli.utils import run_command


class BuildCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        bench_binary = str(self.bench.env_path / "bin" / "bench")
        run_command(
            [bench_binary, "frappe", "build", "--force"],
            cwd=self.bench.sites_path,
            stream_output=True,
        )
