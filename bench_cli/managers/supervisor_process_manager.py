from __future__ import annotations

import shutil
import os
from pathlib import Path
from typing import TYPE_CHECKING

from bench_cli.managers.process_manager import ProcessManager, ProcessDefinition, _cli_root
from bench_cli.managers.admin_env_manager import AdminEnvManager
from bench_cli.utils import run_command

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


class SupervisorProcessManager(ProcessManager):
    """Manages bench processes via supervisord (used in production)."""

    @property
    def supervisor_conf_path(self) -> Path:
        return self.bench.config_path / "supervisor" / f"{self.bench.config.name}.conf"

    @property
    def supervisor_include_dir(self) -> Path:
        return Path("/etc/supervisor/conf.d")

    def generate_config(self) -> None:
        AdminEnvManager(_cli_root()).ensure()
        self.supervisor_conf_path.parent.mkdir(parents=True, exist_ok=True)
        conf = self._render_supervisor_conf()
        self.supervisor_conf_path.write_text(conf)

    def install_config(self) -> None:
        symlink = self.supervisor_include_dir / f"{self.bench.config.name}.conf"
        if symlink.exists() or symlink.is_symlink():
            symlink.unlink()
        try:
            os.symlink(self.supervisor_conf_path, symlink)
        except PermissionError:
            print(
                f"Permission denied creating symlink at {symlink}.\n"
                f"Run manually:\n"
                f"  sudo ln -sf {self.supervisor_conf_path} {symlink}\n"
                f"Then reload supervisord:\n"
                f"  sudo supervisorctl reread && sudo supervisorctl update"
            )

    def reload(self) -> None:
        run_command(["supervisorctl", "reread"])
        run_command(["supervisorctl", "update"])

    def start(self) -> None:
        run_command(["supervisorctl", "start", f"{self.bench.config.name}:*"])

    def stop(self) -> None:
        run_command(["supervisorctl", "stop", f"{self.bench.config.name}:*"])

    def is_running(self) -> bool:
        import subprocess
        result = subprocess.run(
            ["supervisorctl", "status", f"{self.bench.config.name}:*"],
            capture_output=True, text=True,
        )
        return "RUNNING" in result.stdout

    def _render_supervisor_conf(self) -> str:
        defs = self._prod_process_definitions()
        program_names = ",".join(
            f"{self.bench.config.name}-{pd.name.replace('_', '-')}" for pd in defs
        )
        group = f"[group:{self.bench.config.name}]\nprograms={program_names}\n\n"
        blocks = [self._render_program(pd, pd.name.replace("_", "-")) for pd in defs]
        return group + "".join(blocks)

    def _render_program(self, pd: ProcessDefinition, safe_name: str) -> str:
        import re
        log_dir = self.bench.logs_path
        cmd = pd.command

        # Extract leading VAR=value env assignments
        env_vars: list[str] = []
        while True:
            m = re.match(r'^([A-Z_][A-Z0-9_]*)=(\S+)\s+', cmd)
            if not m:
                break
            env_vars.append(f'{m.group(1)}="{m.group(2)}"')
            cmd = cmd[m.end():]

        # Extract leading `cd /dir && ` working-directory prefix
        directory = ""
        m2 = re.match(r'^cd\s+(\S+)\s*&&\s*', cmd)
        if m2:
            directory = m2.group(1)
            cmd = cmd[m2.end():]

        lines = [
            f"[program:{self.bench.config.name}-{safe_name}]",
            f"command={cmd}",
            "autostart=true",
            "autorestart=true",
            f"stdout_logfile={log_dir}/{pd.name}.log",
            f"stderr_logfile={log_dir}/{pd.name}.error.log",
            "user=root",
            "stopasgroup=true",
            "killasgroup=true",
        ]
        if directory:
            lines.insert(2, f"directory={directory}")
        if env_vars:
            lines.insert(2, f"environment={','.join(env_vars)}")
        return "\n".join(lines) + "\n\n"

    def _prod_process_definitions(self) -> list[ProcessDefinition]:
        """Process definitions for production (no dev processes)."""
        from bench_cli.managers.process_manager import ProcessDefinition
        defs = [
            self._web_definition(),
            self._socketio_definition(),
            self._admin_definition(),
            *self._worker_definitions("default", self.bench.config.workers.default_count),
            *self._worker_definitions("short", self.bench.config.workers.short_count),
            *self._worker_definitions("long", self.bench.config.workers.long_count),
        ]
        if self.bench.config.redis.is_single_instance:
            defs.append(self._redis_definition("redis", "redis.conf"))
        else:
            defs.append(self._redis_definition("redis_cache", "redis_cache.conf"))
            defs.append(self._redis_definition("redis_queue", "redis_queue.conf"))
            defs.append(self._redis_definition("redis_socketio", "redis_socketio.conf"))
        return defs
