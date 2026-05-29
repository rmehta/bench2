from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SnapshotEntry:
    dataset: str
    tag: str
    created_at: datetime
    used_bytes: int


@dataclass
class SnapshotStatus:
    volume_enabled: bool
    snapshots_enabled: bool
    snapshots: list[SnapshotEntry] = field(default_factory=list)


class SnapshotReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def read(self, dataset_filter: str | None = None) -> SnapshotStatus:
        from bench_cli.config.bench_config import BenchConfig
        from bench_cli.managers.volume_manager import VolumeManager

        config = BenchConfig.from_file(self._bench_root / "bench.toml").volume

        if not config.enabled:
            return SnapshotStatus(volume_enabled=False, snapshots_enabled=False)

        if dataset_filter == "mariadb":
            datasets = [config.mariadb_dataset]
        elif dataset_filter == "benches":
            datasets = [config.benches_dataset]
        else:
            datasets = [config.benches_dataset, config.mariadb_dataset]

        manager = VolumeManager(config)
        snapshots = []
        for ds in datasets:
            for snap in manager.list_snapshots(ds):
                snapshots.append(
                    SnapshotEntry(
                        dataset=snap.dataset,
                        tag=snap.snapshot_tag,
                        created_at=snap.created_at,
                        used_bytes=snap.used_bytes,
                    )
                )

        return SnapshotStatus(
            volume_enabled=True,
            snapshots_enabled=config.snapshots.enabled,
            snapshots=snapshots,
        )
