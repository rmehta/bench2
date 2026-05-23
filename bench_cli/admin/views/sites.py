from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml
from flask import Blueprint, current_app, jsonify, render_template, request

from bench_cli.admin.readers.site_reader import SiteReader
from bench_cli.tasks.task_runner import TaskRunner

sites_bp = Blueprint("sites", __name__)


@sites_bp.route("/")
def index():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        sites = SiteReader(bench_root).read_all()
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template("sites/list.html", sites=sites)


@sites_bp.route("/<name>")
def detail(name: str):
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        site = SiteReader(bench_root).read_one(name)
    except Exception as error:
        return render_template("error.html", error=str(error))

    masked_config = _mask_password(site.site_config)
    masked_json = json.dumps(masked_config, indent=2)
    return render_template("sites/detail.html", site=site, site_config_json=masked_json)


@sites_bp.route("/create", methods=["POST"])
def create():
    bench_root = Path(current_app.config["BENCH_ROOT"])
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Site name is required."})

    bench_yml = bench_root / "bench.yml"
    try:
        cfg = yaml.safe_load(bench_yml.read_text()) or {}
    except Exception as e:
        return jsonify({"ok": False, "error": f"Could not read bench.yml: {e}"})

    existing = [s.get("name") for s in cfg.get("sites", [])]
    if name in existing:
        return jsonify({"ok": False, "error": f"'{name}' is already in bench.yml."})

    apps = cfg.get("apps", [])
    framework_app = apps[0].get("name") if apps else "frappe"

    cfg.setdefault("sites", []).append({"name": name, "apps": [framework_app]})

    try:
        bench_yml.write_text(yaml.dump(cfg, default_flow_style=False, allow_unicode=True, sort_keys=False))
    except Exception as e:
        return jsonify({"ok": False, "error": f"Could not write bench.yml: {e}"})

    try:
        task_id = TaskRunner(bench_root).run("new-site", {"name": name})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Site added to bench.yml but could not start new-site task: {e}"})

    return jsonify({"ok": True, "task_id": task_id})


def _mask_password(config: dict) -> dict:
    masked = copy.deepcopy(config)
    if "db_password" in masked:
        masked["db_password"] = "••••••••"
    return masked
