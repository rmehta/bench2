from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from bench_cli.exceptions import TaskNotFoundError, TaskNotRunningError
from bench_cli.tasks.task_reader import TaskReader
from bench_cli.tasks.task_runner import TaskRunner

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/")
def index():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        task_list = TaskReader(bench_root).list_tasks()
    except Exception as error:
        return render_template("error.html", error=str(error))

    now = datetime.now(timezone.utc)
    return render_template("tasks/list.html", tasks=task_list, now=now)


@tasks_bp.route("/<task_id>")
def task_detail(task_id: str):
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        reader = TaskReader(bench_root)
        task = reader.read_task(task_id)
        output = reader.read_output(task_id)
    except TaskNotFoundError as error:
        return render_template("error.html", error=str(error)), 404
    except Exception as error:
        return render_template("error.html", error=str(error))

    now = datetime.now(timezone.utc)
    return render_template("tasks/detail.html", task=task, output=output, now=now)


@tasks_bp.route("/<task_id>/stream")
def stream_task_output(task_id: str):
    bench_root = current_app.config["BENCH_ROOT"]
    reader = TaskReader(bench_root)

    def generate():
        for line in reader.stream_output(task_id):
            if line.startswith("__DONE__:"):
                yield f"event: done\ndata: {line[9:]}\n\n"
            else:
                yield f"data: {line}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@tasks_bp.route("/run", methods=["POST"])
def run_task():
    bench_root = current_app.config["BENCH_ROOT"]
    form_data = dict(request.form)
    command = form_data.pop("command", "")
    args = form_data

    try:
        task_id = TaskRunner(bench_root).run(command, args)
    except ValueError as error:
        return str(error), 400
    except Exception as error:
        return render_template("error.html", error=str(error))

    return redirect(url_for("tasks.task_detail", task_id=task_id), code=303)


@tasks_bp.route("/<task_id>/kill", methods=["POST"])
def kill_task(task_id: str):
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        TaskRunner(bench_root).kill(task_id)
    except (TaskNotFoundError, TaskNotRunningError) as error:
        return render_template("error.html", error=str(error))
    except Exception as error:
        return render_template("error.html", error=str(error))

    return redirect(url_for("tasks.task_detail", task_id=task_id))
