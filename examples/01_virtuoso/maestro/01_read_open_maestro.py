#!/usr/bin/env python3
"""Read the currently open maestro window. Does not open or close anything.

Usage:
    1. Open a maestro view in Virtuoso GUI
    2. Run this script
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import (
    find_open_session, read_config, read_env, read_results,
)


def _print(data: dict) -> None:
    for key, (skill_expr, raw) in data.items():
        print(f"[{key}] {skill_expr}")
        print(raw)


def main() -> int:
    client = VirtuosoClient.from_env()

    ses = find_open_session(client)
    if ses is None:
        print("No active maestro session found.")
        return 1

    print("=== Config ===")
    _print(read_config(client, ses))

    print("\n=== Environment ===")
    _print(read_env(client, ses))

    print("\n=== Results ===")
    results = read_results(client, ses)
    if results:
        _print(results)
    else:
        print("(no simulation results)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
