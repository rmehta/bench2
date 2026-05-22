# Admin Interface Wireframes

ASCII wireframes for the four main sections of the `bench admin` web interface. All pages share a common nav bar and render in a monospace-friendly browser layout.

---

## Base layout

Every page extends this shell:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│   Logs   │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  [ page content ]

──────────────────────────────────────────────────────────────────────────
bench · reads filesystem on every request · no state stored
```

Nav items are plain links. The bench name is shown in the header. The green "running" badge is derived from `ProcessReader.read_all()` — amber if any process is stopped, red if all are down.

---

## Dashboard (`GET /`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│   Logs   │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  ┌─ Bench ───────────────────────────────────────────────────────────────┐
  │  name: my-bench          python: 3.14       manager: honcho           │
  │  apps: 2                 sites:  1                                    │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ Apps ────────────────────────────────────────────────────────────────┐
  │  Name         Branch        Commit    Dirty   Installed               │
  │  ──────────── ───────────── ───────── ─────── ───────────             │
  │  frappe       version-15    a1b2c3d   no      15.42.0                 │
  │  erpnext      version-15    f7e8d9a   yes ⚠   15.38.1                 │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ Sites ───────────────────────────────────────────────────────────────┐
  │  Name                  Exists   DB              Apps                  │
  │  ──────────────────── ──────── ─────────────── ───────────────────── │
  │  site1.localhost       ✓        site1_db        frappe, erpnext       │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ Processes ───────────────────────────────────────────────────────────┐
  │  Name              Status        PID      Uptime    Log               │
  │  ───────────────── ──────────── ──────── ───────── ──────────────── │
  │  web               ● running    12341    0:14:22   web.log           │
  │  worker.default    ● running    12342    0:14:21   worker.default.log│
  │  worker.long       ● running    12343    0:14:21   worker.long.log   │
  │  redis-cache       ● running    12344    0:14:23   redis-cache.log   │
  │  redis-queue       ● running    12345    0:14:23   redis-queue.log   │
  │  scheduler         ● running    12346    0:14:20   scheduler.log     │
  └───────────────────────────────────────────────────────────────────────┘
```

Status colour convention used throughout:
- `● running` — green
- `● stopped` — amber
- `● error` — red
- `● unknown` — grey

---

## Apps list (`GET /apps`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│ [Apps]   │  Sites   │ Processes│   Logs   │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Apps  (2)

  ┌────────────────────────────────────────────────────────────────────────┐
  │  Name     Repo                            Branch      Installed        │
  │  ──────── ─────────────────────────────── ──────────  ──────────────  │
  │  frappe   github.com/frappe/frappe         version-15  15.42.0         │
  │  erpnext  github.com/frappe/erpnext        version-15  15.38.1         │
  └────────────────────────────────────────────────────────────────────────┘

  ┌─ frappe ───────────────────────────────────────────────────────────────┐
  │  Commit   a1b2c3d  "fix: resolved issue with form submission"          │
  │  Dirty    no                                                           │
  └────────────────────────────────────────────────────────────────────────┘

  ┌─ erpnext ──────────────────────────────────────────────────────────────┐
  │  Commit   f7e8d9a  "feat: add payment ledger report"                   │
  │  Dirty    yes ⚠  (uncommitted changes present)                        │
  └────────────────────────────────────────────────────────────────────────┘
```

Each app section shows the full commit message and flags dirty working trees. The repo URL in the table is plain text (not a link — localhost admin has no outbound access assumption).

---

## Sites list (`GET /sites`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │ [Sites]  │ Processes│   Logs   │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Sites  (1)

  ┌───────────────────────────────────────────────────────────────────────┐
  │  Name                  Exists   DB Name      Installed Apps           │
  │  ───────────────────── ──────── ──────────── ────────────────────── │
  │  site1.localhost        ✓        site1_db     frappe, erpnext   [▶]  │
  └───────────────────────────────────────────────────────────────────────┘

  [▶] = link to site detail page
```

---

## Site detail (`GET /sites/<name>`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │ [Sites]  │ Processes│   Logs   │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  ← Sites / site1.localhost

  ┌─ Overview ────────────────────────────────────────────────────────────┐
  │  Name     site1.localhost                                             │
  │  DB       site1_db  @  localhost                                      │
  │  Exists   ✓                                                           │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ Installed apps ──────────────────────────────────────────────────────┐
  │  • frappe                                                             │
  │  • erpnext                                                            │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ Actions ─────────────────────────────────────────────────────────────┐
  │                                                                       │
  │  [ Run migrate ]   [ Clear cache ]                                    │
  │                                                                       │
  │  Install app on this site:                                            │
  │  App name: [__________]  [ Install ]                                  │
  │                                                                       │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ site_config.json ────────────────────────────────────────────────────┐
  │  {                                                                    │
  │    "db_name": "site1_db",                                             │
  │    "db_password": "••••••••",                                         │
  │    "db_host": "localhost",                                            │
  │    "installed_apps": ["frappe", "erpnext"],                           │
  │    "socketio_port": 9000                                              │
  │  }                                                                    │
  └───────────────────────────────────────────────────────────────────────┘
