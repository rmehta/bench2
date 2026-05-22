from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template

from bench_cli.admin.views.apps import apps_bp
from bench_cli.admin.views.dashboard import dashboard_bp
from bench_cli.admin.views.database import database_bp
from bench_cli.admin.views.logs import logs_bp
from bench_cli.admin.views.processes import processes_bp
from bench_cli.admin.views.sites import sites_bp
from bench_cli.admin.views.tasks import tasks_bp
from bench_cli.exceptions import ConfigError


def create_app(bench_root: Path) -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["BENCH_ROOT"] = bench_root

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(apps_bp, url_prefix="/apps")
    app.register_blueprint(sites_bp, url_prefix="/sites")
    app.register_blueprint(processes_bp, url_prefix="/processes")
    app.register_blueprint(logs_bp, url_prefix="/logs")
    app.register_blueprint(database_bp, url_prefix="/database")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")

    app.register_error_handler(ConfigError, _handle_config_error)
    app.register_error_handler(FileNotFoundError, _handle_file_not_found)

    return app


def _handle_config_error(error: ConfigError):
    return render_template("error.html", error=str(error)), 500


def _handle_file_not_found(error: FileNotFoundError):
    return render_template("error.html", error=str(error)), 404
