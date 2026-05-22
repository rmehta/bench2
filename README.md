# bench

A command-line tool for setting up and managing [Frappe](https://frappeframework.com) environments. Configuration lives in a single `bench.yml` file. No Docker.

## Requirements

**Ubuntu 22.04 LTS** (other Debian-based distros are best-effort)
- Python 3.10+
- `sudo` access (needed during `bench init` to install system packages via apt)

**macOS** (development only)
- Python 3.10+
- [Homebrew](https://brew.sh) (`brew` in `$PATH`)

## Installation

```bash
pip install frappe-cli
```

`bench init` will install MariaDB, Redis, Node.js, and any other system dependencies itself.

---

## Quick start

**1. Create a directory for your bench and scaffold a config:**

```bash
mkdir my-bench && cd my-bench
bench new
```

This writes a starter `bench.yml`. Open it and fill in your apps, sites, and database credentials.

**2. Run the setup:**

```bash
bench init
```

This will:
- Install MariaDB, Redis, Node.js via `apt` (or `brew` on macOS)
- Create a Python virtualenv at `env/` using `uv`
- Clone your apps into `apps/` and install each one with `uv pip install -e`
- Create your sites (database credentials are generated and managed by frappe)
- Build JavaScript and CSS assets
- Generate a `Procfile` for running all processes

**3. Start everything:**

```bash
bench start
```

All processes (web, workers, Redis) start in the foreground. Press `Ctrl-C` to stop.

**4. Stop from another terminal:**

```bash
bench stop
```

**5. Open the app:**

Visit `http://site1.localhost:8000` (or whatever site/port you configured).

---

## bench.yml

A minimal config for a single Frappe site:

```yaml
bench:
  name: my-bench
  python: "3.14"
  process_manager: honcho
  http_port: 8000
  socketio_port: 9000

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16

sites:
  - name: site1.localhost
    admin_password: "admin"
    apps:
      - frappe

mariadb:
  host: localhost
  port: 3306
  root_password: "your_root_password"
  admin_user: root
  version: "10.6"           # optional — omit to use the package manager default

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000
  version: "7"              # optional — macOS only; see docs/config.md for Linux notes

workers:
  default: 2
  short: 1
  long: 1
```

> **Note:** Database name and credentials are generated automatically by frappe's `new-site`. You don't configure them — they're written into `sites/<sitename>/site_config.json` after `bench init`.

---

## Commands

| Command | What it does |
|---------|-------------|
| `bench new` | Scaffold a starter `bench.yml` in the current directory |
| `bench init` | Install system packages, clone apps, create sites, build assets, generate process config |
| `bench start` | Start all processes (web, workers, Redis) in the foreground |
| `bench stop` | Stop a running bench (works across terminal sessions via PID file) |
| `bench build` | Rebuild JavaScript and CSS assets |
| `bench update` | Pull latest app commits, reinstall packages, migrate all sites |
| `bench start-admin` | Start the admin UI as a background daemon (default: `http://localhost:8002`) |
| `bench stop-admin` | Stop the background admin UI |
| `bench admin` | Start the admin UI in the foreground (dev use) |
| `bench setup nginx` | Generate and install nginx config |
| `bench setup letsencrypt` | Obtain SSL certificates |
| `bench setup production` | Full production setup (nginx + supervisor + SSL) |

All commands read `bench.yml` from the current directory or the nearest parent directory that contains one.

---

## Production setup

Update `bench.yml` to enable nginx, SSL, and supervisor:

```yaml
bench:
  name: prod-bench
  python: "3.14"
  process_manager: supervisor

apps:
  - name: frappe
    repo: https://github.com/frappe/frappe
    branch: version-16

sites:
  - name: mysite.example.com
    admin_password: "changeme"
    apps: [frappe]
    ssl: true

mariadb:
  root_password: "root_secret"

redis:
  cache_port: 13000
  queue_port: 11000
  socketio_port: 12000

nginx:
  enabled: true

letsencrypt:
  email: ops@example.com
```

Then run `bench init` followed by:

```bash
bench setup production
```

This installs nginx, obtains a Let's Encrypt certificate, and starts all processes under supervisor.

---

## Web admin

```bash
bench start-admin          # start on default port 8002 (background daemon)
bench stop-admin           # stop the daemon
bench start-admin --port 9000  # custom port
```

The admin starts as a background daemon and auto-stops after **15 minutes of inactivity** — so you don't accidentally leave it running. Use `bench stop-admin` to stop it immediately.

For interactive/foreground use during development:

```bash
bench admin                # foreground, Ctrl-C to stop
```

The admin interface provides:

- App git status and installed versions
- Site configuration and installed apps
- Process status (running / stopped)
- Live log tailing
- MariaDB binary log viewer
- Run common commands (migrate, clear-cache, build) with streamed output

The admin reads all state directly from the filesystem on each request — it keeps no state of its own.

---

## Directory layout

After `bench init`, your bench directory looks like this:

```
my-bench/
├── bench.yml          # your config
├── apps/              # cloned app source code
│   └── frappe/
├── sites/             # site data
│   ├── assets/        # built JS/CSS (symlinked from apps)
│   ├── apps.txt       # installed app list read by frappe
│   ├── common_site_config.json   # redis URLs, ports
│   └── site1.localhost/
│       └── site_config.json     # db credentials (set by frappe)
├── env/               # shared Python virtualenv
├── logs/              # per-process log files
├── pids/              # bench.pid, admin.pid, admin.port
└── config/            # Procfile, Redis configs, Nginx configs
```

---

## Further reading

- [docs/config.md](docs/config.md) — complete `bench.yml` field reference
- [docs/commands.md](docs/commands.md) — what each command does, step by step
- [docs/production.md](docs/production.md) — nginx, Let's Encrypt, and DNS multitenancy
- [docs/admin.md](docs/admin.md) — admin interface design
- [docs/architecture.md](docs/architecture.md) — Python package layout and class design
