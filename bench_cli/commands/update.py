from __future__ import annotations

import click

from bench_cli.core.bench import Bench
from bench_cli.exceptions import CommandError
from bench_cli.managers.process_manager import ProcessManagerFactory
from bench_cli.managers.python_env_manager import PythonEnvManager


class UpdateCommand:
    def __init__(self, bench: Bench, skip_confirm: bool = False) -> None:
        self.bench = bench
        self.skip_confirm = skip_confirm

    def run(self) -> None:
        self._warn_if_running()
        self._update_apps()
        self._reinstall_apps()
        self._migrate_sites()

    def _warn_if_running(self) -> None:
        process_manager = ProcessManagerFactory.create(self.bench)
        if not process_manager.is_running():
            return
        click.echo(
            "Warning: bench processes appear to be running. "
            "Updating while running may cause instability."
        )
        if not self.skip_confirm:
            click.confirm("Continue anyway?", abort=True)

    def _update_apps(self) -> None:
        for app in self.bench.apps():
            click.echo(f"Updating {app.config.name}...")
            try:
                app.update()
            except CommandError as error:
                click.echo(f"  Error updating {app.config.name}: {error}", err=True)

    def _reinstall_apps(self) -> None:
        python_env_manager = PythonEnvManager(self.bench)
        for app in self.bench.apps():
            click.echo(f"Reinstalling {app.config.name}...")
            python_env_manager.install_app(app)

    def _migrate_sites(self) -> None:
        failed = False
        for site in self.bench.sites():
            click.echo(f"Migrating {site.config.name}...")
            try:
                site.migrate()
            except CommandError as error:
                click.echo(f"  Migration failed for {site.config.name}: {error}", err=True)
                failed = True
        if failed:
            raise SystemExit(1)
