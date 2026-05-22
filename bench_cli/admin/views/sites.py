from __future__ import annotations

import copy
import json

from flask import Blueprint, current_app, render_template

from bench_cli.admin.readers.site_reader import SiteReader

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


def _mask_password(config: dict) -> dict:
    masked = copy.deepcopy(config)
    if "db_password" in masked:
        masked["db_password"] = "••••••••"
    return masked
