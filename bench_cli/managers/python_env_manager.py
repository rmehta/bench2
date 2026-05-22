from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from bench_cli.platform import is_macos
from bench_cli.utils import run_command, uv_bin

if TYPE_CHECKING:
    from bench_cli.core.app import App
    from bench_cli.core.bench import Bench


class PythonEnvManager:
    def __init__(self, bench: "Bench") -> None:
        self.bench = bench

    def ensure_python(self) -> None:
        version = self.bench.config.python_version
        run_command([uv_bin(), "python", "install", version])

    def create_venv(self) -> None:
        if self.bench.python.exists():
            return
        version = self.bench.config.python_version
        run_command([uv_bin(), "venv", str(self.bench.env_path), "--python", version])

    def generate_bench_script(self) -> None:
        python_path = self.bench.env_path / "bin" / "python"
        bench_script = self.bench.env_path / "bin" / "bench"
        bench_script.write_text(
            f"#!{python_path}\n"
            "import sys\n"
            "from frappe.utils.bench_helper import main\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(main() or 0)\n"
        )
        bench_script.chmod(0o755)

    def install_app(self, app: "App") -> None:
        run_command([
            uv_bin(), "pip", "install",
            "--python", str(self.bench.env_path / "bin" / "python"),
            "-e", str(app.path),
        ], stream_output=True)

    def install_node(self) -> None:
        if shutil.which("node"):
            if not shutil.which("yarn"):
                run_command(["npm", "install", "-g", "yarn"])
            return
        if is_macos():
            run_command(["brew", "install", "node"])
        else:
            self._install_node_linux()
        run_command(["npm", "install", "-g", "yarn"])

    def install_node_dependencies(self) -> None:
        for app_config in self.bench.config.apps:
            app_path = self.bench.apps_path / app_config.name
            if (app_path / "package.json").exists():
                run_command(["npm", "install"], cwd=app_path, stream_output=True)

    def build_assets(self) -> None:
        bench_binary = str(self.bench.env_path / "bin" / "bench")
        run_command([bench_binary, "frappe", "build", "--force"], cwd=self.bench.sites_path, stream_output=True)

    def _install_node_linux(self) -> None:
        run_command(
            ["bash", "-c", "curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -"],
            stream_output=True,
        )
        run_command(["sudo", "apt-get", "install", "-y", "nodejs"], stream_output=True)
