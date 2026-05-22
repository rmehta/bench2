# bench — Implementation Plan

## Why This Order

The dependency graph is strict: you cannot test sites without MariaDB, cannot start processes without a Procfile, cannot stream task output without a forked child, and cannot build the admin without readers that work against real on-disk state. The phases follow that graph bottom-up, so each phase ends with something you can actually run and verify — not just code that compiles.

The order also respects risk: the two hardest pieces (subprocess management in Phase 2, SSE streaming in Phase 4) are isolated to their own phases so they do not block the less risky work on either side.

---

## Phase 0 — Project Skeleton

**Goal:** `pip install -e .` works; `bench --help` prints the command list; imports don't crash.

### Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, dependencies (`click`, `pyyaml`, `pymysql`, `honcho`, `supervisor`, `flask`), entry point `bench = "bench_cli.cli:cli"` |
| __cli/__init__.py` | Package marker, `__version__` |
| __cli/exceptions.py` | `ConfigError`, `BenchError`, `CommandError`, `TaskNotFoundError`, `TaskNotRunningError` — all subclass `BenchError` |
| __cli/platform.py` | `Platform` enum, `detect()`, `is_macos()`, `is_linux()`, `SystemPackageManager` ABC, `AptPackageManager`, `BrewPackageManager`, `get_package_manager()` factory |
| `bench_cli/cli.py` | Click group with stub commands: `new`, `init`, `run`, `build`, `update`, `admin`, and `setup` sub-group with `nginx`, `letsencrypt`, `production` |
| __cli/config/__init__.py` | Empty |
| __cli/core/__init__.py` | Empty |
| __cli/managers/__init__.py` | Empty |
| __cli/commands/__init__.py` | Empty |
| __cli/commands/setup/__init__.py` | Empty |
| __cli/tasks/__init__.py` | Empty |
| __cli/admin/__init__.py` | Empty |
| __cli/admin/readers/__init__.py` | Empty |
| __cli/admin/views/__init__.py` | Empty |

### Checkpoint
```bash
pip install -e .
bench --help          # shows all commands
bench new --help      # works
```

---

## Phase 1 — Config Layer + Validation

**Goal:** `BenchConfig.from_file()` parses and validates `bench.yml`; all 14 validation rules are enforced; errors name the offending field.

### Files

| File | Purpose |
|------|---------|
| `bench_cli/config/app_config.py` | `AppConfig` dataclass: `name`, `repo`, `branch` |
| `bench_cli/config/site_config.py` | `SiteConfig` dataclass: `name`, `db_name`, `db_password`, `apps`, `domains`, `ssl`; `all_domains` property |
| `bench_cli/config/mariadb_config.py` | `MariaDBConfig` dataclass with defaults; optional `version` field |
| `bench_cli/config/redis_config.py` | `RedisConfig` dataclass with defaults; optional `version` field |
| `bench_cli/config/worker_config.py` | `WorkerConfig` dataclass with defaults |
| `bench_cli/config/nginx_config.py` | `NginxConfig` dataclass with defaults |
| `bench_cli/config/letsencrypt_config.py` | `LetsEncryptConfig` dataclass with defaults |
| `bench_cli/config/bench_config.py` | `BenchConfig` — `from_file()` classmethod, `validate()` with all 14 rules, `app_by_name()`, `framework_app` |
| `bench_cli/commands/new.py` | `NewCommand.run()` — writes starter `bench.yml` template |
| `tests/__init__.py` | Empty |
| `tests/test_config.py` | Unit tests: happy path, each of the 14 validation rules |
| `tests/fixtures/minimal.yml` | Minimal valid `bench.yml` |
| `tests/fixtures/invalid_*.yml` | One fixture per validation rule |

### Checkpoint
```bash
python -m pytest tests/test_config.py -v
bench new    # writes bench.yml
```

---

## Phase 2 — Core Objects + Managers (System Setup)

**Goal:** `bench init` completes on a real Ubuntu machine — MariaDB and Redis installed, virtualenv created, apps cloned and pip-installed, sites created, Procfile written.

### Risk flags
- `MariaDBManager._connect()` requires live MariaDB — these tests must be integration tests run manually, not in CI.
- `Site.create()` calls the Frappe `bench` CLI, which requires the virtualenv to be fully set up first. The steps inside `InitCommand.run()` are strictly ordered and cannot be parallelised.
- `PythonEnvManager.ensure_python()` may need to add the deadsnakes PPA (Ubuntu) or run `brew install python@X` (macOS) — must be idempotent on both platforms.
- On macOS, `MariaDBManager.start()` uses `brew services start mariadb` — this requires the Homebrew services daemon to be running (`brew services list` should work). On Ubuntu it uses `systemctl`. All platform branching goes through `bench_cli.platform`.

