import shutil
import subprocess
import sys
from pathlib import Path

from bench_cli.exceptions import CommandError


def uv_bin() -> str:
    # uv is a bench dependency; prefer the one installed alongside bench
    # over whatever might (or might not) be in PATH.
    local = Path(sys.executable).parent / "uv"
    if local.exists():
        return str(local)
    found = shutil.which("uv")
    if found:
        return found
    raise RuntimeError("uv not found. Reinstall bench: pip install frappe-cli")


def run_command(
    argv: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
    stream_output: bool = False,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=not stream_output,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode() if not stream_output and result.stderr else ""
        raise CommandError(
            f"Command {argv[0]!r} failed with exit code {result.returncode}.\n{stderr}".strip(),
            returncode=result.returncode,
        )
    return result
