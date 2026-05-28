from __future__ import annotations

from dataclasses import asdict

import psutil
from flask import Blueprint, current_app, jsonify

from ..readers.volume_reader import VolumeReader

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats")
def stats():
    bench_root = current_app.config["BENCH_ROOT"]
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    volume = VolumeReader(bench_root).read()
    return jsonify(
        {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": mem.percent,
            "memory_used": mem.used,
            "memory_total": mem.total,
            "disk_percent": disk.percent,
            "disk_used": disk.used,
            "disk_total": disk.total,
            "volume": asdict(volume),
        }
    )
