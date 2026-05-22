from dataclasses import dataclass, field
from typing import List


@dataclass
class SiteConfig:
    name: str
    apps: List[str]
    admin_password: str = "admin"
    domains: List[str] = field(default_factory=list)
    ssl: bool = False

    @property
    def all_domains(self) -> List[str]:
        return [self.name] + self.domains
