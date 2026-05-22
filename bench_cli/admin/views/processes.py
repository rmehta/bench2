from __future__ import annotations

from flask import Blueprint, current_app, render_template

from bench_cli.admin.readers.process_reader import ProcessReader
from bench_cli.admin.readers.bench_reader import BenchReader

processes_bp = Blueprint("processes", __name__)


@processes_bp.route("/")
def index():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        processes = ProcessReader(bench_root).read_all()
        config = BenchReader(bench_root).config()
        process_manager = config.process_manager
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template(
        "processes.html",
        processes=processes,
        process_manager=process_manager,
    )
