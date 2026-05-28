# Volume Management Specification

bench supports optional ZFS-based volume management for benches running on a dedicated disk. When enabled, a single ZFS pool is created on a block device, and separate datasets are carved out for bench data and MariaDB data — each with configurable quotas and reservations.

---

## Design constraints

- **Opt-in only.** ZFS volume management is disabled by default. Set `volume.enabled = true` in `bench.toml` to activate it.
- **One pool, two datasets.** A single ZFS pool on one large disk holds two datasets: one for bench directories (`<pool>/benches`) and one for MariaDB data (`<pool>/mariadb`). This keeps data locality simple and snapshotting independent per concern.
- **Quotas and reservations from bench.toml.** Space limits and guarantees are declared in `bench.toml` — no manual `zfs set` commands needed.
- **Snapshot support.** ZFS datasets can be snapshotted on demand via `bench volume snapshot`. This is a building block for backup workflows; scheduling is left to the operator (cron, etc.).
- **Linux only.** ZFS volume management targets Ubuntu/Linux servers. The `VolumeManager` exits with a clear error on macOS.
- **No pool destruction.** bench will never destroy a ZFS pool or rollback a dataset without an explicit user-confirmed command. All destructive operations require `--yes`.

---

## bench.toml additions

```toml
# ── Volume (ZFS, optional) ────────────────────────────────────────────────
[volume]
enabled = false            # set to true to enable ZFS volume management
pool = "bench-pool"        # ZFS pool name (created if it does not exist)
device = "/dev/sdb"        # block device to create the pool on
                           # ignored if the pool already exists

[volume.benches]
reservation = "10G"        # guaranteed space for bench directories
quota = "50G"              # hard cap on bench directory space

[volume.mariadb]
reservation = "5G"         # guaranteed space for MariaDB data files
quota = "20G"              # hard cap on MariaDB data space
data_dir = "/var/lib/mysql" # path MariaDB uses for its data files
                            # bench will bind-mount the dataset here

[volume.snapshots]
enabled = false            # set to true to allow `bench volume snapshot`
```

### Validation additions

9. If `volume.enabled = true`, `volume.pool` and `volume.device` must be non-empty strings.
10. `volume.benches.reservation` and `volume.mariadb.reservation` must be valid ZFS size strings (e.g. `"10G"`, `"512M"`).
11. `volume.benches.quota` must be greater than `volume.benches.reservation`; same for `volume.mariadb`.
12. `volume.mariadb.data_dir` must be an absolute path.

---

## Package layout additions

```
bench_cli/
└── bench_cli/
    ├── config/
    │   └── volume_config.py      # VolumeConfig, BenchesDatasetConfig, MariaDBDatasetConfig
    │
    └── managers/
        └── volume_manager.py     # VolumeManager
```

---

## Config dataclasses

```python
@dataclass
class BenchesDatasetConfig:
    reservation: str = "10G"
    quota: str = "50G"

@dataclass
class MariaDBDatasetConfig:
    reservation: str = "5G"
    quota: str = "20G"
    data_dir: str = "/var/lib/mysql"

@dataclass
class SnapshotConfig:
    enabled: bool = False

@dataclass
class VolumeConfig:
    enabled: bool = False
    pool: str = ""
    device: str = ""
    benches: BenchesDatasetConfig = field(default_factory=BenchesDatasetConfig)
    mariadb: MariaDBDatasetConfig = field(default_factory=MariaDBDatasetConfig)
    snapshots: SnapshotConfig = field(default_factory=SnapshotConfig)

    @property
    def benches_dataset(self) -> str:
        """Return the fully-qualified ZFS dataset name for bench directories."""
        return f"{self.pool}/benches"

    @property
    def mariadb_dataset(self) -> str:
        """Return the fully-qualified ZFS dataset name for MariaDB data."""
        return f"{self.pool}/mariadb"
```

`VolumeConfig` is added to `BenchConfig`:

```python
@dataclass
class BenchConfig:
    ...
    volume: VolumeConfig = field(default_factory=VolumeConfig)
```

---

## `VolumeManager`

All ZFS operations go through `VolumeManager`. It runs `zfs` and `zpool` as subprocesses — no Python ZFS library needed.

