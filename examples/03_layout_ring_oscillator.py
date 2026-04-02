#!/usr/bin/env python3
"""Create a simple layout: row of inverter instances with M1 wiring.

Demonstrates layout editing: placing PCell instances, drawing rectangles,
paths, vias, and labels.

Prerequisites:
  - .env configured, bridge running
  - A library and an inverter cell exist (or change the names below)

Usage:
    python examples/03_layout_ring_oscillator.py
    python examples/03_layout_ring_oscillator.py --lib MY_LIB --cell RO_LAYOUT
"""

from __future__ import annotations

import argparse

from virtuoso_bridge import BridgeClient


# ── PDK settings (change to match your process) ──────────────────────────
PDK_LIB = "tsmcN28"
NMOS_CELL = "nch_ulvt_mac"
PITCH = 0.52  # um, instance pitch
# ──────────────────────────────────────────────────────────────────────────


def build_layout(client: BridgeClient, lib: str, cell: str, stages: int) -> None:
    """Place a row of NMOS instances with M1 interconnect."""

    with client.layout.edit(lib, cell) as layout:
        # Place instances in a row
        for i in range(stages):
            x = i * PITCH
            layout.add_instance(
                PDK_LIB, NMOS_CELL, (x, 0), f"M{i}",
                params={"w": "200n", "l": "30n", "nf": 2},
            )

        # M1 bus across top (drain connections)
        total_width = (stages - 1) * PITCH
        layout.add_rect("M1", "drawing", (0, 0.3, total_width, 0.4))

        # Label
        layout.add_label("M1", "drawing", (total_width / 2, 0.35), "BUS")

        # VIA at each instance drain
        for i in range(stages):
            x = i * PITCH
            layout.add_via("M1_M2", (x, 0.35))

    print(f"Created layout: {lib}/{cell}/layout ({stages} stages)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lib", default="PLAYGROUND_LLM")
    parser.add_argument("--cell", default="RO_LAYOUT_DEMO")
    parser.add_argument("--stages", type=int, default=5)
    args = parser.parse_args()

    client = BridgeClient()
    if not client.test_connection().get("alive"):
        print("Bridge not running. Run: virtuoso-bridge start")
        return 1

    build_layout(client, args.lib, args.cell, args.stages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
