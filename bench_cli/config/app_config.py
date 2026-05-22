from dataclasses import dataclass


@dataclass
class AppConfig:
    name: str
    repo: str
    branch: str
