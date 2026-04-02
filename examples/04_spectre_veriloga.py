#!/usr/bin/env python3
"""Run a Spectre simulation with a Verilog-A model.

This example creates a simple Verilog-A resistor model, writes a testbench
netlist that uses it, and runs a DC simulation via SpectreSimulator.

No PDK models required — pure Verilog-A. Good for verifying your Spectre
setup works before dealing with PDK paths.

Prerequisites:
  - .env configured with VB_REMOTE_HOST
  - VB_CADENCE_CSHRC set (so spectre is in PATH)
  - virtuoso-bridge start

Usage:
    python examples/04_spectre_veriloga.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parent / "output" / "spectre_veriloga"

# ── Verilog-A resistor model ─────────────────────────────────────────────
VERILOGA_MODEL = """\
`include "constants.vams"
`include "disciplines.vams"

module va_resistor(p, n);
    inout p, n;
    electrical p, n;
    parameter real r = 1k from (0:inf);

    analog begin
        V(p, n) <+ r * I(p, n);
    end
endmodule
"""

# ── Spectre testbench netlist ────────────────────────────────────────────
NETLIST = """\
// Verilog-A resistor test — DC sweep
simulator lang=spectre
global 0

ahdl_include "./va_resistor.va"

// DUT: 1k resistor
R0 (out 0) va_resistor r=1k

// DC voltage source swept from 0 to 1V
V0 (out 0) vsource type=dc dc=1

// DC analysis
dcOp dc
"""


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Write Verilog-A model
    va_path = WORK_DIR / "va_resistor.va"
    va_path.write_text(VERILOGA_MODEL, encoding="utf-8")
    print(f"[Write] {va_path}")

    # Write netlist
    netlist_path = WORK_DIR / "tb_va_resistor.scs"
    netlist_path.write_text(NETLIST, encoding="utf-8")
    print(f"[Write] {netlist_path}")

    # Run simulation
    from virtuoso_bridge.spectre.runner import SpectreSimulator

    sim = SpectreSimulator.from_env(
        work_dir=WORK_DIR,
        output_format="psfascii",
    )

    print("[Run] Spectre DC simulation with Verilog-A resistor...")
    result = sim.run_simulation(netlist_path, {})

    print(f"[Status] {result.status.value}")
    if result.errors:
        for e in result.errors[:5]:
            print(f"  [Error] {e}")
    if result.warnings:
        print(f"  [Warnings] {len(result.warnings)}")

    if result.ok:
        print(f"[Signals] {sorted(result.data.keys())}")
        # DC op: check voltage across resistor
        for sig in sorted(result.data.keys()):
            vals = result.data[sig]
            if vals:
                print(f"  {sig}: {vals[0] if len(vals) == 1 else vals[:3]}")
        print("\nSpectre + Verilog-A works!")
    else:
        print("\nSimulation failed. Check VB_CADENCE_CSHRC in .env.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
