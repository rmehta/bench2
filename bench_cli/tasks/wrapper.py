"""
Entry point for a forked child process that runs a bench command.

Invoked as: python -m bench_bench_cli.tasks.wrapper <task-dir>

This module uses only the standard library — no cli imports.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    task_dir = Path(sys.argv[1])
    meta = json.loads((task_dir / "meta.json").read_text())

    with open(task_dir / "output.log", "wb") as log_file:
        result = subprocess.run(
            meta["command_argv"],
            cwd=str(task_dir.parent.parent),  # bench_root
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    meta["exit_code"] = result.returncode
    (task_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    status = "success" if result.returncode == 0 else "failed"
    (task_dir / "status").write_text(status)


if __name__ == "__main__":
    main()