```

Action buttons submit to `POST /tasks/run`. "Run migrate" passes `command=migrate&site=site1.localhost`. Responses are 303 redirects to the task detail page. `db_password` is masked in the rendered JSON.

---

## Database tools

### Binary logs list (`GET /database/binlogs`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│   Logs   │ [Database] Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Database  /  Binary logs

  ┌────────────────────────────────────────────────────────────────────────┐
  │  Log name             Size                                             │
  │  ──────────────────── ───────────────────────────────────────────     │
  │  mysql-bin.000001     1.2 MB                                  [▶]     │
  │  mysql-bin.000002     4.7 MB                                  [▶]     │
  │  mysql-bin.000003     892 KB                                  [▶]     │
  └────────────────────────────────────────────────────────────────────────┘

  [▶] = link to binary log detail page
  File sizes formatted as human-readable (B / KB / MB).

  ──────────────────────────────────────────────────────────────────────
  Also:  [ Slow queries → ]
```

### Binary log detail (`GET /database/binlogs/<log_name>`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│   Logs   │ [Database] Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Database  /  Binary logs  /  mysql-bin.000002

  Showing events 1–200  [ ← prev ]  [ next → ]

  ┌────────────────────────────────────────────────────────────────────────┐
  │  Pos    Event type      Server ID  End pos   Info                      │
  │  ────── ─────────────── ────────── ───────── ──────────────────────── │
  │  4      Format_desc     1          123       Server ver: 10.6.14       │
  │  123    Previous_gtids  1          154       [empty]                   │
  │  154    Gtid            1          219       SET @@SESSION.GTID_NEXT.. │
  │  219    Query           1          341       BEGIN                     │
  │  341    Table_map       1          401       table_id: 92 (site1_db..)  │
  │  401    Write_rows      1          489       table_id: 92              │
  │  489    Xid             1          520       COMMIT /* xid=1023 */     │
  │  …                                                                     │
  └────────────────────────────────────────────────────────────────────────┘

  Pagination: ?offset=0&limit=200
```

### Slow queries (`GET /database/slow-queries`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│   Logs   │ [Database] Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Database  /  Slow queries  (showing last 50)   [ ?limit=100 ]

  ┌────────────────────────────────────────────────────────────────────────┐
  │  Timestamp           Q-time  Lock    Rows    User            SQL ▼     │
  │  ──────────────────  ──────  ──────  ──────  ─────────────   ──────── │
  │  2025-05-21 14:30:02  2.341s  0.001s  48291  frappe@local…           │
  │  ┌──────────────────────────────────────────────────────────────────┐ │
  │  │ SELECT `tabDocType`.`name` FROM `tabDocType` WHERE               │ │
  │  │ `tabDocType`.`issingle` = 1 ORDER BY `modified` DESC             │ │
  │  └──────────────────────────────────────────────────────────────────┘ │
  │                                                                        │
  │  2025-05-21 14:28:51  1.872s  0.000s  12048  frappe@local…           │
  │  ┌──────────────────────────────────────────────────────────────────┐ │
  │  │ SELECT * FROM `tabSales Invoice` WHERE `docstatus` = 1 AND …     │ │
  │  └──────────────────────────────────────────────────────────────────┘ │
  │  …                                                                     │
  └────────────────────────────────────────────────────────────────────────┘

  Each SQL block is inside a <details> element — collapsed by default,
  expanded on click. No JS required (native HTML behaviour).
```

---

## Processes (`GET /processes`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │[Processes]│   Logs  │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Processes

  ┌────────────────────────────────────────────────────────────────────────┐
  │  Name              Status        PID      Uptime     Log               │
  │  ───────────────── ──────────── ──────── ────────── ────────────────  │
  │  web               ● running    12341    0:14:22    web.log        [▶] │
  │  worker.default    ● running    12342    0:14:21    worker.def…    [▶] │
  │  worker.long       ● running    12343    0:14:21    worker.long…   [▶] │
  │  redis-cache       ● running    12344    0:14:23    redis-cache…   [▶] │
  │  redis-queue       ● running    12345    0:14:23    redis-queue…   [▶] │
  │  scheduler         ● stopped    —        —          scheduler…     [▶] │
  └────────────────────────────────────────────────────────────────────────┘

  Note: manage via `supervisorctl -c config/supervisor.conf`
  (shown only when process_manager = supervisor)

  [▶] = link to /logs/<name>.log
```

---

## Logs

### Log file list (`GET /logs`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│  [Logs]  │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Logs

  ┌────────────────────────────────────────────────────────────────────────┐
  │  File                   Process          Size     Last modified        │
  │  ──────────────────────  ────────────────  ───────  ──────────────     │
  │  web.log                web              412 KB   2 minutes ago  [▶]  │
  │  worker.default.log     worker.default   88 KB    4 minutes ago  [▶]  │
  │  worker.long.log        worker.long      12 KB    8 minutes ago  [▶]  │
  │  redis-cache.log        redis-cache      3 KB     14 minutes ago [▶]  │
  │  redis-queue.log        redis-queue      3 KB     14 minutes ago [▶]  │
  │  scheduler.log          scheduler        24 KB    1 minute ago   [▶]  │
  └────────────────────────────────────────────────────────────────────────┘

  [▶] = link to log viewer
```

