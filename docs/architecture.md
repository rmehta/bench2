# Architecture Specification

---

## Package layout

```
bench_cli/
├── bench.yml                    # user's config (not part of the package)
│
├── setup.py                     # or pyproject.toml — installs the `bench` CLI entry point
│
└── bench_cli/                         # Python package
    ├── __init__.py
    ├── cli.py                   # Click entry point — wires commands to classes
    ├── platform.py              # OS detection and system package manager abstraction
    │
    ├── config/                  # Data classes that model bench.yml
    │   ├── __init__.py
    │   ├── bench_config.py      # BenchConfig — top-level config object
    │   ├── app_config.py        # AppConfig
    │   ├── site_config.py       # SiteConfig (now includes domains, ssl)
    │   ├── mariadb_config.py    # MariaDBConfig
    │   ├── redis_config.py      # RedisConfig
    │   ├── worker_config.py     # WorkerConfig
    │   ├── nginx_config.py      # NginxConfig
    │   └── letsencrypt_config.py # LetsEncryptConfig
    │
    ├── core/                    # Domain objects that own real state on disk
    │   ├── __init__.py
    │   ├── bench.py             # Bench — root object, owns path resolution
    │   ├── app.py               # App — one git repo + pip package
    │   └── site.py              # Site — one Frappe site directory
    │
    ├── managers/                # System-level concerns (install, configure)
    │   ├── __init__.py
    │   ├── mariadb_manager.py        # MariaDBManager
    │   ├── redis_manager.py          # RedisManager
    │   ├── python_env_manager.py     # PythonEnvManager
    │   ├── process_manager.py        # ProcessManager (abstract base)
    │   ├── honcho_process_manager.py # HonchoProcessManager — dev, foreground
    │   ├── supervisor_process_manager.py  # SupervisorProcessManager — production
    │   ├── nginx_manager.py          # NginxManager — config generation and reload
    │   └── letsencrypt_manager.py    # LetsEncryptManager — cert obtain and renew
    │
    ├── commands/                # One class per CLI command
    │   ├── __init__.py
    │   ├── new.py               # NewCommand     — scaffold a starter bench.yml
    │   ├── init.py              # InitCommand    — install deps, clone apps, create sites
    │   ├── run.py               # RunCommand
    │   ├── build.py             # BuildCommand
    │   ├── update.py            # UpdateCommand
    │   └── setup/
    │       ├── __init__.py
    │       ├── nginx.py         # SetupNginxCommand
    │       ├── letsencrypt.py   # SetupLetsEncryptCommand
    │       └── production.py    # SetupProductionCommand
    │
    ├── tasks/                   # Task execution and tracking (see specs/tasks.md)
    │   ├── __init__.py
    │   ├── models.py            # TaskInfo dataclass
    │   ├── task_runner.py       # TaskRunner — forks child, writes task directory
    │   ├── task_reader.py       # TaskReader — reads task directory (stateless)
    │   └── wrapper.py           # entry point for the forked child (stdlib only)
    │
    └── admin/                   # Flask admin interface (see specs/admin.md)
        ├── __init__.py
        ├── app.py               # create_app(bench_root) factory
        ├── readers/             # Stateless filesystem/DB readers
        └── views/               # Flask blueprints (tasks.py replaces commands.py)
```

---

## Bench directory layout (what gets created on disk)

```
<bench-root>/               # wherever the user ran bench init
├── bench.yml               # user's config
├── apps/                   # git-cloned app source trees
│   ├── frappe/
│   └── erpnext/
├── sites/                  # site data directories
│   ├── assets/             # built JS/CSS assets served by the web process
│   └── site1.localhost/
│       ├── site_config.json
│       ├── private/
│       └── public/
├── env/                    # shared Python virtualenv
├── logs/                   # per-process log files
│   ├── web.log
│   ├── worker.default.1.log
│   └── ...
├── config/                 # generated service config files
│   ├── redis_cache.conf
│   ├── redis_queue.conf
│   ├── redis_socketio.conf
│   ├── Procfile            # written when process_manager = honcho
│   ├── supervisor.conf     # written when process_manager = supervisor
│   └── nginx/              # written by bench setup nginx (nginx.enabled = true)
│       ├── include.conf    # single include directive — symlinked into nginx config_dir
│       ├── site1.example.com.conf
│       └── site2.example.com.conf
├── pids/                   # PID files and supervisor socket
│   └── supervisor.sock     # supervisor-only: unix socket for supervisorctl
└── tasks/                  # one sub-directory per admin-triggered task
    └── 20250521-143022-a1b2c3/
        ├── meta.json       # command, args, started_at, finished_at, exit_code
        ├── pid             # integer PID of the forked child
        ├── output.log      # combined stdout + stderr
        └── status          # running | success | failed | killed
```

