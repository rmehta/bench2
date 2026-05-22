from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bench_cli.config.app_config import AppConfig
from bench_cli.config.bench_config import BenchConfig
from bench_cli.config.mariadb_config import MariaDBConfig
from bench_cli.config.redis_config import RedisConfig
from bench_cli.config.site_config import SiteConfig
from bench_cli.config.worker_config import WorkerConfig
from bench_cli.core.app import App
from bench_cli.core.bench import Bench
from bench_cli.core.site import Site
from bench_cli.managers.honcho_process_manager import HonchoProcessManager
from bench_cli.managers.supervisor_process_manager import SupervisorProcessManager


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def make_bench(tmp_path: Path, process_manager: str = "honcho") -> Bench:
    config = BenchConfig(
        name="test-bench",
        python_version="3.14",
        process_manager=process_manager,
        apps=[
            AppConfig(name="frappe", repo="https://github.com/frappe/frappe", branch="version-16"),
        ],
        sites=[
            SiteConfig(name="site1.localhost", apps=["frappe"]),
        ],
        mariadb=MariaDBConfig(root_password="root"),
        redis=RedisConfig(cache_port=13000, queue_port=11000, socketio_port=12000),
        workers=WorkerConfig(default_count=2, short_count=1, long_count=1),
    )
    return Bench(config, tmp_path)


# ── App tests ────────────────────────────────────────────────────────────────


def test_app_is_cloned_returns_false_for_nonexistent_path(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    app_config = AppConfig(name="frappe", repo="https://example.com/frappe", branch="main")
    app = App(app_config, bench)
    assert app.is_cloned is False


def test_app_is_cloned_returns_false_when_no_git_directory(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    app_config = AppConfig(name="myapp", repo="https://example.com/myapp", branch="main")
    app = App(app_config, bench)
    app.path.mkdir(parents=True)
    assert app.is_cloned is False


def test_app_is_cloned_returns_true_when_git_directory_exists(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    app_config = AppConfig(name="myapp", repo="https://example.com/myapp", branch="main")
    app = App(app_config, bench)
    app.path.mkdir(parents=True)
    (app.path / ".git").mkdir()
    assert app.is_cloned is True


def test_app_path_is_under_apps_directory(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    app_config = AppConfig(name="frappe", repo="https://example.com", branch="main")
    app = App(app_config, bench)
    assert app.path == tmp_path / "apps" / "frappe"


# ── Site tests ───────────────────────────────────────────────────────────────


def test_site_exists_returns_false_for_nonexistent_path(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    site_config = SiteConfig(name="site1.localhost", apps=["frappe"])
    site = Site(site_config, bench)
    assert site.exists is False


def test_site_exists_returns_false_when_no_site_config_json(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    site_config = SiteConfig(name="site1.localhost", apps=["frappe"])
    site = Site(site_config, bench)
    site.path.mkdir(parents=True)
    assert site.exists is False


def test_site_exists_returns_true_when_site_config_json_present(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    site_config = SiteConfig(name="site1.localhost", apps=["frappe"])
    site = Site(site_config, bench)
    site.path.mkdir(parents=True)
    (site.path / "site_config.json").write_text("{}")
    assert site.exists is True


def test_site_path_is_under_sites_directory(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    site_config = SiteConfig(name="site1.localhost", apps=["frappe"])
    site = Site(site_config, bench)
    assert site.path == tmp_path / "sites" / "site1.localhost"


# ── Bench tests ───────────────────────────────────────────────────────────────


def test_bench_create_directories(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    bench.create_directories()
    assert (tmp_path / "apps").is_dir()
    assert (tmp_path / "sites").is_dir()
    assert (tmp_path / "sites" / "assets").is_dir()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "config").is_dir()
    assert (tmp_path / "pids").is_dir()


# ── ProcessManager tests ─────────────────────────────────────────────────────


def test_process_definitions_returns_correct_count(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    # workers: default=2, short=1, long=1 => 4 worker processes
    # plus web, socketio, redis_cache, redis_queue, redis_socketio = 5
    # total = 9
    process_manager = HonchoProcessManager(bench)
    definitions = process_manager._process_definitions()
    assert len(definitions) == 9


def test_process_definitions_worker_names_are_numbered(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    process_manager = HonchoProcessManager(bench)
    definitions = process_manager._process_definitions()
    names = [pd.name for pd in definitions]
    assert "worker_default_1" in names
    assert "worker_default_2" in names
    assert "worker_short_1" in names
    assert "worker_long_1" in names


def test_process_definitions_includes_redis_processes(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    process_manager = HonchoProcessManager(bench)
    definitions = process_manager._process_definitions()
    names = [pd.name for pd in definitions]
    assert "redis_cache" in names
    assert "redis_queue" in names
    assert "redis_socketio" in names


def test_process_definitions_order_starts_with_web(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    process_manager = HonchoProcessManager(bench)
    definitions = process_manager._process_definitions()
    assert definitions[0].name == "web"


# ── HonchoProcessManager tests ───────────────────────────────────────────────


def test_honcho_generate_config_writes_procfile(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    bench.create_directories()
    process_manager = HonchoProcessManager(bench)
    process_manager.generate_config()

    procfile = tmp_path / "config" / "Procfile"
    assert procfile.exists()
    content = procfile.read_text()
    assert "web:" in content
    assert "socketio:" in content
    assert "worker_default_1:" in content
    assert "redis_cache:" in content


def test_honcho_generate_config_procfile_format(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    bench.create_directories()
    process_manager = HonchoProcessManager(bench)
    process_manager.generate_config()

    procfile = tmp_path / "config" / "Procfile"
    content = procfile.read_text()
    for line in content.strip().splitlines():
        assert ": " in line, f"Line missing ': ' separator: {line!r}"


# ── SupervisorProcessManager tests ──────────────────────────────────────────


def test_supervisor_generate_config_writes_supervisor_conf(tmp_path: Path) -> None:
    bench = make_bench(tmp_path, process_manager="supervisor")
    bench.create_directories()
    process_manager = SupervisorProcessManager(bench)
    process_manager.generate_config()

    supervisor_conf = tmp_path / "config" / "supervisor.conf"
    assert supervisor_conf.exists()


def test_supervisor_generate_config_contains_env_bench_root_placeholder(tmp_path: Path) -> None:
    bench = make_bench(tmp_path, process_manager="supervisor")
    bench.create_directories()
    process_manager = SupervisorProcessManager(bench)
    process_manager.generate_config()

    supervisor_conf = tmp_path / "config" / "supervisor.conf"
    content = supervisor_conf.read_text()
    assert "%(ENV_BENCH_ROOT)s" in content


def test_supervisor_generate_config_contains_all_programs(tmp_path: Path) -> None:
    bench = make_bench(tmp_path, process_manager="supervisor")
    bench.create_directories()
    process_manager = SupervisorProcessManager(bench)
    process_manager.generate_config()

    supervisor_conf = tmp_path / "config" / "supervisor.conf"
    content = supervisor_conf.read_text()
    assert "[program:web]" in content
    assert "[program:worker_default_1]" in content
    assert "[program:redis_cache]" in content


def test_supervisor_socket_path(tmp_path: Path) -> None:
    bench = make_bench(tmp_path, process_manager="supervisor")
    process_manager = SupervisorProcessManager(bench)
    assert process_manager.socket_path == tmp_path / "pids" / "supervisor.sock"


def test_supervisor_conf_path(tmp_path: Path) -> None:
    bench = make_bench(tmp_path, process_manager="supervisor")
    process_manager = SupervisorProcessManager(bench)
    assert process_manager.conf_path == tmp_path / "config" / "supervisor.conf"
