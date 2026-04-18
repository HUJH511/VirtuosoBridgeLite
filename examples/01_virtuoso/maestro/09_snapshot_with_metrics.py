#!/usr/bin/env python3
"""Snapshot a Maestro session into a timestamped directory with metrics.

Writes to  H:/analog-agents/output/snapshots/<ts>__<lib>__<cell>/ :
    snapshot.json    — structured dict (session_info, config, env, variables,
                       outputs, corners)
    maestro.sdb      — the raw XML we parsed (for audit / offline re-parse)
    metrics.json     — per-step wall time, SKILL call count, SCP transfer
                       count.  SSH connection count is 0 (persistent tunnel).

Naming rule:  single `_` within a segment, double `__` between segments.

Usage:
    1. Open a maestro view in Virtuoso GUI (or run a sim that leaves one open)
    2. python 09_snapshot_with_metrics.py
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import (
    find_open_session,
    read_config,
    read_corners,
    read_env,
    read_outputs,
    read_session_info,
    read_status,
    read_variables,
    snapshot,
)


# --- Output root -----------------------------------------------------------
# Always write under the project's output/, never inside the vendored repo.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # .../analog-agents
SNAPSHOTS_ROOT = _PROJECT_ROOT / "output" / "snapshots"


# --- Instrumentation -------------------------------------------------------

class Counters:
    def __init__(self):
        self.skill_calls = 0
        self.skill_time = 0.0
        self.scp_transfers = 0
        self.scp_time = 0.0


def wrap(client: VirtuosoClient, counters: Counters) -> None:
    orig_skill = client.execute_skill
    orig_download = client.download_file
    orig_upload = client.upload_file

    def skill_wrapper(*a, **kw):
        t0 = time.perf_counter()
        try:
            return orig_skill(*a, **kw)
        finally:
            counters.skill_calls += 1
            counters.skill_time += time.perf_counter() - t0

    def download_wrapper(*a, **kw):
        t0 = time.perf_counter()
        try:
            return orig_download(*a, **kw)
        finally:
            counters.scp_transfers += 1
            counters.scp_time += time.perf_counter() - t0

    def upload_wrapper(*a, **kw):
        t0 = time.perf_counter()
        try:
            return orig_upload(*a, **kw)
        finally:
            counters.scp_transfers += 1
            counters.scp_time += time.perf_counter() - t0

    client.execute_skill = skill_wrapper
    client.download_file = download_wrapper
    client.upload_file = upload_wrapper


STEPS: list[dict] = []


@contextmanager
def step(name: str, counters: Counters):
    s0 = counters.skill_calls
    t0 = counters.scp_transfers
    start = time.perf_counter()
    try:
        yield
    finally:
        STEPS.append({
            "step": name,
            "wall_s": round(time.perf_counter() - start, 4),
            "skill_calls": counters.skill_calls - s0,
            "scp_transfers": counters.scp_transfers - t0,
        })


# --- Main ------------------------------------------------------------------

def main() -> int:
    counters = Counters()
    client = VirtuosoClient.from_env()
    wrap(client, counters)

    with step("find_open_session", counters):
        session = find_open_session(client)
    if not session:
        print("No active Maestro session found.")
        return 1
    print(f"Session: {session}\n")

    # Grab session_info FIRST so we can construct the snapshot dir.
    with step("read_session_info", counters):
        info = read_session_info(client, session)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    lib = info.get("lib") or "unknown_lib"
    cell = info.get("cell") or "unknown_cell"
    snap_dir = SNAPSHOTS_ROOT / f"{ts}__{lib}__{cell}"
    snap_dir.mkdir(parents=True, exist_ok=True)
    print(f"Snapshot dir: {snap_dir}\n")

    with step("read_status", counters):
        status = read_status(client, session)
    print(f"status.run_mode: {status['run_mode']}")
    print(f"status.current_history_handle: {status['current_history_handle']}")
    print(f"status.messages: error={len(status['messages']['error'])} "
          f"warning={len(status['messages']['warning'])} "
          f"info={len(status['messages']['info'])}")

    with step("read_config", counters):
        config = read_config(client, session)

    with step("read_env", counters):
        env = read_env(client, session)

    with step("read_variables", counters):
        variables = read_variables(client, session)
    print(f"variables ({len(variables)}): {variables}")

    with step("read_outputs", counters):
        outputs = read_outputs(client, session)
    named = [o for o in outputs if o["category"] == "computed"]
    save_only = [o for o in outputs if o["category"] == "save-only"]
    print(f"\noutputs: {len(outputs)} total "
          f"({len(named)} computed, {len(save_only)} save-only)")

    # Download sdb directly into the snapshot dir — persistent, audit-friendly.
    local_sdb = snap_dir / "maestro.sdb"
    with step("read_corners", counters):
        corners = read_corners(client, session,
                               sdb_path=info.get("sdb_path") or None,
                               local_sdb_path=str(local_sdb))
    print(f"\ncorners: {len(corners)} total")
    for name, c in corners.items():
        state = "ON " if c["enabled"] else "off"
        temps = ",".join(c["temperature"]) or "-"
        nmod = sum(1 for m in c["models"] if m["enabled"])
        print(f"  {state} {name:10s} temp=[{temps}]  {nmod} models enabled")

    # Full aggregator — uses the already-downloaded sdb via sdb_cache_path so
    # it doesn't re-scp (and overwriting the same file is harmless).
    with step("snapshot (aggregator)", counters):
        snap = snapshot(client, session, include_results=False,
                        sdb_cache_path=str(local_sdb))

    # --- Write artifacts ---------------------------------------------------
    (snap_dir / "snapshot.json").write_text(
        json.dumps(snap, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    totals = {
        "wall_s": round(sum(s["wall_s"] for s in STEPS), 4),
        "skill_calls": counters.skill_calls,
        "scp_transfers": counters.scp_transfers,
        "skill_time_s": round(counters.skill_time, 4),
        "scp_time_s": round(counters.scp_time, 4),
    }
    metrics = {
        "timestamp": ts,
        "session": session,
        "lib": lib,
        "cell": cell,
        "steps": STEPS,
        "totals": totals,
        "note": "skill_calls go over the persistent SSH tunnel (no new SSH); "
                "scp_transfers are the only SSH connection openings.",
    }
    (snap_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # --- Console summary ---------------------------------------------------
    print("\n" + "=" * 70)
    print(f"{'step':30s} {'wall_s':>8s} {'skill':>8s} {'scp':>6s}")
    print("-" * 70)
    for s in STEPS:
        print(f"{s['step']:30s} {s['wall_s']:>8.3f} "
              f"{s['skill_calls']:>8d} {s['scp_transfers']:>6d}")
    print("-" * 70)
    print(f"{'TOTAL':30s} {totals['wall_s']:>8.3f} "
          f"{totals['skill_calls']:>8d} {totals['scp_transfers']:>6d}")
    print(f"   (skill wall: {totals['skill_time_s']:.3f} s  "
          f"scp wall: {totals['scp_time_s']:.3f} s)")
    print(f"\nWrote:")
    print(f"  {snap_dir / 'snapshot.json'}")
    print(f"  {snap_dir / 'maestro.sdb'}")
    print(f"  {snap_dir / 'metrics.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
