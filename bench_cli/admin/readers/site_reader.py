from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from bench_cli.config.bench_config import BenchConfig


@dataclass
class SiteInfo:
    name: str
    exists: bool
    db_name: str
    db_host: str
    installed_apps: list[str]
    site_config: dict


class SiteReader:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = bench_root

    def read_all(self) -> list[SiteInfo]:
        config = BenchConfig.from_file(self._bench_root / "bench.yml")
        return [self._read_site(site.name) for site in config.sites]

    def read_one(self, site_name: str) -> SiteInfo:
        return self._read_site(site_name)

    def _read_site(self, site_name: str) -> SiteInfo:
        site_config_path = self._bench_root / "sites" / site_name / "site_config.json"
        exists = site_config_path.exists()
        site_config: dict = {}

        if exists:
            try:
                site_config = json.loads(site_config_path.read_text())
            except (json.JSONDecodeError, OSError):
                site_config = {}

        db_name = site_config.get("db_name", "")
        db_host = site_config.get("db_host", "localhost")
        installed_apps = site_config.get("installed_apps", [])

        return SiteInfo(
            name=site_name,
            exists=exists,
            db_name=db_name,
            db_host=db_host,
            installed_apps=installed_apps,
            site_config=site_config,
        )
