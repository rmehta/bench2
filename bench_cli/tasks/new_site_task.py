"""
Creates a new Frappe site.
Invoked as: python -m bench_cli.tasks.new_site_task <bench_root> <site_name>
"""
import sys
from pathlib import Path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("bench_root")
    parser.add_argument("site_name")
    args = parser.parse_args()

    bench_root = Path(args.bench_root)

    from bench_cli.config.bench_config import BenchConfig
    from bench_cli.core.bench import Bench
    from bench_cli.core.site import Site

    cfg = BenchConfig.from_file(bench_root / "bench.yml")
    bench = Bench(cfg, bench_root)

    try:
        site_cfg = next(s for s in cfg.sites if s.name == args.site_name)
    except StopIteration:
        print(f"Error: site '{args.site_name}' not found in bench.yml", file=sys.stderr)
        sys.exit(1)

    site = Site(site_cfg, bench)

    if site.exists:
        print(f"Site '{args.site_name}' already exists. Skipping creation.")
        sys.stdout.flush()
        return

    print(f"Creating site '{args.site_name}'...")
    sys.stdout.flush()
    site.create()
    print(f"\nSite '{args.site_name}' created successfully.")


if __name__ == "__main__":
    main()
