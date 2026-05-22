from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from bench_cli.platform import get_package_manager, is_linux
from bench_cli.utils import run_command

if TYPE_CHECKING:
    from bench_cli.config.site_config import SiteConfig
    from bench_cli.core.bench import Bench


class NginxManager:
    def __init__(self, bench: "Bench") -> None:
        self.bench = bench

    def is_installed(self) -> bool:
        return shutil.which("nginx") is not None

    def install(self) -> None:
        if not self.is_installed():
            get_package_manager().install("nginx")

    def generate_config(self, ssl_ready: bool = False) -> None:
        nginx_dir = self.bench.config_path / "nginx"
        nginx_dir.mkdir(parents=True, exist_ok=True)
        for site in self.bench.config.sites:
            site_ssl_ready = ssl_ready and self.cert_exists(site)
            conf_text = self._generate_site_config(site, site_ssl_ready)
            conf_path = nginx_dir / f"{site.name}.conf"
            conf_path.write_text(conf_text)
        self._write_include_conf(nginx_dir)

    def _write_include_conf(self, nginx_dir: Path) -> None:
        include_path = nginx_dir / "include.conf"
        include_path.write_text(f"include {nginx_dir}/*.conf;\n")

    def _generate_site_config(self, site: "SiteConfig", ssl_ready: bool) -> str:
        bench_name = self.bench.config.name
        nginx_config = self.bench.config.nginx
        redis_config = self.bench.config.redis
        bench_root = self.bench.path

        upstream_block = self._render_upstream_block(bench_name)

        if not site.ssl:
            return upstream_block + self._render_http_only_block(
                site, bench_name, nginx_config, redis_config, bench_root
            )

        if not ssl_ready:
            return upstream_block + self._render_http_only_block(
                site, bench_name, nginx_config, redis_config, bench_root
            )

        return (
            upstream_block
            + self._render_http_redirect_block(site, nginx_config)
            + self._render_https_block(site, bench_name, nginx_config, redis_config, bench_root)
        )

    def _render_upstream_block(self, bench_name: str) -> str:
        return (
            f"upstream bench-{bench_name} {{\n"
            f"    server 127.0.0.1:8000;\n"
            f"    keepalive 32;\n"
            f"}}\n\n"
        )

    def _render_http_only_block(
        self,
        site: "SiteConfig",
        bench_name: str,
        nginx_config: object,
        redis_config: object,
        bench_root: Path,
    ) -> str:
        server_name = " ".join(site.all_domains)
        max_body = nginx_config.client_max_body_size
        http_port = nginx_config.http_port
        socketio_port = redis_config.socketio_port

        return (
            f"server {{\n"
            f"    listen {http_port};\n"
            f"    server_name {server_name};\n\n"
            f"    root {bench_root}/sites;\n"
            f"    client_max_body_size {max_body};\n\n"
            + self._render_assets_location()
            + self._render_files_location(site)
            + self._render_socketio_location(socketio_port)
            + self._render_proxy_location(bench_name)
            + f"}}\n"
        )

    def _render_http_redirect_block(self, site: "SiteConfig", nginx_config: object) -> str:
        server_name = " ".join(site.all_domains)
        http_port = nginx_config.http_port
        webroot = self.bench.config.letsencrypt.webroot_path

        return (
            f"server {{\n"
            f"    listen {http_port};\n"
            f"    server_name {server_name};\n\n"
            f"    location /.well-known/acme-challenge/ {{\n"
            f"        root {webroot};\n"
            f"        try_files $uri =404;\n"
            f"    }}\n\n"
            f"    location / {{\n"
            f"        return 301 https://$host$request_uri;\n"
            f"    }}\n"
            f"}}\n\n"
        )

    def _render_https_block(
        self,
        site: "SiteConfig",
        bench_name: str,
        nginx_config: object,
        redis_config: object,
        bench_root: Path,
    ) -> str:
        server_name = " ".join(site.all_domains)
        https_port = nginx_config.https_port
        max_body = nginx_config.client_max_body_size
        socketio_port = redis_config.socketio_port
        cert = self.cert_path(site)
        key = Path("/etc/letsencrypt/live") / site.name / "privkey.pem"

        ssl_directives = (
            f"    ssl_certificate     {cert};\n"
            f"    ssl_certificate_key {key};\n"
            f"    ssl_protocols       TLSv1.2 TLSv1.3;\n"
            f"    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:"
            f"ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;\n"
            f"    ssl_prefer_server_ciphers off;\n"
            f"    ssl_session_cache   shared:SSL:10m;\n"
            f"    ssl_session_timeout 1d;\n\n"
        )

        return (
            f"server {{\n"
            f"    listen {https_port} ssl http2;\n"
            f"    server_name {server_name};\n\n"
            + ssl_directives
            + f"    root {bench_root}/sites;\n"
            f"    client_max_body_size {max_body};\n\n"
            + self._render_assets_location()
            + self._render_files_location(site)
            + self._render_socketio_location(socketio_port)
            + self._render_proxy_location(bench_name)
            + f"}}\n"
        )

    def _render_assets_location(self) -> str:
        return (
            f"    location /assets {{\n"
            f"        try_files $uri =404;\n"
            f"        expires 1y;\n"
            f'        add_header Cache-Control "public, immutable";\n'
            f"    }}\n\n"
        )

    def _render_files_location(self, site: "SiteConfig") -> str:
        return (
            f"    location ~ ^/files/.*\\.(jpg|jpeg|png|gif|svg|webp|pdf|docx?|xlsx?)$ {{\n"
            f"        root {self.bench.path}/sites/{site.name}/public;\n"
            f"        try_files $uri =404;\n"
            f"    }}\n\n"
        )

    def _render_socketio_location(self, socketio_port: int) -> str:
        return (
            f"    location /socket.io {{\n"
            f"        proxy_pass         http://127.0.0.1:{socketio_port};\n"
            f"        proxy_http_version 1.1;\n"
            f"        proxy_set_header   Upgrade $http_upgrade;\n"
            f'        proxy_set_header   Connection "upgrade";\n'
            f"        proxy_set_header   Host $host;\n"
            f"    }}\n\n"
        )

    def _render_proxy_location(self, bench_name: str) -> str:
        return (
            f"    location / {{\n"
            f"        proxy_pass         http://bench-{bench_name};\n"
            f"        proxy_read_timeout 120;\n"
            f"        proxy_redirect     off;\n"
            f"        proxy_set_header   Host               $host;\n"
            f"        proxy_set_header   X-Real-IP          $remote_addr;\n"
            f"        proxy_set_header   X-Forwarded-For    $proxy_add_x_forwarded_for;\n"
            f"        proxy_set_header   X-Forwarded-Proto  $scheme;\n"
            f"        proxy_set_header   X-Frappe-Site-Name $host;\n"
            f"    }}\n"
        )

    def install_config(self) -> None:
        nginx_dir = self.bench.config.nginx.config_dir
        symlink_path = nginx_dir / f"{self.bench.config.name}.conf"
        source_path = self.bench.config_path / "nginx" / "include.conf"

        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()

        try:
            os.symlink(source_path, symlink_path)
        except PermissionError:
            print(
                f"Permission denied creating symlink at {symlink_path}.\n"
                f"Run the following command manually:\n"
                f"  sudo ln -sf {source_path} {symlink_path}\n"
                f"Then reload nginx:\n"
                f"  sudo systemctl reload nginx"
            )

    def reload(self) -> None:
        run_command(["nginx", "-t"])
        if is_linux():
            run_command(["systemctl", "reload", "nginx"])
        else:
            run_command(["nginx", "-s", "reload"])

    def cert_path(self, site: "SiteConfig") -> Path:
        return Path("/etc/letsencrypt/live") / site.name / "fullchain.pem"

    def cert_exists(self, site: "SiteConfig") -> bool:
        live_dir = Path("/etc/letsencrypt/live") / site.name
        return (live_dir / "fullchain.pem").exists() and (live_dir / "privkey.pem").exists()
