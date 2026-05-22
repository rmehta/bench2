from pathlib import Path

import pytest
import yaml

from bench_cli.config.bench_config import BenchConfig
from bench_cli.exceptions import ConfigError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_from_string(yaml_string: str) -> BenchConfig:
    data = yaml.safe_load(yaml_string)
    config = BenchConfig._from_dict(data)
    config.validate()
    return config


MINIMAL_VALID_YAML = """\
bench:
  name: test-bench
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
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""


def test_load_minimal_config() -> None:
    config = BenchConfig.from_file(FIXTURES_DIR / "minimal.yml")

    assert config.name == "test-bench"
    assert config.python_version == "3.14"
    assert config.process_manager == "honcho"

    assert len(config.apps) == 1
    assert config.apps[0].name == "frappe"
    assert config.apps[0].repo == "https://github.com/frappe/frappe"
    assert config.apps[0].branch == "version-16"

    assert len(config.sites) == 1
    assert config.sites[0].name == "site1.localhost"
    assert config.sites[0].apps == ["frappe"]

    assert config.mariadb.root_password == "root"
    assert config.mariadb.host == "localhost"
    assert config.mariadb.port == 3306

    assert config.redis.cache_port == 13000
    assert config.redis.queue_port == 11000
    assert config.redis.socketio_port == 12000


def test_framework_app_is_first() -> None:
    config = BenchConfig.from_file(FIXTURES_DIR / "minimal.yml")
    assert config.framework_app.name == "frappe"


def test_all_domains_includes_site_name() -> None:
    config = BenchConfig.from_file(FIXTURES_DIR / "minimal.yml")
    site = config.sites[0]
    assert "site1.localhost" in site.all_domains
    assert site.all_domains[0] == site.name


def test_all_domains_includes_extra_domains() -> None:
    yaml_string = MINIMAL_VALID_YAML + """\
# override the site to add domains
"""
    data = yaml.safe_load(MINIMAL_VALID_YAML)
    data["sites"][0]["domains"] = ["alias.localhost"]
    config = BenchConfig._from_dict(data)
    config.validate()
    assert config.sites[0].all_domains == ["site1.localhost", "alias.localhost"]


def test_app_by_name_found() -> None:
    config = BenchConfig.from_file(FIXTURES_DIR / "minimal.yml")
    app = config.app_by_name("frappe")
    assert app.name == "frappe"


def test_app_by_name_not_found() -> None:
    config = BenchConfig.from_file(FIXTURES_DIR / "minimal.yml")
    with pytest.raises(KeyError):
        config.app_by_name("nonexistent")


# ── Validation rule tests ─────────────────────────────────────────────────────


def test_rule_1_required_fields_bench_name_missing() -> None:
    yaml_string = """\
bench:
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
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "bench.name" in str(exc_info.value)


def test_rule_1_required_fields_no_apps() -> None:
    yaml_string = """\
bench:
  name: test-bench
  python: "3.14"
  process_manager: honcho

apps: []

sites:
  - name: site1.localhost
    apps:
      - frappe

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "app" in str(exc_info.value).lower()


def test_rule_1_required_fields_no_sites() -> None:
    yaml_string = """\
bench:
  name: test-bench
  python: "3.14"

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16

sites: []

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "site" in str(exc_info.value).lower()


def test_rule_2_bench_name_invalid() -> None:
    yaml_string = MINIMAL_VALID_YAML.replace("name: test-bench", "name: 123-invalid")
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "bench.name" in str(exc_info.value)


def test_rule_3_invalid_process_manager() -> None:
    yaml_string = MINIMAL_VALID_YAML.replace("process_manager: honcho", "process_manager: docker")
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "bench.process_manager" in str(exc_info.value)


def test_rule_4_duplicate_app_names() -> None:
    yaml_string = """\
bench:
  name: test-bench
  python: "3.14"
  process_manager: honcho

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16

sites:
  - name: site1.localhost
    apps:
      - frappe

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "apps[].name" in str(exc_info.value)


def test_rule_5_duplicate_site_names() -> None:
    yaml_string = """\
bench:
  name: test-bench
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
  - name: site1.localhost
    apps:
      - frappe

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "sites[].name" in str(exc_info.value)


