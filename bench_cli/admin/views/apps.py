from __future__ import annotations

from flask import Blueprint, current_app, render_template

from bench_cli.admin.readers.app_reader import AppReader

apps_bp = Blueprint("apps", __name__)


@apps_bp.route("/")
def index():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        apps = AppReader(bench_root).read_all()
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template("apps.html", apps=apps)