---

## Config layer (`bench_cli/config/`)

Config classes are pure data holders. They are constructed by parsing `bench.yml` and expose no side effects. They are the only objects that know the shape of the YAML file.

### `BenchConfig`

```python
@dataclass
class BenchConfig:
    name: str
    python_version: str
    process_manager: str        # 'honcho' or 'supervisor'
    apps: List[AppConfig]
    sites: List[SiteConfig]
    mariadb: MariaDBConfig
    redis: RedisConfig
    workers: WorkerConfig
    nginx: NginxConfig = field(default_factory=NginxConfig)
    letsencrypt: LetsEncryptConfig = field(default_factory=LetsEncryptConfig)

    @classmethod
    def from_file(cls, path: Path) -> 'BenchConfig':
        """Load and validate bench.yml. Raises ConfigError on any violation."""

    def validate(self) -> None:
        """Run all validation rules defined in config.md. Raises ConfigError."""

    def app_by_name(self, name: str) -> AppConfig:
        """Return the AppConfig with the given name. Raises KeyError if not found."""

    @property
    def framework_app(self) -> AppConfig:
        """The first app in the list, treated as the Frappe framework."""
```

### `AppConfig`

```python
@dataclass
class AppConfig:
    name: str
    repo: str
    branch: str
```

### `SiteConfig`

```python
@dataclass
class SiteConfig:
    name: str
    db_name: str
    db_password: str
    apps: List[str]          # ordered list of app names
```

### `MariaDBConfig`

```python
@dataclass
class MariaDBConfig:
    host: str = 'localhost'
    port: int = 3306
    root_password: str = ''
    admin_user: str = 'root'
    socket_path: str = ''
    version: Optional[str] = None   # e.g. "10.6", "11.4"
```

### `RedisConfig`

```python
@dataclass
class RedisConfig:
    cache_port: int = 13000
    queue_port: int = 11000
    socketio_port: int = 12000
    version: Optional[str] = None   # e.g. "7", "7.0"
```

### `WorkerConfig`

```python
@dataclass
class WorkerConfig:
    default: int = 2
    short: int = 1
    long: int = 1
```

---

## Core layer (`bench_cli/core/`)

Core objects represent things that exist (or will exist) on disk. They receive the relevant config and the parent `Bench` object so they can resolve paths without knowing where the bench root is.

### `Bench`

The root object. All commands construct a `Bench` from a `BenchConfig` and a root path, then call methods on it.

```python
class Bench:
    def __init__(self, config: BenchConfig, path: Path): ...

    # Path helpers
    @property
    def apps_path(self) -> Path: ...      # <root>/apps/
    @property
    def sites_path(self) -> Path: ...     # <root>/sites/
    @property
    def env_path(self) -> Path: ...       # <root>/env/
    @property
    def logs_path(self) -> Path: ...      # <root>/logs/
    @property
    def config_path(self) -> Path: ...    # <root>/config/
    @property
    def pids_path(self) -> Path: ...      # <root>/pids/
    @property
    def python(self) -> Path: ...         # <root>/env/bin/python
    @property
    def pip(self) -> Path: ...            # <root>/env/bin/pip

    # Domain object accessors
    def apps(self) -> List[App]: ...      # one App per entry in config.apps
    def sites(self) -> List[Site]: ...    # one Site per entry in config.sites

    def create_directories(self) -> None:
        """Create apps/, sites/, logs/, config/, pids/ if they do not exist."""
```

### `App`

```python
class App:
    def __init__(self, config: AppConfig, bench: Bench): ...

    @property
    def path(self) -> Path: ...           # bench.apps_path / config.name

    @property
    def is_cloned(self) -> bool: ...      # True if path exists and is a git repo

    def clone(self) -> None:
        """git clone config.repo --branch config.branch into apps/."""

    def install(self) -> None:
        """pip install -e . inside the bench virtualenv."""

    def update(self) -> None:
        """git fetch + git merge origin/<branch>. Raises on merge conflicts."""

    def build_assets(self) -> None:
        """Run the app's asset build command if it defines one (e.g. yarn build)."""
```

### `Site`

