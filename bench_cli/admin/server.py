from __future__ import annotations

import argparse
import os
import signal
import threading
import time
from pathlib import Path

_last_request = time.monotonic()


def main() -> None:
    parser = argparse.ArgumentParser(description="bench admin server daemon")
    parser.add_argument("--bench-root", required=True)
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--timeout", type=int, default=900, help="Inactivity timeout in seconds")
    parser.add_argument("--no-timeout", action="store_true", help="Disable inactivity watchdog (used when managed by procfile)")
    args = parser.parse_args()

    from bench_cli.admin.app import create_app
    from bench_cli.config.bench_config import BenchConfig

    bench_root = Path(args.bench_root)
    app = create_app(bench_root)

    try:
        cfg = BenchConfig.from_file(bench_root / "bench.yml")
        admin_enabled = cfg.admin.enabled
    except Exception:
        admin_enabled = False

    if not args.no_timeout and not admin_enabled:
        @app.before_request
        def _touch() -> None:
            global _last_request
            _last_request = time.monotonic()

        def _watchdog() -> None:
            while True:
                time.sleep(60)
                if time.monotonic() - _last_request > args.timeout:
                    os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_watchdog, daemon=True).start()

    app.run(host="0.0.0.0", port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