### Files

| File | Purpose |
|------|---------|
| `bench_cli/utils.py` | `run_command(argv, cwd, env, capture)` — wraps `subprocess.run`, raises `CommandError` on failure, optionally streams output |
| `bench_cli/core/bench.py` | `Bench` — path properties, `create_directories()`, `apps()` and `sites()` accessors |
| `bench_cli/core/app.py` | `App` — `is_cloned`, `clone()`, `install()`, `update()`, `build_assets()` |
| `bench_cli/core/site.py` | `Site` — `exists`, `create()`, `install_app()`, `migrate()` |
| `bench_cli/managers/python_env_manager.py` | `PythonEnvManager` — `ensure_python()` (deadsnakes on Ubuntu, `brew install python@X` on macOS), `create_venv()`, `install_app()`, `install_node()` (NodeSource on Ubuntu, `brew install node` on macOS) |
| `bench_cli/managers/mariadb_manager.py` | `MariaDBManager` — `install()` picks `mariadb-server-<version>` (apt) or `mariadb@<version>` (brew); `start()` uses the versioned brew service name when a version is set; `is_installed()`, `is_running()`, `create_database()`, `create_user()`, `_connect()` |
| `bench_cli/managers/redis_manager.py` | `RedisManager` — `install()` picks `redis@<version>` (brew) or `redis-server` (apt, version-agnostic); `is_installed()`, `generate_configs()` |
| `bench_cli/managers/process_manager.py` | `ProcessManager` ABC, `ProcessDefinition` dataclass, `ProcessManagerFactory` |
| `bench_cli/managers/honcho_process_manager.py` | `HonchoProcessManager` — `generate_config()` writes Procfile, `start()`, `stop()`, `is_running()` |
| `bench_cli/managers/supervisor_process_manager.py` | `SupervisorProcessManager` — `generate_config()` writes supervisor.conf, `start()`/`stop()`/`is_running()`/`status()` |
| `bench_cli/commands/init.py` | `InitCommand.run()` — orchestrates all 12 steps in order |
| `bench_cli/commands/run.py` | `RunCommand.run()` — validates config, calls `pm.start()` |
| `bench_cli/commands/build.py` | `BuildCommand.run()` — iterates apps, then runs `bench build --make-copy` |
| `bench_cli/commands/update.py` | `UpdateCommand.run()` — warns if running, updates apps, reinstalls, migrates sites |

Wire up `cli.py` fully in this phase: find `bench.yml` (walk parent dirs), parse config, construct `Bench`, call the right command. Add `--verbose` and `--yes` options. Translate `BenchError` subclasses to clean exit-code-1 messages.

### Checkpoint (Ubuntu VM or macOS with Homebrew)
```bash
mkdir ~/testbench && cd ~/testbench
bench new && # edit bench.yml
bench init --verbose
bench run
bench build
bench update
```

On macOS, `bench init` should install MariaDB and Redis via Homebrew, start MariaDB via `brew services`, and proceed identically from step 3 onward. The same `bench run` / `bench build` / `bench update` commands work unchanged.

---

## Phase 3 — Task Execution System

**Goal:** `TaskRunner.run()` forks a child, writes the task directory, returns a task ID. `TaskReader` reads it back. The wrapper runs correctly when invoked as `python -m bench_cli.tasks.wrapper <task-dir>`.

### Risk flags
- **`os.fork()` + detach:** The forked child must call `os.setsid()` and redirect stdin/stdout/stderr to `/dev/null`. If it does not, the Flask response will not flush until the child exits — breaking SSE. This is the most OS-specific line in the codebase; test on Linux, not macOS.
- **`stream_output()` generator:** Open `output.log`, seek to last position, read new bytes, close — on every 0.5s poll iteration. The `__DONE__` sentinel must be the final `yield`, not the first thing after status changes, or clients miss the last buffered lines.

### Files

| File | Purpose |
|------|---------|
| __cli/tasks/models.py` | `TaskInfo` dataclass with computed `duration_seconds` |
| __cli/tasks/wrapper.py` | Forked child — stdlib-only; reads `meta.json`, runs `command_argv`, writes status and updates `meta.json` on exit |
| __cli/tasks/task_runner.py` | `TaskRunner` — `run()`, `kill()`, `_build_argv()` whitelist, `_generate_task_id()`, fork/detach, TASK_RETENTION_LIMIT purge |
| __cli/tasks/task_reader.py` | `TaskReader` — `list_tasks()`, `read_task()`, `read_output()`, `stream_output()`, `_effective_status()` |
| `tests/test_tasks.py` | Unit tests: task ID format, whitelist enforcement, unknown command raises `ValueError`, `_effective_status` dead-PID logic |