```python
class Site:
    def __init__(self, config: SiteConfig, bench: Bench): ...

    @property
    def path(self) -> Path: ...           # bench.sites_path / config.name

    @property
    def exists(self) -> bool: ...         # True if path/site_config.json is present

    def create(self, mariadb: MariaDBConfig) -> None:
        """
        Run `bench new-site` via the framework app CLI.
        Creates the MariaDB database, user, and site_config.json.
        """

    def install_app(self, app_name: str) -> None:
        """Run `bench --site <name> install-app <app_name>`."""

    def migrate(self) -> None:
        """Run `bench --site <name> migrate`."""
```

---

## Managers layer (`bench_cli/managers/`)

Managers handle interactions with system services and tools. They do not know about Sites or Apps directly — they receive only what they need.

### `MariaDBManager`

```python
class MariaDBManager:
    def __init__(self, config: MariaDBConfig): ...

    def install(self) -> None:
        """
        Install MariaDB via the system package manager.
        Ubuntu: apt-get install mariadb-server[-<version>]  e.g. mariadb-server-10.6
        macOS:  brew install mariadb[@<version>]            e.g. mariadb@10.6
        When config.version is None, the package manager's default is used.
        """

    def is_installed(self) -> bool: ...

    def is_running(self) -> bool: ...

    def start(self) -> None:
        """
        Start the MariaDB service.
        Ubuntu: systemctl start mariadb  (service name is version-independent on Linux)
        macOS:  brew services start mariadb[@<version>]  — uses the versioned formula name
                so the correct service is started when a non-default version is installed.
        """

    def create_database(self, db_name: str) -> None:
        """CREATE DATABASE IF NOT EXISTS."""

    def create_user(self, username: str, password: str, db_name: str) -> None:
        """CREATE USER and GRANT ALL on db_name."""

    def _connect(self) -> 'MySQLConnection':
        """Return an authenticated root connection."""
```

### `RedisManager`

```python
class RedisManager:
    def __init__(self, config: RedisConfig, bench: Bench): ...

    def install(self) -> None:
        """
        Install Redis via the system package manager.
        Ubuntu: apt-get install redis-server  (apt has no versioned redis package names;
                use the official Redis apt repo for version pinning before running bench init)
        macOS:  brew install redis[@<version>]  e.g. redis@7
        Redis is not started as a system service; bench run launches it
        directly from the Procfile/supervisor config with a custom port.
        """

    def is_installed(self) -> bool: ...

    def generate_configs(self) -> None:
        """
        Write three minimal redis.conf files to bench.config_path:
          redis_cache.conf, redis_queue.conf, redis_socketio.conf.
        Each binds to 127.0.0.1 on its configured port.
        """
```

### `PythonEnvManager`

All apps share a single virtualenv at `env/`. This is intentional: every app listed in `bench.yml` can be installed on any site in the bench. Because Frappe loads all installed apps into the same Python process, they must all live in the same environment. Dependency conflicts between apps are resolved at the app level, not by isolating environments.

```python
class PythonEnvManager:
    def __init__(self, bench: Bench): ...

    def ensure_python(self) -> None:
        """
        Check that the configured Python version is available.
        Ubuntu: install via the deadsnakes PPA (python3-<version>-venv).
        macOS:  install via Homebrew (brew install python@<version>).
               Prints a hint to use pyenv if the version is unavailable via brew.
        """

    def create_venv(self) -> None:
        """python -m venv bench.env_path if it does not already exist."""

    def install_app(self, app: App) -> None:
        """pip install -e app.path using bench.pip."""

    def install_node(self) -> None:
        """
        Install Node.js 18 LTS if not present (required for asset builds).
        Ubuntu: download and run the NodeSource setup script, then apt-get install nodejs.
        macOS:  brew install node.
        Yarn is installed globally afterward via: npm install -g yarn.
        """
```

### `ProcessManager` (abstract base)

`ProcessManager` defines the interface. The concrete implementation is chosen at runtime based on `bench.config.process_manager`.

```python
class ProcessManager(ABC):
    def __init__(self, bench: Bench): ...

    @abstractmethod
    def generate_config(self) -> None:
        """Write the process manager's config file(s) to bench.config_path."""

    @abstractmethod
    def start(self) -> None:
        """Start all bench processes."""

    @abstractmethod
    def stop(self) -> None:
        """Stop all bench processes."""

    @abstractmethod
    def is_running(self) -> bool:
        """Return True if any managed process is currently running."""

    def _process_definitions(self) -> List[ProcessDefinition]:
        """
        Build the ordered list of processes from bench config:
          web, socketio, N×default worker, M×short worker, K×long worker,
          redis_cache, redis_queue, redis_socketio.
        Shared by both subclasses.
        """
```

`ProcessDefinition` is a small dataclass:

