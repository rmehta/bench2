from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, List

from bench_cli.config.bench_config import BenchConfig

if TYPE_CHECKING:
    from bench_cli.core.app import App
    from bench_cli.core.site import Site


class Bench:
    def __init__(self, config: BenchConfig, path: Path) -> None:
        self.config = config
        self.path = path

    @property
    def apps_path(self) -> Path:
        return self.path / "apps"

    @property
    def sites_path(self) -> Path:
        return self.path / "sites"

    @property
    def env_path(self) -> Path:
        return self.path / "env"

    @property
    def logs_path(self) -> Path:
        return self.path / "logs"

    @property
    def config_path(self) -> Path:
        return self.path / "config"

    @property
    def pids_path(self) -> Path:
        return self.path / "pids"

    @property
    def python(self) -> Path:
        return self.env_path / "bin" / "python"

    def apps(self) -> List["App"]:
        from bench_cli.core.app import App
        return [App(app_config, self) for app_config in self.config.apps]

    def sites(self) -> List["Site"]:
        from bench_cli.core.site import Site
        return [Site(site_config, self) for site_config in self.config.sites]

    def create_directories(self) -> None:
        for directory in [
            self.apps_path,
            self.sites_path,
            self.sites_path / "assets",
            self.logs_path,
            self.config_path,
            self.pids_path,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def write_apps_txt(self) -> None:
        apps_txt = self.sites_path / "apps.txt"
        app_names = "\n".join(app.name for app in self.config.apps)
        apps_txt.write_text(app_names + "\n")

    def write_common_site_config(self) -> None:
        r = self.config.redis
        config = {
            "redis_cache": f"redis://localhost:{r.cache_port}",
            "redis_queue": f"redis://localhost:{r.queue_port}",
            "redis_socketio": f"redis://localhost:{r.socketio_port}",
            "socketio_port": self.config.socketio_port,
            "webserver_port": self.config.http_port,
        }
        config_path = self.sites_path / "common_site_config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n")
