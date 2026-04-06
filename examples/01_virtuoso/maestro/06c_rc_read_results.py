#!/usr/bin/env python3
"""Step 3: Read simulation results, export waveforms.

Prerequisite: run 06b_rc_simulate.py first.

NOTE: maeOpenResults / maeGetOutputValue only work in GUI mode
(deOpenCellView + maeMakeEditable). Background sessions return nil.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import read_results, export_waveform

LIB = "PLAYGROUND_LLM"
CELL = "TB_RC_FILTER"


def parse_wave_file(path: str) -> list[tuple[float, float]]:
    pairs = []
    for line in Path(path).read_text().splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                pairs.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    return pairs


def main() -> int:
    client = VirtuosoClient.from_env()
    print(f"[info] {LIB}/{CELL}")

    # Must use GUI mode for reading results
    client.execute_skill(
        f'deOpenCellView("{LIB}" "{CELL}" "maestro" "maestro" nil "r")')
    client.execute_skill('maeMakeEditable()')

    # Get session
    r = client.execute_skill('''
let((s) s = nil
  foreach(x maeGetSessions() unless(s when(maeGetSetup(?session x) s = x)))
  s)
''')
    session = (r.output or "").strip('"')
    if not session or session == "nil":
        print("No active session found.")
        return 1

    # Scalar results
    print("\n=== Results ===")
    results = read_results(client, session, lib=LIB, cell=CELL)
    if results:
        for key, (expr, raw) in results.items():
            print(f"[{key}] {expr}")
            print(f"  {raw}")
    else:
        print("No results found.")

    # Export waveforms
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract history name from yield result for export_waveform
    yield_raw = results.get("maeGetOverallYield", ("", ""))[0]
    import re
    hm = re.search(r'Interactive\.\d+', yield_raw)
    history = hm.group(0) if hm else ""

    print("\n=== Waveforms ===")
    mag_file = str(output_dir / "rc_ac_mag_db.txt")
    export_waveform(client, session, 'dB20(mag(v("/OUT")))', mag_file,
                    analysis="ac", history=history)
    print(f"AC magnitude: {mag_file}")

    phase_file = str(output_dir / "rc_ac_phase.txt")
    export_waveform(client, session, 'phase(v("/OUT"))', phase_file,
                    analysis="ac", history=history)
    print(f"AC phase: {phase_file}")

    # Quick comparison
    data = parse_wave_file(mag_file)
    if data:
        print(f"\n=== {len(data)} frequency points ===")
        for target in [1e6, 1e8, 1e9, 1e10]:
            closest = min(data, key=lambda p: abs(p[0] - target))
            print(f"  {target:.0e} Hz: {closest[1]:.2f} dB")

        for i, (f, db) in enumerate(data):
            if db <= -3.0:
                if i > 0:
                    f_prev, db_prev = data[i - 1]
                    ratio = (-3.0 - db_prev) / (db - db_prev)
                    f_3db = f_prev + ratio * (f - f_prev)
                else:
                    f_3db = f
                print(f"  f_3dB = {f_3db:.3e} Hz")
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
