from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bench_cli.config.site_config import SiteConfig
from bench_cli.utils import run_command

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


class Site:
    def __init__(self, config: SiteConfig, bench: "Bench") -> None:
        self.config = config
        self.bench = bench

    @property
    def path(self) -> Path:
        return self.bench.sites_path / self.config.name

    @property
    def exists(self) -> bool:
        return (self.path / "site_config.json").exists()

    def _bench_binary(self) -> str:
        return str(self.bench.env_path / "bin" / "bench")

    def create(self) -> None:
        from bench_cli.managers.mariadb_manager import MariaDBManager

        mariadb = self.bench.config.mariadb
        socket_path = MariaDBManager(mariadb)._detect_socket()

        cmd = [
            self._bench_binary(), "frappe",
            "--site", self.config.name,
            "new-site", self.config.name,
            "--db-root-username", mariadb.admin_user,
            "--admin-password", self.config.admin_password,
        ]
        if socket_path:
            cmd += ["--db-socket", socket_path]
            # unix_socket auth ignores the password; pass a non-empty placeholder
            # so frappe doesn't fall back to an interactive getpass() prompt
            cmd += ["--db-root-password", mariadb.root_password or "socket_auth"]
        else:
            cmd += ["--db-host", mariadb.host, "--db-port", str(mariadb.port)]
            if mariadb.root_password:
                cmd += ["--db-root-password", mariadb.root_password]

        run_command(cmd, cwd=self.bench.sites_path, stream_output=True)

    def install_app(self, app_name: str) -> None:
        run_command([
            self._bench_binary(), "frappe",
            "--site", self.config.name,
            "install-app", app_name,
        ], cwd=self.bench.sites_path, stream_output=True)

    def migrate(self) -> None:
        run_command([
            self._bench_binary(), "frappe",
            "--site", self.config.name,
            "migrate",
        ], cwd=self.bench.sites_path, stream_output=True)
