from pathlib import Path

import click

from bench_cli.exceptions import BenchError

_BENCH_YML_TEMPLATE = """\
bench:
  name: my-bench
  python: "3.14"
  process_manager: honcho

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16

sites:
  - name: site1.localhost
    apps:
      - frappe

mariadb:
  host: localhost
  port: 3306
  root_password: "root"
  # version: "10.6"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000

workers:
  default: 2
  short: 1
  long: 1
"""


class NewCommand:
    def __init__(self, target_directory: Path) -> None:
        self.target_directory = target_directory

    def run(self) -> None:
        bench_yml = self.target_directory / "bench.yml"
        if bench_yml.exists():
            raise BenchError(
                f"bench.yml already exists at {bench_yml}. "
                "Remove it or run this command in a different directory."
            )
        bench_yml.write_text(_BENCH_YML_TEMPLATE)
        click.echo(f"Created bench.yml at {bench_yml}")
        click.echo("Edit it to configure your bench, then run: bench init")