```python
@dataclass
class ProcessDefinition:
    name: str           # e.g. "worker_default_1"
    command: str        # full shell command string with absolute paths
    log_file: Path      # bench.logs_path / f"{name}.log"
```

#### `HonchoProcessManager`

Used when `process_manager: honcho`. Intended for development.

```python
class HonchoProcessManager(ProcessManager):

    def generate_config(self) -> None:
        """Write config/Procfile from _process_definitions()."""

    def start(self) -> None:
        """
        Invoke honcho programmatically with config/Procfile.
        Multiplexes stdout with '<name> |' prefix.
        Each process also writes to logs/<name>.log.
        Blocks until SIGINT/SIGTERM; sends SIGTERM to children, then SIGKILL after 5s.
        """

    def stop(self) -> None:
        """Send SIGTERM to the honcho process group (no-op if not running)."""

    def is_running(self) -> bool:
        """True if a honcho process started by this bench is alive."""
```

#### `SupervisorProcessManager`

Used when `process_manager: supervisor`. Intended for production.

```python
class SupervisorProcessManager(ProcessManager):

    @property
    def socket_path(self) -> Path: ...     # bench.pids_path / "supervisor.sock"
    @property
    def conf_path(self) -> Path: ...       # bench.config_path / "supervisor.conf"

    def generate_config(self) -> None:
        """
        Write config/supervisor.conf.
        The file contains a [supervisord] section, [unix_http_server],
        [supervisorctl], [rpcinterface:supervisor], and one [program:X]
        section per ProcessDefinition.
        """

    def start(self) -> None:
        """
        If supervisord is not running: supervisord -c config/supervisor.conf
        If supervisord is already running: supervisorctl -c config/supervisor.conf reload
        Exits immediately (supervisord runs as a background daemon).
        """

    def stop(self) -> None:
        """supervisorctl -c config/supervisor.conf shutdown"""

    def is_running(self) -> bool:
        """True if supervisor.sock exists and supervisord responds to a status ping."""

    def status(self) -> str:
        """supervisorctl -c config/supervisor.conf status  (returns raw output)."""
```

The generated `supervisor.conf` has this structure:

```ini
[unix_http_server]
file=%(ENV_BENCH_ROOT)s/pids/supervisor.sock
chmod=0700

[supervisord]
logfile=%(ENV_BENCH_ROOT)s/logs/supervisord.log
logfile_maxbytes=50MB
logfile_backups=10
loglevel=info
pidfile=%(ENV_BENCH_ROOT)s/pids/supervisord.pid
nodaemon=false

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix://%(ENV_BENCH_ROOT)s/pids/supervisor.sock

[program:web]
command=%(ENV_BENCH_ROOT)s/env/bin/gunicorn -b 0.0.0.0:8000 -w 1 -t 120 frappe.app:application
directory=%(ENV_BENCH_ROOT)s
autostart=true
autorestart=true
stdout_logfile=%(ENV_BENCH_ROOT)s/logs/web.log
stderr_logfile=%(ENV_BENCH_ROOT)s/logs/web.error.log

[program:worker_default_1]
command=%(ENV_BENCH_ROOT)s/env/bin/bench worker --queue default
directory=%(ENV_BENCH_ROOT)s
autostart=true
autorestart=true
stdout_logfile=%(ENV_BENCH_ROOT)s/logs/worker_default_1.log
stderr_logfile=%(ENV_BENCH_ROOT)s/logs/worker_default_1.error.log

; … one [program] block per ProcessDefinition …
```

`%(ENV_BENCH_ROOT)s` is resolved by supervisord from the environment variable `BENCH_ROOT`, which `bench run` sets before invoking supervisord. This keeps the config file portable (not hard-coded to a path).

#### `ProcessManagerFactory`

```python
class ProcessManagerFactory:
    @staticmethod
    def create(bench: Bench) -> ProcessManager:
        if bench.config.process_manager == 'supervisor':
            return SupervisorProcessManager(bench)
        return HonchoProcessManager(bench)
```

---

## Commands layer (`bench_cli/commands/`)

Each command class receives a `Bench` object and a logger. It orchestrates managers and core objects in the correct order. Commands are the only layer that produces user-visible console output.

```python
class NewCommand:
    def __init__(self, target_dir: Path): ...
    def run(self) -> None: ...          # write a starter bench.yml; no other side effects

class InitCommand:
    def __init__(self, bench: Bench): ...
    def run(self) -> None: ...          # full setup: deps, venv, apps, sites, config

class RunCommand:
    def __init__(self, bench: Bench): ...
    def run(self) -> None: ...

class BuildCommand:
    def __init__(self, bench: Bench): ...
    def run(self) -> None: ...

class UpdateCommand:
    def __init__(self, bench: Bench): ...
    def run(self) -> None: ...
```