### Checkpoint
```python
from bench_cli.tasks.task_runner import TaskRunner
from bench_cli.tasks.task_reader import TaskReader
runner = TaskRunner(Path('/path/to/bench'))
task_id = runner.run('build', {})
import time; time.sleep(3)
reader = TaskReader(Path('/path/to/bench'))
info = reader.read_task(task_id)
print(info.status)           # 'success' or 'failed'
print(reader.read_output(task_id))
```

---

## Phase 4 — Flask Admin Interface

**Goal:** `bench admin` starts a Flask server; all pages render real data; the task detail page streams live output via SSE.

### Risk flag
`stream_with_context` keeps the Flask worker thread open for the lifetime of the stream. Use `threaded=True` in `app.run()`. With the Flask dev server, two simultaneous SSE tabs will block each other — document this; it is not a bug.

### Readers

| File | Purpose |
|------|---------|
| __cli/admin/readers/bench_reader.py` | `BenchReader` — `config()`, `summary()` |
| __cli/admin/readers/app_reader.py` | `AppReader` — `read_all()`, `read_one()`; reads git state via subprocess |
| __cli/admin/readers/site_reader.py` | `SiteReader` — `read_all()`, `read_one()`; reads `site_config.json` |
| __cli/admin/readers/process_reader.py` | `ProcessReader` — supervisor: parse `supervisorctl status`; honcho: check `pids/` |
| __cli/admin/readers/log_reader.py` | `LogReader` — `list_logs()`, `read_tail()`, `stream_tail()`; path-traversal guard |
| __cli/admin/readers/database_reader.py` | `DatabaseReader` — binary logs, slow query log |

### App factory

| File | Purpose |
|------|---------|
| __cli/admin/app.py` | `create_app(bench_root)` — registers all blueprints, stores `BENCH_ROOT`, sets `threaded=True` |

### Views

| File | Purpose |
|------|---------|
| __cli/admin/views/dashboard.py` | `GET /` |
| __cli/admin/views/apps.py` | `GET /apps` |
| __cli/admin/views/sites.py` | `GET /sites`, `GET /sites/<name>` — masks `db_password` in rendered JSON |
| __cli/admin/views/processes.py` | `GET /processes` |
| __cli/admin/views/logs.py` | `GET /logs`, `GET /logs/<filename>`, `GET /logs/<filename>/stream` (SSE) |
| __cli/admin/views/database.py` | `GET /database/binlogs`, `GET /database/binlogs/<log_name>`, `GET /database/slow-queries` |
| __cli/admin/views/tasks.py` | `GET/POST /tasks/run`, `GET /tasks`, `GET /tasks/<id>`, `GET /tasks/<id>/stream` (SSE), `POST /tasks/<id>/kill` |

### Templates

