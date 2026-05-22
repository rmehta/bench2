from dataclasses import dataclass


@dataclass
class WorkerConfig:
    default_count: int = 2
    short_count: int = 1
    long_count: int = 1
