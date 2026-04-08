#!/usr/bin/env python3
"""Read full connectivity from a schematic.

Usage::

    python 02_read_connectivity.py MYLIB MYCELL
    python 02_read_connectivity.py              # uses the active design

Prerequisites:
  - virtuoso-bridge service running (virtuoso-bridge start)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from _timing import format_elapsed, timed_call
from virtuoso_bridge import VirtuosoClient

IL_FILE = Path(__file__).resolve().parent.parent / "assets" / "read_connectivity.il"


# ---------------------------------------------------------------------------
# Minimal SKILL list parser
# ---------------------------------------------------------------------------

def _tokenize(s: str) -> list[str]:
    """Tokenize a SKILL %L string into parens and atoms."""
    tokens: list[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t\n\r":
            i += 1
        elif c in "()":
            tokens.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            while j < n:
                if s[j] == '\\':
                    j += 2
                elif s[j] == '"':
                    break
                else:
                    j += 1
            tokens.append(s[i + 1 : j].replace('\\"', '"').replace("\\\\", "\\"))
            i = j + 1
        else:
            j = i
            while j < n and s[j] not in ' \t\n\r()"':
                j += 1
            tokens.append(s[i:j])
            i = j
    return tokens


def _parse(tokens: list[str], pos: int = 0) -> tuple[object, int]:
    if tokens[pos] == "(":
        lst: list[object] = []
        pos += 1
        while tokens[pos] != ")":
            val, pos = _parse(tokens, pos)
            lst.append(val)
        return lst, pos + 1
    return tokens[pos], pos + 1


def parse_skill_list(raw: str) -> object:
    """Parse a SKILL %L string into nested Python lists/strings."""
    raw = raw.strip().strip('"')
    if not raw or raw == "nil":
        return []
    tokens = _tokenize(raw)
    if not tokens:
        return raw
    val, _ = _parse(tokens)
    return val


def to_dict(data: list) -> dict:
    """Convert list-of-pairs to dict."""
    d = {}
    for item in data:
        val = item[1:] if len(item) > 2 else item[1]
        if val == "nil" or val is None:
            val = []
        d[item[0]] = val
    return d


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_connectivity(data: dict) -> str:
    lines: list[str] = []
    lib, cell, view = data.get("lib", "?"), data.get("cell", "?"), data.get("view", "?")
    instances = data.get("instances", [])
    nets = data.get("nets", [])
    pins = data.get("pins", [])

    lines.append(f"Schematic : {lib}/{cell}/{view}")
    lines.append(f"Instances : {len(instances)}   Nets : {len(nets)}   Pins : {len(pins)}")

    # Instances
    if instances:
        name_w = max(len(i[0]) for i in instances)
        lines.append(f"\n{'INSTANCE':<{name_w}}  LIB/CELL")
        lines.append("-" * (name_w + 30))
        for name, ilib, icell in instances:
            lines.append(f"{name:<{name_w}}  {ilib}/{icell}")

    # Nets
    if nets:
        net_w = max(len(n[0]) for n in nets)
        lines.append(f"\n{'NET':<{net_w}}  CONNECTIONS (inst.terminal)")
        lines.append("-" * (net_w + 50))
        for row in nets:
            net_name, conns = row[0], row[1:]
            lines.append(f"{net_name:<{net_w}}  {'  '.join(conns)}")

    # Pins
    if pins:
        pin_w = max(len(p[0]) for p in pins)
        lines.append(f"\n{'PIN':<{pin_w}}  DIRECTION")
        lines.append("-" * (pin_w + 20))
        for name, direction in pins:
            lines.append(f"{name:<{pin_w}}  {direction}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    client = VirtuosoClient.from_env()

    if len(sys.argv) >= 3:
        lib, cell = sys.argv[1], sys.argv[2]
    else:
        lib, cell, _ = client.get_current_design()
        if not lib:
            print("Usage: python 02_read_connectivity.py LIB CELL")
            print("       or open a schematic in Virtuoso first.")
            return 1

    load_elapsed, load_result = timed_call(lambda: client.load_il(IL_FILE))
    meta = load_result.metadata
    print(f"[load_il] {'uploaded' if meta.get('uploaded') else 'cache hit'}  [{format_elapsed(load_elapsed)}]")

    exec_elapsed, result = timed_call(
        lambda: client.execute_skill(f'ReadSchematic("{lib}" "{cell}")', timeout=30)
    )
    print(f"[execute_skill] [{format_elapsed(exec_elapsed)}]")
    print()

    raw = result.output or ""
    if raw.startswith('"ERROR') or raw.startswith("ERROR"):
        print(raw)
        return 1

    data = to_dict(parse_skill_list(raw))
    print(format_connectivity(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