### Log viewer (`GET /logs/<filename>`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│  [Logs]  │  Database  Tasks │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Logs  /  web.log      Lines: [200▾]   [ Live tail ↺ ]

  ┌────────────────────────────────────────────────────────────────────────┐
  │                                                                        │
  │  2025-05-21 14:30:01,234 INFO werkzeug: 127.0.0.1 - - [21/May/2025]  │
  │   "GET /api/resource/User HTTP/1.1" 200 -                             │
  │  2025-05-21 14:30:02,109 INFO werkzeug: 127.0.0.1 - - [21/May/2025]  │
  │   "POST /api/method/frappe.client.save HTTP/1.1" 200 -               │
  │  2025-05-21 14:30:04,881 WARNING frappe: …                            │
  │  …                                                                     │
  │                                                                        │
  └────────────────────────────────────────────────────────────────────────┘

  "Lines:" dropdown: 200 / 500 / 1000 / 5000  (reloads page with ?lines=N)
  "Live tail" button: navigates to ?stream=1 which switches to SSE mode.

  ── Live tail mode (?stream=1) ──────────────────────────────────────────

  Logs  /  web.log      ● streaming   [ Stop ]

  ┌────────────────────────────────────────────────────────────────────────┐
  │  … (prior lines pre-loaded) …                                          │
  │  2025-05-21 14:31:00,001 INFO werkzeug: ...                           │
  │  2025-05-21 14:31:00,444 INFO werkzeug: ...    ← new lines appended   │
  │                                                   by EventSource JS   │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## Tasks

### Task list (`GET /tasks`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│   Logs   │  Database [Tasks]│
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  Tasks

  ┌────────────────────────────────────────────────────────────────────────┐
  │  Command                        Status       Started          Duration │
  │  ──────────────────────────────  ──────────── ───────────────  ──────  │
  │  migrate — site1.localhost       ✓ success    3 minutes ago   0m 12s  │
  │  clear-cache — site1.localhost   ✓ success    8 minutes ago   0m 02s  │
  │  build                           ● running    just now        —    [✕]│
  │  update                          ✗ failed     1 hour ago      2m 04s  │
  └────────────────────────────────────────────────────────────────────────┘

  Each row links to the task detail page.
  [✕] = kill button (shown only for running tasks, submits POST /tasks/<id>/kill).
  Status badges: ✓ success (green) · ✗ failed (red) · ● running (amber) · — killed (grey)
```

### Task detail (`GET /tasks/<id>`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  bench admin          my-bench                              ⬡ running  │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Dashboard│   Apps   │  Sites   │ Processes│   Logs   │  Database [Tasks]│
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘

  ← Tasks  /  migrate — site1.localhost

  ┌─ Task ────────────────────────────────────────────────────────────────┐
  │  Command    migrate                                                   │
  │  Site       site1.localhost                                           │
  │  Status     ● running                                    [ Kill ]     │
  │  Started    2025-05-21 14:30:22  (3 minutes ago)                      │
  │  Finished   —                                                         │
  │  Exit code  —                                                         │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ Output ──────────────────────────────────────────────────────────────┐
  │                                                                        │
  │  Migrating site1.localhost…                                            │
  │  Running patches…                                                      │
  │  Patch 0001_setup_defaults.py                      ✓                  │
  │  Patch 0002_migrate_user_roles.py                  ✓                  │
  │  Rebuilding search index…                          ✓                  │
  │                                          ← lines appended by SSE JS  │
  │                                                                        │
  └────────────────────────────────────────────────────────────────────────┘

  When task completes:
  ┌─ Task ────────────────────────────────────────────────────────────────┐
  │  …                                                                    │
  │  Status     ✓ success                (badge updated in-place by JS)   │
  │  Finished   2025-05-21 14:30:35                                       │
  │  Exit code  0                                                         │
  └───────────────────────────────────────────────────────────────────────┘
```

`[ Kill ]` button is hidden once status changes to success/failed/killed (JS hides it on receipt of the `done` SSE event). No page reload needed.

---

## Design notes

- **No tables for layout.** All grid-like content uses `<table>` with semantic headers. No CSS grid or flexbox required — the page looks fine with only `font-family: monospace` and modest padding.
- **Colour via CSS classes only.** `class="status-running"`, `class="status-stopped"`, etc. One `<style>` block in `base.html`; no external CSS file needed.
- **`<details>` for collapsible content.** The slow-query SQL blocks and any long JSON blobs use `<details><summary>…</summary>…</details>` — no JS needed.
- **No JavaScript for static pages.** JS is used only on two pages: the live log viewer (`?stream=1`) and the task detail page (SSE output streaming). Both use the browser-native `EventSource` API — no libraries.
- **Breadcrumbs** (`← Sites / site1.localhost`) are plain `<a>` links, not a component.
