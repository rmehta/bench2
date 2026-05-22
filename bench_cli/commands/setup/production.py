from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from bench_cli.exceptions import ConfigError
from bench_cli.platform import is_linux

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


class SetupProductionCommand:
    def __init__(self, bench: "Bench") -> None:
        self.bench = bench

    def run(self) -> None:
        self.bench.config.validate()
        self._require_linux()
        self._require_supervisor()
        self._write_dns_multitenancy()
        self._setup_supervisor()
        self._setup_nginx()
        self._setup_letsencrypt_if_needed()
        self._print_summary()

    def _require_linux(self) -> None:
        if not is_linux():
            print(
                "Error: bench setup production only runs on Linux servers.\n"
                "On macOS, use 'bench start' with honcho for local development.",
                file=sys.stderr,
            )
            sys.exit(1)

    def _require_supervisor(self) -> None:
        if self.bench.config.process_manager != "supervisor":
            raise ConfigError(
                f"process_manager must be 'supervisor' for production setup, "
                f"got '{self.bench.config.process_manager}'."
            )

    def _write_dns_multitenancy(self) -> None:
        common_config_path = self.bench.sites_path / "common_site_config.json"
        existing_data: dict = {}
        if common_config_path.exists():
            existing_data = json.loads(common_config_path.read_text())
        existing_data["dns_multitenant"] = 1
        common_config_path.write_text(json.dumps(existing_data, indent=2))

    def _setup_supervisor(self) -> None:
        from bench_cli.managers.supervisor_process_manager import SupervisorProcessManager

        manager = SupervisorProcessManager(self.bench)
        manager.generate_config()
        manager.start()

    def _setup_nginx(self) -> None:
        from bench_cli.commands.setup.nginx import SetupNginxCommand

        SetupNginxCommand(self.bench).run()

    def _setup_letsencrypt_if_needed(self) -> None:
        has_ssl_sites = any(site.ssl for site in self.bench.config.sites)
        if not has_ssl_sites:
            return
        from bench_cli.commands.setup.letsencrypt import SetupLetsEncryptCommand

        SetupLetsEncryptCommand(self.bench).run()

    def _print_summary(self) -> None:
        from bench_cli.managers.nginx_manager import NginxManager

        nginx_manager = NginxManager(self.bench)
        print("\nProduction setup complete.")
        print("Sites:")
        for site in self.bench.config.sites:
            if site.ssl and nginx_manager.cert_exists(site):
                print(f"  https://{site.name}")
            else:
                http_port = self.bench.config.nginx.http_port
                port_suffix = "" if http_port == 80 else f":{http_port}"
                print(f"  http://{site.name}{port_suffix}")