| File | Purpose |
|------|---------|
| __cli/admin/templates/base.html` | Nav bar, status badge, minimal inline CSS (no external CSS file) |
| __cli/admin/templates/dashboard.html` | Four tables: Bench info, Apps, Sites, Processes |
| __cli/admin/templates/apps.html` | Apps table + per-app detail blocks |
| __cli/admin/templates/sites/list.html` | Sites table |
| __cli/admin/templates/sites/detail.html` | Overview, installed apps, action forms, masked site_config.json |
| __cli/admin/templates/processes.html` | Process table with optional supervisor note |
| __cli/admin/templates/logs/list.html` | Log file table |
| __cli/admin/templates/logs/viewer.html` | `<pre>` block, lines dropdown, Live Tail button; SSE JS active only when `?stream=1` |
| __cli/admin/templates/database/binlogs.html` | Binary logs table |
| __cli/admin/templates/database/binlog_detail.html` | Events table with pagination |
| __cli/admin/templates/database/slow_queries.html` | Slow query rows with `<details>` for SQL (no JS needed) |
| __cli/admin/templates/tasks/list.html` | Tasks table with status badges and kill buttons |
| __cli/admin/templates/tasks/detail.html` | Task header, output `<pre>`, SSE JS, kill button hidden on `done` event |

### Checkpoint
```
bench admin
# Dashboard shows real apps, sites, processes
# /sites/site1.localhost → "Run migrate" → redirected to /tasks/<id>
# Output streams live; status badge updates when done
# /logs/web.log?stream=1 — lines appear as written
# /database/binlogs — lists real MariaDB binary logs
```

---

## Phase 5 — Production Setup Commands

**Goal:** `bench setup nginx`, `bench setup letsencrypt`, and `bench setup production` work on a real Ubuntu server with DNS pointed at it.

> **macOS:** Phase 5 code is written and tested on macOS (unit tests for config generation work anywhere) but end-to-end testing requires a real Linux server. `SetupProductionCommand` exits with a clear error if run on macOS.

### Risk flags
- **Nginx config correctness:** Test `generate_config()` output with `nginx -t -c /dev/stdin` before writing to disk. Broken config leaves the server down. Unit-test the string output before touching a live server.
- **Two-phase SSL:** `SetupProductionCommand.run()` must not call `nginx reload` with the SSL config before verifying certbot succeeded.
- **Certbot timeout:** Port 80 must be publicly reachable. Print a DNS + port reachability check before running certbot so the operator can diagnose failures.

### Files

| File | Purpose |
|------|---------|
| __cli/managers/nginx_manager.py` | `NginxManager` — `install()` (apt/brew), `generate_config(ssl_ready)`, `install_config()` (symlink), `reload()` (`systemctl` on Ubuntu / `nginx -s reload` on macOS), `cert_exists()` |
| __cli/managers/letsencrypt_manager.py` | `LetsEncryptManager` — `install()` (apt/brew), `ensure_webroot()`, `obtain()`, `obtain_all()`, `renew()` |
| __cli/commands/setup/nginx.py` | `SetupNginxCommand.run()` |
| __cli/commands/setup/letsencrypt.py` | `SetupLetsEncryptCommand.run()` |
| __cli/commands/setup/production.py` | `SetupProductionCommand.run()` — validate, supervisor, `common_site_config.json` (dns_multitenant), nginx, letsencrypt |
| `tests/test_nginx_config.py` | Unit tests: assert generated config contains `server_name`, `ssl_certificate` only when `ssl_ready=True`, correct proxy headers |

### Checkpoint (live Ubuntu server, DNS configured)
```bash
bench setup nginx        # nginx reloads, site serves HTTP
bench setup letsencrypt  # cert obtained, HTTPS live
bench setup production   # idempotent re-run — no errors
```

---

## Cross-Cutting Concerns

### Output convention
All user-visible output uses `click.echo()`. No bare `print()`. Progress steps use `[N/12] Step description...`. Errors go to `click.echo(..., err=True)`.

### Idempotency discipline
Every create/configure method checks state before acting:
- `is_cloned` before `clone()`
- `env/bin/python` exists before `create_venv()`
- `site_config.json` exists before `site.create()`
- `os.path.exists(symlink)` before writing nginx symlink

### `run_command` helper
```python
def run_command(
    argv: List[str],
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    stream_output: bool = False,
    capture: bool = True,
) -> subprocess.CompletedProcess
```
Raises `CommandError(stderr, returncode)` on failure. Used by every subprocess call in the codebase — the single chokepoint.

### Platform branching rule
All `if is_macos() / else` branches live in __cli/platform.py` or inside the relevant manager method. No platform checks appear in `commands/`, `core/`, or `admin/`. This keeps the commands layer platform-agnostic and makes it easy to add a third platform later.

### Test strategy
- **Unit tests** (phases 1, 3, 5): pure Python, no filesystem, no network. Mock `subprocess.run` where needed.
- **Integration tests** (phases 2, 4, 5): real Ubuntu VM with MariaDB/Redis. Mark with `@pytest.mark.integration` and skip by default in CI.

---

## File Count Summary

| Phase | Files |
|-------|-------|
| 0 — Skeleton | 14 (including `platform.py`) |
| 1 — Config | 12 |
| 2 — Core + Managers | 13 |
| 3 — Tasks | 5 |
| 4 — Admin | 21 (7 readers/views + 14 templates) |
| 5 — Production | 6 |
| **Total** | **~70 Python files + 14 HTML templates** |

---

## The Three Riskiest Pieces

1. **`os.fork()` + detach in `TaskRunner.run()`** — Child must call `os.setsid()` and close stdin/stdout/stderr (redirect to `/dev/null`). Without this the Flask response will not flush until the child exits, breaking SSE. Test on Linux, not macOS.

2. **`stream_output()` generator in `TaskReader`** — Polls `output.log` by opening, seeking, reading new bytes, closing. The `__DONE__` sentinel must be the final `yield` — not the first thing emitted after status changes — or clients miss the last buffered lines.

3. **Two-phase Nginx config generation** — `generate_config(ssl_ready=False)` must produce a config nginx accepts (no `ssl_certificate` pointing at a non-existent file). Unit-test the exact string output in `test_nginx_config.py`; the `nginx -t` call in `NginxManager.reload()` is the runtime safety net but you want failures caught before a live server is involved.
