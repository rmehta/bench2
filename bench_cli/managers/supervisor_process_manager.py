from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bench_cli.managers.process_manager import ProcessManager
from bench_cli.utils import run_command

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench

_SUPERVISOR_HEADER = """\
[unix_http_server]
file=%(ENV_BENCH_ROOT)s/pids/supervisor.sock
chmod=0700

[supervisord]
logfile=%(ENV_BENCH_ROOT)s/logs/supervisord.log
logfile_maxbytes=50MB
logfile_backups=10
loglevel=info
pidfile=%(ENV_BENCH_ROOT)s/pids/supervisord.pid
nodaemon=false

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix://%(ENV_BENCH_ROOT)s/pids/supervisor.sock

"""

_PROGRAM_TEMPLATE = """\
[program:{name}]
command=%(ENV_BENCH_ROOT)s/{relative_command}
directory=%(ENV_BENCH_ROOT)s
autostart=true
autorestart=true
stdout_logfile=%(ENV_BENCH_ROOT)s/logs/{name}.log
stderr_logfile=%(ENV_BENCH_ROOT)s/logs/{name}.error.log

"""


class SupervisorProcessManager(ProcessManager):
    def __init__(self, bench: "Bench") -> None:
        super().__init__(bench)

    @property
    def socket_path(self) -> Path:
        return self.bench.pids_path / "supervisor.sock"

    @property
    def conf_path(self) -> Path:
        return self.bench.config_path / "supervisor.conf"

    def generate_config(self) -> None:
        content = _SUPERVISOR_HEADER
        bench_root = str(self.bench.path)
        for process_definition in self._process_definitions():
            relative_command = process_definition.command.replace(bench_root + "/", "")
            content += _PROGRAM_TEMPLATE.format(
                name=process_definition.name,
                relative_command=relative_command,
            )
        self.conf_path.write_text(content)

    def start(self) -> None:
        import os
        env = {**os.environ, "BENCH_ROOT": str(self.bench.path)}
        if not self.is_running():
            run_command(["supervisord", "-c", str(self.conf_path)], env=env)
        else:
            run_command(["supervisorctl", "-c", str(self.conf_path), "reload"], env=env)

    def stop(self) -> None:
        run_command(["supervisorctl", "-c", str(self.conf_path), "shutdown"])

    def is_running(self) -> bool:
        if not self.socket_path.exists():
            return False
        try:
            run_command(["supervisorctl", "-c", str(self.conf_path), "status"])
            return True
        except Exception:
            return False

    def status(self) -> str:
        result = run_command(["supervisorctl", "-c", str(self.conf_path), "status"])
        return result.stdout.decode() if result.stdout else ""
