from __future__ import annotations

import click

from bench_cli.core.bench import Bench
from bench_cli.managers.process_manager import ProcessManagerFactory


class StopCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        ProcessManagerFactory.create(self.bench).stop()
        click.echo("Bench stopped.")
