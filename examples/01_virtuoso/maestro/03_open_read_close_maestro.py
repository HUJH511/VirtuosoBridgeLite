#!/usr/bin/env python3
"""Open a specific maestro in background, read its config, then close it.

Edit LIB and CELL below.

Usage:
    python 03_open_read_close_maestro.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import (
    open_session, close_session, read_config, read_env, read_results,
)

LIB  = "PLAYGROUND_AMP"
CELL = "TB_AMP_5T_D2S_DC_AC"


def _print(data: dict) -> None:
    for key, (skill_expr, raw) in data.items():
        print(f"[{key}] {skill_expr}")
        print(raw)


def main() -> int:
    client = VirtuosoClient.from_env()

    ses = open_session(client, LIB, CELL)
    print(f"Session: {ses}\n")

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

    close_session(client, ses)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
