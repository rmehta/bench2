from __future__ import annotations

from flask import Blueprint, current_app, render_template, request

from bench_cli.admin.readers.bench_reader import BenchReader
from bench_cli.admin.readers.database_reader import DatabaseReader

database_bp = Blueprint("database", __name__)


def _get_database_reader(bench_root) -> DatabaseReader:
    config = BenchReader(bench_root).config()
    return DatabaseReader(config.mariadb)


@database_bp.route("/binlogs")
def binlogs():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        reader = _get_database_reader(bench_root)
        binary_logs = reader.list_binary_logs()
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template("database/binlogs.html", binary_logs=binary_logs)


@database_bp.route("/binlogs/<log_name>")
def binlog_detail(log_name: str):
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        limit = int(request.args.get("limit", 200))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        limit, offset = 200, 0

    try:
        reader = _get_database_reader(bench_root)
        events = reader.read_binary_log_events(log_name, limit=limit, offset=offset)
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template(
        "database/binlog_detail.html",
        log_name=log_name,
        events=events,
        limit=limit,
        offset=offset,
    )


@database_bp.route("/slow-queries")
def slow_queries():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50
    limit = min(limit, 500)

    try:
        reader = _get_database_reader(bench_root)
        queries = reader.read_slow_queries(limit=limit)
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template("database/slow_queries.html", queries=queries, limit=limit)
