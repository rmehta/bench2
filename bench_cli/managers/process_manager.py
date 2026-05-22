from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


@dataclass
class ProcessDefinition:
    name: str
    command: str
    log_file: Path


class ProcessManager(ABC):
    def __init__(self, bench: "Bench") -> None:
        self.bench = bench

    @abstractmethod
    def generate_config(self) -> None:
        """Write the process manager config file(s) to bench.config_path."""

    @abstractmethod
    def start(self) -> None:
        """Start all bench processes."""

    @abstractmethod
    def stop(self) -> None:
        """Stop all bench processes."""

    @abstractmethod
    def is_running(self) -> bool:
        """Return True if any managed process is currently running."""

    def _process_definitions(self) -> List[ProcessDefinition]:
        definitions = []
        definitions.append(self._web_definition())
        definitions.append(self._socketio_definition())
        definitions.extend(self._worker_definitions("default", self.bench.config.workers.default_count))
        definitions.extend(self._worker_definitions("short", self.bench.config.workers.short_count))
        definitions.extend(self._worker_definitions("long", self.bench.config.workers.long_count))
        definitions.append(self._redis_definition("redis_cache", "redis_cache.conf"))
        definitions.append(self._redis_definition("redis_queue", "redis_queue.conf"))
        definitions.append(self._redis_definition("redis_socketio", "redis_socketio.conf"))
        return definitions

    def _web_definition(self) -> ProcessDefinition:
        port = self.bench.config.http_port
        sites = self.bench.sites_path
        bench_bin = self.bench.env_path / "bin" / "bench"
        command = f"cd {sites} && {bench_bin} frappe serve --port {port} --noreload"
        return ProcessDefinition(
            name="web",
            command=command,
            log_file=self.bench.logs_path / "web.log",
        )

    def _socketio_definition(self) -> ProcessDefinition:
        sites = self.bench.sites_path
        command = f"cd {sites} && node {self.bench.apps_path}/frappe/socketio.js"
        return ProcessDefinition(
            name="socketio",
            command=command,
            log_file=self.bench.logs_path / "socketio.log",
        )

    def _worker_definitions(self, queue: str, count: int) -> List[ProcessDefinition]:
        sites = self.bench.sites_path
        definitions = []
        for index in range(1, count + 1):
            name = f"worker_{queue}_{index}"
            command = f"cd {sites} && {self.bench.env_path}/bin/bench frappe worker --queue {queue}"
            definitions.append(ProcessDefinition(
                name=name,
                command=command,
                log_file=self.bench.logs_path / f"{name}.log",
            ))
        return definitions

    def _redis_definition(self, name: str, config_filename: str) -> ProcessDefinition:
        command = f"redis-server {self.bench.config_path}/{config_filename}"
        return ProcessDefinition(
            name=name,
            command=command,
            log_file=self.bench.logs_path / f"{name}.log",
        )


class ProcessManagerFactory:
    @staticmethod
    def create(bench: "Bench") -> ProcessManager:
        from bench_cli.managers.honcho_process_manager import HonchoProcessManager
        from bench_cli.managers.supervisor_process_manager import SupervisorProcessManager

        if bench.config.process_manager == "supervisor":
            return SupervisorProcessManager(bench)
        return HonchoProcessManager(bench)
