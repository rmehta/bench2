"""Tests for NginxManager config generation — no real nginx required."""
from pathlib import Path

import pytest
import yaml

from bench_cli.config.bench_config import BenchConfig
from bench_cli.core.bench import Bench
from bench_cli.managers.nginx_manager import NginxManager


_BASE_YAML = """\
bench:
  name: test-bench
  python: "3.14"
  process_manager: honcho

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16

sites:
  - name: site1.example.com
    apps:
      - frappe

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""

_SSL_YAML = """\
bench:
  name: test-bench
  python: "3.14"
  process_manager: honcho

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16

sites:
  - name: site1.example.com
    apps:
      - frappe
    ssl: true

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000

nginx:
  enabled: true
  http_port: 80
  https_port: 443

letsencrypt:
  email: admin@example.com
"""


def _make_bench(tmp_path: Path, yaml_string: str) -> Bench:
    bench_yml = tmp_path / "bench.yml"
    bench_yml.write_text(yaml_string)
    data = yaml.safe_load(yaml_string)
    config = BenchConfig._from_dict(data)
    return Bench(config, tmp_path)


def test_http_only_site_config(tmp_path: Path) -> None:
    bench = _make_bench(tmp_path, _BASE_YAML)
    manager = NginxManager(bench)

    site = bench.config.sites[0]
    config = manager._generate_site_config(site, ssl_ready=False)

    assert "server_name" in config
    assert "listen 80" in config
    assert "ssl_certificate" not in config


def test_ssl_site_not_ready_is_http_only(tmp_path: Path) -> None:
    bench = _make_bench(tmp_path, _SSL_YAML)
    manager = NginxManager(bench)

    site = bench.config.sites[0]
    config = manager._generate_site_config(site, ssl_ready=False)

    assert "listen 80" in config
    assert "ssl_certificate" not in config
    assert "listen 443" not in config


def test_ssl_site_ready_has_https_block(tmp_path: Path) -> None:
    bench = _make_bench(tmp_path, _SSL_YAML)
    manager = NginxManager(bench)

    site = bench.config.sites[0]
    config = manager._generate_site_config(site, ssl_ready=True)

    assert "listen 443 ssl http2" in config
    assert "ssl_certificate" in config
    assert "ssl_certificate_key" in config
    assert "return 301 https://$host$request_uri" in config


def test_include_conf_content(tmp_path: Path) -> None:
    bench = _make_bench(tmp_path, _BASE_YAML)
    manager = NginxManager(bench)
    manager.generate_config(ssl_ready=False)

    include_conf = tmp_path / "config" / "nginx" / "include.conf"
    assert include_conf.exists()
    content = include_conf.read_text()
    assert "include" in content
    assert "*.conf" in content
    nginx_dir = str(tmp_path / "config" / "nginx")
    assert nginx_dir in content


def test_server_name_includes_all_domains(tmp_path: Path) -> None:
    yaml_with_domains = _BASE_YAML + """\
  # patch applied via data dict instead
"""
    data = yaml.safe_load(_BASE_YAML)
    data["sites"][0]["domains"] = ["www.site1.example.com"]
    bench_yml = tmp_path / "bench.yml"
    bench_yml.write_text(yaml.dump(data))
    config = BenchConfig._from_dict(data)
    bench = Bench(config, tmp_path)

    manager = NginxManager(bench)
    site = bench.config.sites[0]
    config_text = manager._generate_site_config(site, ssl_ready=False)

    assert "site1.example.com" in config_text
    assert "www.site1.example.com" in config_text


def test_proxy_headers_present(tmp_path: Path) -> None:
    bench = _make_bench(tmp_path, _BASE_YAML)
    manager = NginxManager(bench)

    site = bench.config.sites[0]
    config = manager._generate_site_config(site, ssl_ready=False)

    assert "X-Frappe-Site-Name" in config
    assert "X-Forwarded-Proto" in config


def test_http_port_is_configurable(tmp_path: Path) -> None:
    yaml_custom_port = _BASE_YAML + """\
nginx:
  enabled: true
  http_port: 8080
  https_port: 8443
"""
    bench = _make_bench(tmp_path, yaml_custom_port)
    manager = NginxManager(bench)

    site = bench.config.sites[0]
    config = manager._generate_site_config(site, ssl_ready=False)

    assert "listen 8080;" in config
    assert "listen 80;" not in config
