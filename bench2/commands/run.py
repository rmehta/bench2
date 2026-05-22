from __future__ import annotations

import click

from bench2.core.bench import Bench
from bench2.exceptions import BenchError
from bench2.managers.process_manager import ProcessManagerFactory


class RunCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        process_manager = ProcessManagerFactory.create(self.bench)
        self._check_config_exists(process_manager)
        process_manager.start()

    def _check_config_exists(self, process_manager) -> None:
        from bench2.managers.honcho_process_manager import HonchoProcessManager
        from bench2.managers.supervisor_process_manager import SupervisorProcessManager

        if isinstance(process_manager, HonchoProcessManager):
            config_file = process_manager.procfile_path
            config_name = "config/Procfile"
        else:
            config_file = process_manager.conf_path
            config_name = "config/supervisor.conf"

        if not config_file.exists():
            raise BenchError(
                f"Process manager config not found at {config_name}. "
                "Run 'bench2 init' first to initialise the bench, then 'bench2 start'."
            )
