from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from bench_cli.config.bench_config import BenchConfig


@dataclass
class AppInfo:
    name: str
    repo: str
    branch: str
    is_cloned: bool
    current_commit: str
    commit_message: str
    uncommitted_changes: bool
    installed_version: str


class AppReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def read_all(self) -> list[AppInfo]:
        config = BenchConfig.from_file(self._bench_root / "bench.yml")
        return [self._read_app(app.name, app.repo, app.branch) for app in config.apps]

    def read_one(self, app_name: str) -> AppInfo:
        config = BenchConfig.from_file(self._bench_root / "bench.yml")
        app_config = config.app_by_name(app_name)
        return self._read_app(app_config.name, app_config.repo, app_config.branch)

    def _read_app(self, name: str, repo: str, branch: str) -> AppInfo:
        app_path = self._bench_root / "apps" / name
        is_cloned = (app_path / ".git").exists()

        if not is_cloned:
            return AppInfo(
                name=name,
                repo=repo,
                branch=branch,
                is_cloned=False,
                current_commit="",
                commit_message="",
                uncommitted_changes=False,
                installed_version=self._pip_version(name),
            )

        return AppInfo(
            name=name,
            repo=repo,
            branch=branch,
            is_cloned=True,
            current_commit=self._git_short_sha(app_path),
            commit_message=self._git_commit_message(app_path),
            uncommitted_changes=self._git_is_dirty(app_path),
            installed_version=self._pip_version(name),
        )

    def _git_short_sha(self, path: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git_commit_message(self, path: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git_is_dirty(self, path: Path) -> bool:
        result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip()) if result.returncode == 0 else False

    def _pip_version(self, name: str) -> str:
        python_bin = self._bench_root / "env" / "bin" / "python"
        from bench_cli.utils import uv_bin
        result = subprocess.run(
            [uv_bin(), "pip", "show", "--python", str(python_bin), name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return ""
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        return ""
