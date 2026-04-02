#!/usr/bin/env python3
"""Create a CMOS inverter schematic from scratch.

Demonstrates schematic editing: adding instances, wires, pins, and labels.
The device names and library below are for TSMC 28nm — change them to match
your PDK. An AI agent can read your exported netlist to find the right names.

Prerequisites:
  - .env configured, bridge running
  - A library exists in Virtuoso (default: PLAYGROUND_LLM)

Usage:
    python examples/02_schematic_inverter.py
    python examples/02_schematic_inverter.py --lib MY_LIB --cell INV_TEST
"""

from __future__ import annotations

import argparse
import sys

from virtuoso_bridge import BridgeClient


# ── PDK device names (change these to match your process) ─────────────────
PDK_LIB = "tsmcN28"             # PDK library name in Virtuoso
NMOS_CELL = "nch_ulvt_mac"      # NMOS device cell name
PMOS_CELL = "pch_ulvt_mac"      # PMOS device cell name
# ──────────────────────────────────────────────────────────────────────────


def build_inverter(client: BridgeClient, lib: str, cell: str) -> None:
    """Create a CMOS inverter schematic."""

    with client.schematic.edit(lib, cell) as sch:
        # NMOS: bottom
        sch.add_instance(PDK_LIB, NMOS_CELL, (0, 0), "MN",
                         params={"w": "500n", "l": "30n", "nf": 1})

        # PMOS: above NMOS
        sch.add_instance(PDK_LIB, PMOS_CELL, (0, 1.5), "MP",
                         params={"w": "1u", "l": "30n", "nf": 1})

        # Power supplies
        sch.add_instance("analogLib", "vdd", (0, 2.5), "VDD0")
        sch.add_instance("analogLib", "gnd", (0, -1.0), "GND0")

        # Wires: VDD to PMOS source, GND to NMOS source
        sch.add_wire([(0, 2.5), (0, 2.0)])    # VDD → MP source
        sch.add_wire([(0, -1.0), (0, -0.5)])  # GND → MN source

        # Wire: gates connected (input)
        sch.add_wire([(-0.5, 0.25), (-0.5, 1.75)])  # gate bus

        # Wire: drains connected (output)
        sch.add_wire([(0.5, 0.5), (0.5, 1.0)])  # drain bus

        # Input and output pins
        sch.add_pin("VIN", "input", (-1.0, 1.0))
        sch.add_pin("VOUT", "output", (1.0, 0.75))

        # Wire pins to nodes
        sch.add_wire([(-1.0, 1.0), (-0.5, 1.0)])  # VIN → gate
        sch.add_wire([(0.5, 0.75), (1.0, 0.75)])   # drain → VOUT

    print(f"Created inverter schematic: {lib}/{cell}/schematic")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create CMOS inverter schematic")
    parser.add_argument("--lib", default="PLAYGROUND_LLM", help="Library name")
    parser.add_argument("--cell", default="INV_DEMO", help="Cell name")
    args = parser.parse_args()

    client = BridgeClient()
    alive = client.test_connection()
    if not alive.get("alive"):
        print("Bridge not running. Run: virtuoso-bridge start")
        return 1

    build_inverter(client, args.lib, args.cell)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
