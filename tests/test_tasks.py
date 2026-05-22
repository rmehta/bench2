"""Tests for bench_cli.tasks — TaskRunner and TaskReader."""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bench_cli.tasks.task_runner import TaskRunner, TASK_RETENTION_LIMIT
from bench_cli.tasks.task_reader import TaskReader
from bench_cli.exceptions import TaskNotFoundError, TaskNotRunningError


# ── TaskRunner._generate_task_id ────────────────────────────────────────────


def test_generate_task_id_format() -> None:
    task_id = TaskRunner._generate_task_id()
    assert re.match(r"^\d{8}-\d{6}-[a-f0-9]{6}$", task_id), f"Unexpected format: {task_id!r}"


# ── TaskRunner._build_argv ───────────────────────────────────────────────────


def test_build_argv_migrate(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    argv = runner._build_argv("migrate", {"site": "mysite.localhost"})
    bench_bin = str(tmp_path / "env" / "bin" / "bench")
    assert argv == [bench_bin, "--site", "mysite.localhost", "migrate"]
    assert Path(argv[0]).is_absolute()


def test_build_argv_clear_cache(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    argv = runner._build_argv("clear-cache", {"site": "mysite.localhost"})
    bench_bin = str(tmp_path / "env" / "bin" / "bench")
    assert argv == [bench_bin, "--site", "mysite.localhost", "clear-cache"]


def test_build_argv_install_app(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    argv = runner._build_argv("install-app", {"site": "mysite.localhost", "app": "erpnext"})
    bench_bin = str(tmp_path / "env" / "bin" / "bench")
    assert argv == [bench_bin, "--site", "mysite.localhost", "install-app", "erpnext"]


def test_build_argv_build(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    argv = runner._build_argv("build", {})
    bench_bin = str(tmp_path / "env" / "bin" / "bench")
    assert argv == [bench_bin, "build"]
    assert Path(argv[0]).is_absolute()


def test_build_argv_update(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    argv = runner._build_argv("update", {})
    bench_bin = str(tmp_path / "env" / "bin" / "bench")
    assert argv == [bench_bin, "update", "--yes"]


def test_build_argv_reload_supervisor(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    argv = runner._build_argv("reload-supervisor", {})
    supervisor_conf = str(tmp_path / "config" / "supervisor.conf")
    assert argv == ["supervisorctl", "-c", supervisor_conf, "reload"]
    assert Path(supervisor_conf).is_absolute()


def test_build_argv_unknown_command_raises(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    with pytest.raises(ValueError, match="Unknown command"):
        runner._build_argv("hack-the-system", {})


def test_build_argv_missing_site_raises(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    with pytest.raises(ValueError, match="site"):
        runner._build_argv("migrate", {})


def test_build_argv_install_app_requires_app(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)
    with pytest.raises(ValueError, match="app"):
        runner._build_argv("install-app", {"site": "mysite.localhost"})


# ── TaskReader._effective_status ────────────────────────────────────────────


def test_effective_status_dead_pid_returns_killed(tmp_path: Path) -> None:
    reader = TaskReader(tmp_path)
    with patch("os.kill", side_effect=OSError("no such process")):
        result = reader._effective_status("task-id", "running", 99999)
    assert result == "killed"


def test_effective_status_live_pid_returns_running(tmp_path: Path) -> None:
    reader = TaskReader(tmp_path)
    with patch("os.kill", return_value=None):
        result = reader._effective_status("task-id", "running", 12345)
    assert result == "running"


def test_effective_status_non_running_passthrough(tmp_path: Path) -> None:
    reader = TaskReader(tmp_path)
    for status in ("success", "failed", "killed"):
        result = reader._effective_status("task-id", status, 12345)
        assert result == status


def test_effective_status_none_pid_returns_killed(tmp_path: Path) -> None:
    reader = TaskReader(tmp_path)
    result = reader._effective_status("task-id", "running", None)
    assert result == "killed"


# ── TaskReader.read_output ───────────────────────────────────────────────────


def _make_task_dir(tasks_root: Path, task_id: str, status: str = "success") -> Path:
    """Helper: create a minimal on-disk task directory."""
    task_dir = tasks_root / task_id
    task_dir.mkdir(parents=True)
    meta = {
        "task_id": task_id,
        "command": "build",
        "args": {},
        "command_argv": ["/usr/bin/bench", "build"],
        "started_at": "2026-05-21T14:30:22+00:00",
        "finished_at": "2026-05-21T14:30:35+00:00",
        "exit_code": 0,
    }
    (task_dir / "meta.json").write_text(json.dumps(meta))
    (task_dir / "status").write_text(status)
    (task_dir / "pid").write_text("12345")
    (task_dir / "output.log").write_text("")
    return task_dir


def test_read_output_returns_last_n_lines(tmp_path: Path) -> None:
    task_id = "20260521-143022-aabbcc"
    task_dir = _make_task_dir(tmp_path / "tasks", task_id)
    lines = [f"line {i}" for i in range(1, 301)]
    (task_dir / "output.log").write_text("\n".join(lines))

    reader = TaskReader(tmp_path)
    with patch("os.kill", return_value=None):
        result = reader.read_output(task_id, lines=50)

    assert len(result) == 50
    assert result[0] == "line 251"
    assert result[-1] == "line 300"


def test_read_output_returns_all_lines_when_fewer_than_limit(tmp_path: Path) -> None:
    task_id = "20260521-143022-aabbcc"
    task_dir = _make_task_dir(tmp_path / "tasks", task_id)
    (task_dir / "output.log").write_text("alpha\nbeta\ngamma")

    reader = TaskReader(tmp_path)
    with patch("os.kill", return_value=None):
        result = reader.read_output(task_id, lines=200)

    assert result == ["alpha", "beta", "gamma"]


# ── TaskRunner task retention ────────────────────────────────────────────────


def _make_fake_popen(task_dir_holder: list) -> MagicMock:
    """Return a Popen mock that writes pid=99999 side-effectfully."""
    mock_proc = MagicMock()
    mock_proc.pid = 99999
    return mock_proc


def test_task_retention_limit(tmp_path: Path) -> None:
    runner = TaskRunner(tmp_path)

    # Pre-create TASK_RETENTION_LIMIT + 1 completed tasks directly on disk
    # so that after running one more the purge removes the oldest.
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    total_pre = TASK_RETENTION_LIMIT + 1
    completed_ids: list[str] = []
    for i in range(total_pre):
        task_id = f"20260521-{i:06d}-aabbcc"
        task_dir = tasks_dir / task_id
        task_dir.mkdir()
        meta = {
            "task_id": task_id,
            "command": "build",
            "args": {},
            "command_argv": ["/usr/bin/bench", "build"],
            "started_at": f"2026-05-21T{i // 3600:02d}:{(i % 3600) // 60:02d}:{i % 60:02d}+00:00",
            "finished_at": f"2026-05-21T{i // 3600:02d}:{(i % 3600) // 60:02d}:{i % 60:02d}+00:00",
            "exit_code": 0,
        }
        (task_dir / "meta.json").write_text(json.dumps(meta))
        (task_dir / "status").write_text("success")
        (task_dir / "pid").write_text("99998")
        (task_dir / "output.log").write_text("")
        completed_ids.append(task_id)

    oldest_id = sorted(completed_ids)[0]
    oldest_dir = tasks_dir / oldest_id
    assert oldest_dir.exists()

    mock_proc = MagicMock()
    mock_proc.pid = 99999

    with patch("bench_cli.tasks.task_runner.subprocess.Popen", return_value=mock_proc):
        runner.run("build", {})

    # The oldest completed task directory should have been removed.
    assert not oldest_dir.exists()

    # Completed tasks on disk should now equal TASK_RETENTION_LIMIT
    # (LIMIT+1 pre-existing minus 1 deleted = LIMIT; the new task is 'running').
    remaining_completed = [
        entry
        for entry in tasks_dir.iterdir()
        if entry.is_dir() and (entry / "status").exists()
        and (entry / "status").read_text().strip() != "running"
    ]
    assert len(remaining_completed) == TASK_RETENTION_LIMIT
