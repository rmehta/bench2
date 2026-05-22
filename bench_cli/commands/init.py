from __future__ import annotations

import click

from bench_cli.core.bench import Bench
from bench_cli.managers.python_env_manager import PythonEnvManager
from bench_cli.managers.redis_manager import RedisManager
from bench_cli.managers.process_manager import ProcessManagerFactory


class InitCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        self._step(1, "Validate bench.yml")
        self.bench.config.validate()

        self._step(2, "Install system packages")
        self._install_system_packages()

        self._step(3, "Create bench directory structure")
        self.bench.create_directories()
        self.bench.write_common_site_config()

        self._step(4, "Create Python virtualenv")
        python_env_manager = PythonEnvManager(self.bench)
        python_env_manager.ensure_python()
        python_env_manager.create_venv()
        python_env_manager.generate_bench_script()

        self._step(5, "Clone apps")
        for app in self.bench.apps():
            if not app.is_cloned:
                click.echo(f"  Cloning {app.config.name}...")
                app.clone()

        self._step(6, "Install Python dependencies")
        for app in self.bench.apps():
            click.echo(f"  Installing {app.config.name}...")
            python_env_manager.install_app(app)
        self.bench.write_apps_txt()

        self._step(7, "Install Node.js")
        python_env_manager.install_node()

        self._step(8, "Install Node.js dependencies")
        python_env_manager.install_node_dependencies()

        self._step(9, "Configure Redis")
        RedisManager(self.bench.config.redis, self.bench).generate_configs()

        self._step(10, "Create sites")
        self._create_sites()

        self._step(11, "Install apps on sites")
        self._install_apps_on_sites()

        self._step(12, "Build assets")
        python_env_manager.build_assets()

        self._step(13, "Generate process manager config")
        ProcessManagerFactory.create(self.bench).generate_config()

        click.echo("Bench initialised successfully. Run: bench start")

    def _step(self, number: int, description: str) -> None:
        click.echo(f"[{number}/13] {description}...")

    def _install_system_packages(self) -> None:
        from bench_cli.managers.mariadb_manager import MariaDBManager
        mariadb_manager = MariaDBManager(self.bench.config.mariadb)
        mariadb_manager.install()
        mariadb_manager.start()
        RedisManager(self.bench.config.redis, self.bench).install()
        PythonEnvManager(self.bench).ensure_python()

    def _create_sites(self) -> None:
        for site in self.bench.sites():
            if not site.exists:
                click.echo(f"  Creating site {site.config.name}...")
                site.create()

    def _install_apps_on_sites(self) -> None:
        framework_name = self.bench.config.framework_app.name
        for site in self.bench.sites():
            for app_name in site.config.apps:
                if app_name == framework_name:
                    continue
                click.echo(f"  Installing {app_name} on {site.config.name}...")
                site.install_app(app_name)
