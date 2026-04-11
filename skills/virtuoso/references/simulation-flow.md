# Standard Simulation Flow (GUI Mode)

Complete flow from opening Maestro to reading results. Follow this order exactly.

> **Why GUI mode?** Background sessions (`open_session` / `maeOpenSetup`) can read/write config but cannot run simulations reliably — `wait_until_done` returns immediately and `close_session` cancels in-flight runs. GUI mode is required for simulation.

## The 8-Step Flow

```python
from virtuoso_bridge import VirtuosoClient, decode_skill_output
from virtuoso_bridge.virtuoso.maestro import (
    read_config, read_results, save_setup, run_and_wait,
)

client = VirtuosoClient.from_env()
LIB, CELL = "myLib", "myTestbench"

# ── Step 1: Clean up stale sessions ──────────────────────────────
# Background sessions leave .cdslck files that block GUI opening.
# Always clean up first.
client.execute_skill('''
foreach(s maeGetSessions() maeCloseSession(?session s ?forceClose t))
''')

# ── Step 2: Open maestro in GUI mode ─────────────────────────────
client.execute_skill(
    f'deOpenCellView("{LIB}" "{CELL}" "maestro" "maestro" nil "r")')

# ── Step 3: Switch to editable mode ──────────────────────────────
# CAUTION: fails with ASSEMBLER-8127 dialog if another session
# already has this cellview in edit mode. See troubleshooting.md.
client.execute_skill('maeMakeEditable()')

# ── Step 4: Find session name ────────────────────────────────────
session = decode_skill_output(
    client.execute_skill('car(maeGetSessions())').output)

# ── Step 5: (Optional) Modify variables, outputs, etc. ──────────
# client.execute_skill(f'maeSetVar("CL" "1p" ?session "{session}")')

# ── Step 6: Save + run + wait ────────────────────────────────────
# save_setup persists changes; run_and_wait starts the simulation
# with a completion callback and polls via SSH.
# SKILL channel stays free during the wait.
save_setup(client, LIB, CELL, session=session)
history, status = run_and_wait(client, session=session, timeout=600)
history = history.strip('"')
print(f"Simulation {status}: {history}")

# ── Step 7: Read results ─────────────────────────────────────────
results = read_results(client, session, lib=LIB, cell=CELL, history=history)
for key, (expr, raw) in results.items():
    print(f"  {key}: {decode_skill_output(raw)[:200]}")

# ── Step 8: (Optional) Export waveforms ──────────────────────────
# from virtuoso_bridge.virtuoso.maestro import export_waveform
# export_waveform(client, session, 'VT("/VOUT")', "output/vout.txt",
#                 analysis="tran", history=history)
```

## When you already have an open GUI session

If Maestro is already open and editable (e.g. user opened it manually), skip steps 1-3:

```python
# Find the existing session
session = decode_skill_output(
    client.execute_skill('car(maeGetSessions())').output)

# Save, run, wait, read — same as steps 6-7
save_setup(client, LIB, CELL, session=session)
history, status = run_and_wait(client, session=session, timeout=600)
history = history.strip('"')
results = read_results(client, session, lib=LIB, cell=CELL, history=history)
```

## How `run_and_wait` works

1. Defines a SKILL callback procedure that writes a marker file when simulation finishes
2. Calls `maeRunSimulation(?callback "proc_name")` — callback is registered atomically with the simulation start (no race condition)
3. Polls the marker file via SSH (using `SSHRunner.run_command`, not the SKILL channel)
4. Returns `(history, status)` when marker appears

The SKILL channel remains **completely free** during the wait — you can execute_skill, dismiss dialogs, take screenshots, read config, etc.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Skipping step 1 | `deOpenCellView` returns nil/error | `maeCloseSession(?forceClose t)` on all stale sessions |
| Skipping step 3 | `maeRunSimulation` returns error | Must `maeMakeEditable()` after `deOpenCellView` |
| Using `open_session` for simulation | `wait_until_done` returns immediately | Use GUI mode (steps 2-3), not background |
| Skipping `save_setup` | Simulation uses stale parameters | Always save before running |
| Calling `maeMakeEditable` when another session has edit lock | ASSEMBLER-8127 dialog deadlocks SKILL channel | Close the other session first, or work in that session |
| `maeCloseResults` leaves Maestro read-only | Next `maeRunSimulation` fails | This is expected; re-run `maeMakeEditable()` if needed (check for edit lock first) |

## Optimization loops

For sweeping parameters and re-running simulation:

```python
for val in ["1p", "2p", "5p", "10p"]:
    client.execute_skill(f'maeSetVar("CL" "{val}" ?session "{session}")')
    save_setup(client, LIB, CELL, session=session)
    history, status = run_and_wait(client, session=session, timeout=600)
    history = history.strip('"')
    results = read_results(client, session, lib=LIB, cell=CELL, history=history)
    # ... process results ...
```

Add dialog recovery (`client.dismiss_dialog()`) in the loop if GUI dialogs may appear.