```python
class VolumeManager:
    def __init__(self, config: VolumeConfig): ...

    # Pool lifecycle

    def pool_exists(self) -> bool:
        """Return True if the pool is importable or already imported."""

    def create_pool(self) -> None:
        """
        Run: zpool create <pool> <device>
        Skipped if pool_exists() is True.
        Raises VolumeError on failure.
        """

    # Dataset lifecycle

    def dataset_exists(self, dataset: str) -> bool:
        """Return True if the ZFS dataset exists."""

    def create_dataset(self, dataset: str) -> None:
        """
        Run: zfs create <dataset>
        Skipped if dataset_exists() is True.
        """

    def set_quota(self, dataset: str, quota: str) -> None:
        """Run: zfs set quota=<quota> <dataset>"""

    def set_reservation(self, dataset: str, reservation: str) -> None:
        """Run: zfs set reservation=<reservation> <dataset>"""

    # Mount helpers

    def mount_point(self, dataset: str) -> Path:
        """
        Return the current mount point of the dataset by parsing
        `zfs get -H -o value mountpoint <dataset>`.
        """

    def bind_mount(self, dataset: str, target: Path) -> None:
        """
        Bind-mount the dataset's mount point onto target.
        Uses: mount --bind <src> <target>
        Adds an entry to /etc/fstab for persistence.
        Requires sudo.
        """

    # Snapshots

    def snapshot(self, dataset: str, name: str) -> None:
        """
        Run: zfs snapshot <dataset>@<name>
        Raises VolumeError if snapshots.enabled is False.
        """

    def list_snapshots(self, dataset: str) -> list[SnapshotInfo]:
        """
        Run: zfs list -t snapshot -o name,creation,used -s creation <dataset>
        Return list of SnapshotInfo sorted oldest-first.
        """

    def destroy_snapshot(self, dataset: str, name: str) -> None:
        """
        Run: zfs destroy <dataset>@<name>
        Raises VolumeError if the snapshot does not exist.
        """

    # High-level setup

    def setup(self) -> None:
        """
        Orchestrate full ZFS setup:
          1. create_pool()
          2. create_dataset(benches_dataset) + set_quota + set_reservation
          3. create_dataset(mariadb_dataset) + set_quota + set_reservation
          4. bind_mount(mariadb_dataset, data_dir)
        Safe to re-run — each step checks existence first.
        """
```

```python
@dataclass
class SnapshotInfo:
    name: str          # e.g. "bench-pool/benches@2025-05-28T14:00:00"
    dataset: str       # "bench-pool/benches"
    snapshot_tag: str  # "2025-05-28T14:00:00"
    created_at: datetime
    used_bytes: int
```

---

## Integration with `bench init`

When `volume.enabled = true`, `InitCommand` calls `VolumeManager.setup()` as step 2a, immediately after validating `bench.toml` and before creating the bench directory structure. This ensures the ZFS datasets are mounted before `Bench.create_directories()` writes into them.

Updated `bench init` steps:

```
1.  Validate bench.toml
2.  Install system packages
2a. [if volume.enabled] Set up ZFS pool and datasets (VolumeManager.setup())
3.  Create bench directory structure
4.  Create Python virtualenv
...
```

---

## CLI commands

### `bench volume setup`

Runs `VolumeManager.setup()` in isolation. Useful after editing `bench.toml` volume settings without running a full `bench init`.

```bash
bench volume setup
```

Pre-conditions: `volume.enabled = true` in `bench.toml`, process has `sudo`, running on Linux.

### `bench volume status`

Displays current pool and dataset state.

```
Pool       bench-pool            ONLINE
Dataset    bench-pool/benches    quota=50G  reservation=10G  used=3.2G
Dataset    bench-pool/mariadb    quota=20G  reservation=5G   used=1.8G
```

### `bench volume snapshot`

Creates a snapshot of one or both datasets.

```bash
bench volume snapshot                    # snapshot both datasets
bench volume snapshot --dataset benches  # snapshot bench data only
bench volume snapshot --dataset mariadb  # snapshot MariaDB data only
```

Snapshot names are generated as `YYYYMMDD-HHMMSS`. Pre-condition: `volume.snapshots.enabled = true` in `bench.toml`.

### `bench volume list-snapshots`

Lists all snapshots for a dataset.

```bash
bench volume list-snapshots
bench volume list-snapshots --dataset benches
```

Output:

```
Dataset: bench-pool/benches
  20250528-140000    created: 2025-05-28 14:00:00    used: 124M
  20250527-020000    created: 2025-05-27 02:00:00    used: 98M
```

### `bench volume destroy-snapshot`

Destroys a named snapshot. Requires `--yes` confirmation.

```bash
bench volume destroy-snapshot 20250527-020000 --dataset benches --yes
```

---

## Error handling

`VolumeManager` raises `bench_cli.exceptions.VolumeError` (a subclass of `BenchError`) for all ZFS command failures. The CLI catches this at the top level and prints the ZFS stderr output along with a suggested fix.

Common errors and messages:

| Situation | Message shown |
|-----------|--------------|
| `zfs` / `zpool` not installed | "ZFS tools not found. Install zfsutils-linux: sudo apt-get install zfsutils-linux" |
| Device not found | "Device /dev/sdb does not exist. Check volume.device in bench.toml" |
| Pool already exists on different device | "Pool bench-pool exists but is mounted from a different device. Import it manually first." |
| Quota less than reservation | "volume.benches.quota (10G) must be greater than volume.benches.reservation (10G)" |
| snapshots.enabled = false | "Snapshots are disabled. Set volume.snapshots.enabled = true in bench.toml to enable." |

---

## Security notes

- All `zpool create`, `zfs create`, and `mount --bind` calls require `sudo`. These are the only operations that need elevated privileges.
- `bench volume destroy-snapshot` always requires `--yes`. No snapshot is ever destroyed silently.
- Dataset names and snapshot tags are constructed from `bench.toml` values and generated timestamps only — no user-supplied strings are interpolated into shell commands. All ZFS calls use `subprocess` with a list argv, never `shell=True`.
