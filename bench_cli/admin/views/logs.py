from __future__ import annotations

from flask import Blueprint, Response, current_app, render_template, request, stream_with_context

from bench_cli.admin.readers.log_reader import LogReader

logs_bp = Blueprint("logs", __name__)

_MAX_LINES = 5000


@logs_bp.route("/")
def index():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        log_files = LogReader(bench_root).list_logs()
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template("logs/list.html", log_files=log_files)


@logs_bp.route("/<filename>")
def viewer(filename: str):
    bench_root = current_app.config["BENCH_ROOT"]
    stream_mode = request.args.get("stream") == "1"

    try:
        lines_param = int(request.args.get("lines", 200))
    except ValueError:
        lines_param = 200
    lines_param = min(lines_param, _MAX_LINES)

    try:
        reader = LogReader(bench_root)
        lines = reader.read_tail(filename, lines_param)
    except ValueError as error:
        return render_template("error.html", error=str(error)), 400
    except Exception as error:
        return render_template("error.html", error=str(error))

    return render_template(
        "logs/viewer.html",
        filename=filename,
        lines=lines,
        lines_count=lines_param,
        stream_mode=stream_mode,
    )


@logs_bp.route("/<filename>/stream")
def stream_log(filename: str):
    bench_root = current_app.config["BENCH_ROOT"]
    reader = LogReader(bench_root)

    def generate():
        try:
            for line in reader.stream_tail(filename):
                yield f"data: {line}\n\n"
        except ValueError as error:
            yield f"data: ERROR: {error}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")
