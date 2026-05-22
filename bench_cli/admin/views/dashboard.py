from __future__ import annotations

from flask import Blueprint, current_app, render_template

from bench_cli.admin.readers.app_reader import AppReader
from bench_cli.admin.readers.bench_reader import BenchReader
from bench_cli.admin.readers.process_reader import ProcessReader
from bench_cli.admin.readers.site_reader import SiteReader

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        summary = BenchReader(bench_root).summary()
        apps = AppReader(bench_root).read_all()
        sites = SiteReader(bench_root).read_all()
        processes = ProcessReader(bench_root).read_all()
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template(
        "dashboard.html",
        summary=summary,
        apps=apps,
        sites=sites,
        processes=processes,
    )
