import sys
from pathlib import Path

import click

from bench_cli.exceptions import BenchError, BenchError

# Options that bench-cli's own group handles; everything else is treated as a
# signal that the invocation should be forwarded to the Frappe bench binary.
_OWN_GROUP_OPTIONS = frozenset(["--verbose", "--yes", "--help", "-h"])


def find_bench_root() -> Path:
    current = Path.cwd()
    for directory in [current, *current.parents]:
        if (directory / "bench.yml").exists():
            return directory
    raise BenchError("No bench.yml found in current directory or any parent directory.")


def _load_bench() -> "Bench":
    from bench_cli.config.bench_config import BenchConfig
    from bench_cli.core.bench import Bench

    bench_root = find_bench_root()
    config = BenchConfig.from_file(bench_root / "bench.yml")
    return Bench(config, bench_root)


def _is_frappe_passthrough(args: list[str]) -> bool:
    """
    Return True when the argv looks like a Frappe bench command rather than a
    bench-cli command, so we can forward it before Click tries to parse it.

    Strategy: iterate tokens left-to-right.
    - A token that is a known group option (--verbose / --yes / --help) → skip.
    - A token starting with '-' that is NOT a known group option → unknown
      option like --site → this is a Frappe invocation.
    - The first bare (non-option) token → if it's a registered bench-cli
      command it stays in bench-cli; otherwise it's forwarded to Frappe.
    """
    for arg in args:
        if arg.startswith("-"):
            if arg in _OWN_GROUP_OPTIONS:
                continue
            return True  # unknown option (e.g. --site, --force)
        # First positional token: is it a bench-cli command?
        return arg not in cli.commands
    return False


@click.group()
@click.option("--verbose", is_flag=True, default=False, help="Show full tracebacks on error.")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation prompts.")
@click.pass_context
def cli(context: click.Context, verbose: bool, yes: bool) -> None:
    context.ensure_object(dict)
    context.obj["verbose"] = verbose
    context.obj["yes"] = yes


@cli.command()
@click.pass_context
def new(context: click.Context) -> None:
    try:
        from bench_cli.commands.new import NewCommand
        NewCommand(Path.cwd()).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def init(context: click.Context) -> None:
    try:
        from bench_cli.commands.init import InitCommand
        bench = _load_bench()
        InitCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command("frappe", context_settings={"ignore_unknown_options": True, "allow_extra_args": True}, add_help_option=False)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def frappe_cmd(context: click.Context, args: tuple) -> None:
    """Run a frappe CLI command (proxied to env/bin/bench frappe)."""
    try:
        from bench_cli.commands.frappe_cmd import FrappeCommand
        bench = _load_bench()
        FrappeCommand(bench).run(args)
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command("get-app")
@click.argument("repo")
@click.option("--branch", default="", help="Git branch to checkout.")
def get_app(repo: str, branch: str) -> None:
    """Clone and install an app from a git repository into this bench."""
    from pathlib import PurePosixPath

    try:
        from bench_cli.config.app_config import AppConfig
        from bench_cli.core.app import App
        from bench_cli.managers.python_env_manager import PythonEnvManager

        bench = _load_bench()

        name = PurePosixPath(repo.rstrip("/")).name
        if name.endswith(".git"):
            name = name[:-4]

        app_cfg = AppConfig(name=name, repo=repo, branch=branch or "main")
        app = App(app_cfg, bench)

        if app.is_cloned:
            click.echo(f"'{name}' already cloned at {app.path}, skipping clone.")
        else:
            click.echo(f"Cloning {name}...")
            app.clone()

        click.echo(f"Installing {name}...")
        PythonEnvManager(bench).install_app(app)

        apps_txt = bench.sites_path / "apps.txt"
        existing = apps_txt.read_text().splitlines() if apps_txt.exists() else []
        if name not in existing:
            apps_txt.write_text("\n".join(existing + [name]) + "\n")

        click.echo(f"\n'{name}' installed successfully.")
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def start(context: click.Context) -> None:
    try:
        from bench_cli.commands.run import RunCommand
        bench = _load_bench()
        RunCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def stop(context: click.Context) -> None:
    try:
        from bench_cli.commands.stop import StopCommand
        bench = _load_bench()
        StopCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command("kill-orphaned")