def test_rule_6_site_app_references_unknown_app() -> None:
    yaml_string = """\
bench:
  name: test-bench
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
      - erpnext

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "erpnext" in str(exc_info.value)


def test_rule_7_site_apps_must_start_with_framework() -> None:
    yaml_string = """\
bench:
  name: test-bench
  python: "3.14"
  process_manager: honcho

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16
  - name: erpnext
    repo: https://github.com/frappe/erpnext
    branch: version-16

sites:
  - name: site1.localhost
    apps:
      - erpnext
      - frappe

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "framework app" in str(exc_info.value)


def test_rule_8_redis_ports_out_of_range() -> None:
    yaml_string = MINIMAL_VALID_YAML.replace("cache_port: 13000", "cache_port: 500")
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "redis.cache_port" in str(exc_info.value)


def test_rule_8_redis_ports_not_distinct() -> None:
    yaml_string = MINIMAL_VALID_YAML.replace("queue_port: 11000", "queue_port: 13000")
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "distinct" in str(exc_info.value)


def test_rule_9_worker_counts_must_be_positive() -> None:
    yaml_string = MINIMAL_VALID_YAML + """\
workers:
  default: 0
  short: 1
  long: 1
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "workers.default_count" in str(exc_info.value)


def test_rule_10_ssl_requires_nginx_enabled_and_email() -> None:
    yaml_string = """\
bench:
  name: test-bench
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
    ssl: true

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "nginx.enabled" in str(exc_info.value) or "letsencrypt.email" in str(exc_info.value)


def test_rule_11_invalid_letsencrypt_email() -> None:
    yaml_string = MINIMAL_VALID_YAML + """\
letsencrypt:
  email: not-an-email
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "letsencrypt.email" in str(exc_info.value)


def test_rule_12_invalid_domain_with_space() -> None:
    yaml_string = """\
bench:
  name: test-bench
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
    domains:
      - "invalid domain.com"

mariadb:
  root_password: "root"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "domain" in str(exc_info.value).lower()


def test_rule_13_nginx_ports_must_be_distinct() -> None:
    yaml_string = MINIMAL_VALID_YAML + """\
nginx:
  enabled: false
  http_port: 80
  https_port: 80
"""
    with pytest.raises(ConfigError) as exc_info:
        load_from_string(yaml_string)
    assert "nginx.http_port" in str(exc_info.value) or "nginx.https_port" in str(exc_info.value)


# ── Dependency version tests ──────────────────────────────────────────────────


def test_mariadb_version_accepted() -> None:
    yaml_string = MINIMAL_VALID_YAML.replace(
        "mariadb:\n  root_password: \"root\"",
        "mariadb:\n  root_password: \"root\"\n  version: \"10.6\"",
    )
    config = load_from_string(yaml_string)
    assert config.mariadb.version == "10.6"


def test_redis_version_accepted() -> None:
    data = yaml.safe_load(MINIMAL_VALID_YAML)
    data["redis"]["version"] = "7"
    config = BenchConfig._from_dict(data)
    config.validate()
    assert config.redis.version == "7"


def test_mariadb_version_defaults_to_none() -> None:
    config = BenchConfig.from_file(FIXTURES_DIR / "minimal.yml")
    assert config.mariadb.version is None


def test_redis_version_defaults_to_none() -> None:
    config = BenchConfig.from_file(FIXTURES_DIR / "minimal.yml")
    assert config.redis.version is None


def test_invalid_mariadb_version() -> None:
    data = yaml.safe_load(MINIMAL_VALID_YAML)
    data["mariadb"]["version"] = "invalid"
    config = BenchConfig._from_dict(data)
    with pytest.raises(ConfigError) as exc_info:
        config.validate()
    assert "mariadb.version" in str(exc_info.value)


def test_invalid_redis_version() -> None:
    data = yaml.safe_load(MINIMAL_VALID_YAML)
    data["redis"]["version"] = "not-a-version"
    config = BenchConfig._from_dict(data)
    with pytest.raises(ConfigError) as exc_info:
        config.validate()
    assert "redis.version" in str(exc_info.value)