---

## CLI entry point (`bench_cli/cli.py`)

Built with [Click](https://click.palletsprojects.com/). Responsibilities:
1. Find `bench.yml` (current directory, then parent directories up to `$HOME`).
2. Parse and validate it into a `BenchConfig`.
3. Construct a `Bench`.
4. Instantiate and call the appropriate command class.

```python
@click.group()
def cli(): ...

@cli.command()
def new(): ...          # NewCommand(Path.cwd()).run() — scaffold bench.yml, then exit

@cli.command()
def init(): ...         # InitCommand(bench).run() — full setup

@cli.command()
def run(): ...          # RunCommand(bench).run()

@cli.command()
def build(): ...        # BuildCommand(bench).run()

@cli.command()
def update(): ...       # UpdateCommand(bench).run()

@cli.command()
@click.option('--port', default=8001)
@click.option('--host', default='127.0.0.1')
def admin(port, host): ...   # create_app(bench.path).run(host, port)

@cli.group()
def setup(): ...             # sub-command group for production setup

@setup.command('nginx')
def setup_nginx(): ...           # SetupNginxCommand(bench).run()

@setup.command('letsencrypt')
def setup_letsencrypt(): ...     # SetupLetsEncryptCommand(bench).run()

@setup.command('production')
def setup_production(): ...      # SetupProductionCommand(bench).run()
```

---

## Platform detection (`bench_cli/platform.py`)

All OS-specific branching lives in one module. Every other module imports from here rather than calling `platform.system()` or `shutil.which()` inline.

```python
from enum import Enum

class Platform(Enum):
    LINUX = 'linux'
    MACOS = 'macos'

def detect() -> Platform:
    """Return Platform.MACOS on Darwin, Platform.LINUX otherwise."""

def is_macos() -> bool: ...
def is_linux() -> bool: ...
```

### `SystemPackageManager` — abstract base

```python
class SystemPackageManager(ABC):
    @abstractmethod
    def install(self, *packages: str) -> None:
        """Install one or more system packages."""

    @abstractmethod
    def is_installed(self, package: str) -> bool:
        """Return True if the package is already installed."""
```

#### `AptPackageManager`

Used on Ubuntu/Debian. Calls `sudo apt-get install -y <packages>`.

```python
class AptPackageManager(SystemPackageManager):
    def install(self, *packages: str) -> None: ...    # sudo apt-get install -y
    def is_installed(self, package: str) -> bool: ... # dpkg -l <package>
```

#### `BrewPackageManager`

Used on macOS. Requires Homebrew to be present (`brew` in `$PATH`).

```python
class BrewPackageManager(SystemPackageManager):
    def install(self, *packages: str) -> None: ...    # brew install
    def is_installed(self, package: str) -> bool: ... # brew list <package>
```

#### `get_package_manager() -> SystemPackageManager`

Factory function — returns `BrewPackageManager()` on macOS, `AptPackageManager()` on Linux. Called once per command run, not per method call.

---

## Error handling

- All config errors raise `bench_cli.exceptions.ConfigError`.
- All command errors raise `bench_cli.exceptions.BenchError`.
- The CLI catches these at the top level and prints a clean error message without a traceback (unless `--verbose` is passed).
- Subprocess failures (git, pip, mysql) raise `bench_cli.exceptions.CommandError` with the captured stderr.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `click` | CLI framework |
| `pyyaml` | Parse `bench.yml` |
| `PyMySQL` | Connect to MariaDB during `bench init` and in the admin's `DatabaseReader` |
| `honcho` | Procfile-based process runner (`HonchoProcessManager`) |
| `supervisor` | Daemon process manager (`SupervisorProcessManager`); also installs the `supervisord` and `supervisorctl` binaries |
| `flask` | Admin web interface (`bench admin`) |

All are pure Python and declared in `setup.py`. No system packages are required to install bench itself.

`bench setup nginx` and `bench setup letsencrypt` additionally install the `nginx` and `certbot` system packages if not already present (via apt on Ubuntu, via Homebrew on macOS). These are managed by their respective managers, not declared as Python dependencies.

**Production setup (`bench setup nginx`, `bench setup letsencrypt`, `bench setup production`) targets Ubuntu/Linux servers.** macOS is a development platform; run `bench run` with honcho there instead.
