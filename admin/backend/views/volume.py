from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from ..readers.snapshot_reader import SnapshotReader
from ..readers.volume_reader import VolumeReader

volume_bp = Blueprint("volume", __name__)


def _get_config(bench_root):
    from bench_cli.config.bench_config import BenchConfig

    return BenchConfig.from_file(bench_root / "bench.toml").volume


def _get_manager(bench_root):
    from bench_cli.managers.volume_manager import VolumeManager

    return VolumeManager(_get_config(bench_root))


@volume_bp.route("/status")
def status():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        config = _get_config(bench_root)
        info = VolumeReader(bench_root).read()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not info.enabled:
        return jsonify({"enabled": False, "snapshots_enabled": False})

    return jsonify(
        {
            "enabled": True,
            "snapshots_enabled": config.snapshots.enabled,
            "pool": info.pool,
            "pool_health": info.pool_health,
            "datasets": [
                {
                    "name": d.name,
                    "used_bytes": d.used_bytes,
                    "available_bytes": d.available_bytes,
                    "quota_bytes": d.quota_bytes,
                    "reservation_bytes": d.reservation_bytes,
                }
                for d in info.datasets
            ],
        }
    )


@volume_bp.route("/snapshots")
def list_snapshots():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        status = SnapshotReader(bench_root).read(request.args.get("dataset"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not status.volume_enabled:
        return jsonify({"error": "Volume management is disabled."}), 400

    return jsonify(
        {
            "snapshots_enabled": status.snapshots_enabled,
            "snapshots": [
                {
                    "dataset": s.dataset,
                    "tag": s.tag,
                    "created_at": s.created_at.isoformat(),
                    "used_bytes": s.used_bytes,
                }
                for s in status.snapshots
            ],
        }
    )


@volume_bp.route("/snapshots", methods=["POST"])
def create_snapshot():
    bench_root = current_app.config["BENCH_ROOT"]
    config = _get_config(bench_root)
    if not config.enabled:
        return jsonify({"error": "Volume management is disabled."}), 400
    if not config.snapshots.enabled:
        return jsonify({"error": "Snapshots are disabled. Set volume.snapshots.enabled = true in bench.toml."}), 400

    body = request.get_json(silent=True) or {}
    dataset_name = body.get("dataset")
    if dataset_name == "mariadb":
        datasets = [config.mariadb_dataset]
    elif dataset_name == "benches":
        datasets = [config.benches_dataset]
    else:
        datasets = [config.benches_dataset, config.mariadb_dataset]

    tag = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        manager = _get_manager(bench_root)
        created = []
        for ds in datasets:
            manager.snapshot(ds, tag)
            created.append(f"{ds}@{tag}")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True, "tag": tag, "snapshots": created})


@volume_bp.route("/snapshots/<dataset>/<tag>", methods=["DELETE"])
def destroy_snapshot(dataset: str, tag: str):
    bench_root = current_app.config["BENCH_ROOT"]
    config = _get_config(bench_root)
    if not config.enabled:
        return jsonify({"error": "Volume management is disabled."}), 400

    if dataset == "mariadb":
        full_dataset = config.mariadb_dataset
    elif dataset == "benches":
        full_dataset = config.benches_dataset
    else:
        return jsonify({"error": f"Unknown dataset '{dataset}'. Use 'benches' or 'mariadb'."}), 400

    try:
        manager = _get_manager(bench_root)
        manager.destroy_snapshot(full_dataset, tag)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True})
