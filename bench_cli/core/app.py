from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bench_cli.config.app_config import AppConfig
from bench_cli.utils import run_command

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench


class App:
    def __init__(self, config: AppConfig, bench: "Bench") -> None:
        self.config = config
        self.bench = bench

    @property
    def path(self) -> Path:
        return self.bench.apps_path / self.config.name

    @property
    def is_cloned(self) -> bool:
        return self.path.exists() and (self.path / ".git").exists()

    def clone(self) -> None:
        run_command([
            "git", "clone",
            self.config.repo,
            "--branch", self.config.branch,
            "--depth", "1",
            str(self.path),
        ], stream_output=True)

    def update(self) -> None:
        run_command(["git", "-C", str(self.path), "fetch", "origin"])
        run_command([
            "git", "-C", str(self.path),
            "merge", "--ff-only",
            f"origin/{self.config.branch}",
        ])

    def build_assets(self) -> None:
        if not (self.path / "package.json").exists():
            return
        run_command(["yarn", "--cwd", str(self.path), "build"])