@click.pass_context
def kill_orphaned(context: click.Context) -> None:
    """Kill orphaned bench processes left behind by a crashed or force-killed bench."""
    try:
        from bench_cli.commands.kill_orphaned import KillOrphanedCommand
        bench = _load_bench()
        yes = context.obj.get("yes", False)
        KillOrphanedCommand(bench, skip_confirm=yes).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command("start-admin")
@click.option("--port", default=None, type=int, help="Port for the admin interface (overrides bench.yml admin.port).")
@click.pass_context
def start_admin(context: click.Context, port: int | None) -> None:
    """Start the admin UI as a background daemon."""
    try:
        from bench_cli.commands.start_admin import StartAdminCommand
        bench = _load_bench()
        StartAdminCommand(bench, port=port).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command("stop-admin")
@click.pass_context
def stop_admin(context: click.Context) -> None:
    """Stop the background admin UI."""
    try:
        from bench_cli.commands.stop_admin import StopAdminCommand
        bench = _load_bench()
        StopAdminCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def build(context: click.Context) -> None:
    try:
        from bench_cli.commands.build import BuildCommand
        bench = _load_bench()
        BuildCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def update(context: click.Context) -> None:
    try:
        from bench_cli.commands.update import UpdateCommand
        bench = _load_bench()
        yes = context.obj.get("yes", False)
        UpdateCommand(bench, skip_confirm=yes).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command("update-config")
def update_config() -> None:
    """Regenerate all config files (Procfile/supervisor, redis, nginx, common_site_config) from bench.yml."""
    try:
        from bench_cli.commands.update_config import UpdateConfigCommand
        bench = _load_bench()
        UpdateConfigCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command("update-bench")
def update_bench() -> None:
    """Pull the latest bench-cli source and reinstall the tool."""
    try:
        from bench_cli.commands.update_bench import UpdateBenchCliCommand
        UpdateBenchCliCommand().run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@cli.command()
@click.option("--port", default=8001, type=int, help="Port for the admin interface.")
@click.option("--host", default="127.0.0.1", help="Host for the admin interface.")
@click.pass_context
def admin(context: click.Context, port: int, host: str) -> None:
    """Start the admin web interface."""
    from bench_cli.admin.app import create_app
    bench_root = find_bench_root()
    app = create_app(bench_root)
    app.run(host=host, port=port, threaded=True, debug=True)


@cli.group()
def setup() -> None:
    pass


@setup.command("nginx")
@click.pass_context
def setup_nginx(context: click.Context) -> None:
    try:
        from bench_cli.commands.setup.nginx import SetupNginxCommand
        bench = _load_bench()
        SetupNginxCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@setup.command("letsencrypt")
@click.pass_context
def setup_letsencrypt(context: click.Context) -> None:
    try:
        from bench_cli.commands.setup.letsencrypt import SetupLetsEncryptCommand
        bench = _load_bench()
        SetupLetsEncryptCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


@setup.command("production")
@click.pass_context
def setup_production(context: click.Context) -> None:
    try:
        from bench_cli.commands.setup.production import SetupProductionCommand
        bench = _load_bench()
        SetupProductionCommand(bench).run()
    except BenchError as error:
        click.echo(str(error), err=True)
        sys.exit(1)


def main() -> None:
    """
    Entry point.  Checks whether the invocation looks like a Frappe bench
    command (unknown option like --site, or unknown subcommand like migrate).
    If so, forward the entire argv to `env/bin/bench frappe …` before Click
    ever parses the args — avoiding Click's strict option validation.
    Otherwise hand off to the normal Click group.
    """
    args = sys.argv[1:]
    if _is_frappe_passthrough(args):
        try:
            from bench_cli.commands.frappe_cmd import FrappeCommand
            bench = _load_bench()
            FrappeCommand(bench).run_raw(["frappe", *args])
        except BenchError as error:
            click.echo(str(error), err=True)
            sys.exit(1)
    else:
        cli()
