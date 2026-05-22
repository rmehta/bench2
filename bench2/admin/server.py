from __future__ import annotations

import argparse
import os
import signal
import threading
import time
from pathlib import Path

_last_request = time.monotonic()


def main() -> None:
    parser = argparse.ArgumentParser(description="bench2 admin server daemon")
    parser.add_argument("--bench-root", required=True)
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--timeout", type=int, default=900, help="Inactivity timeout in seconds")
    args = parser.parse_args()

    from bench2.admin.app import create_app

    app = create_app(Path(args.bench_root))

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
    app.run(host="127.0.0.1", port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
