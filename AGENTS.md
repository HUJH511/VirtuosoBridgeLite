# AGENTS.md — AI Agent Guide for virtuoso-bridge-lite

Remote Cadence Virtuoso control over SSH. Python on your machine, SKILL executes on the server.

## First-time setup check

When a user first opens this project or asks to get started, run these checks **before anything else**:

1. **Check `.env`** — does it exist and have `VB_REMOTE_HOST` set?
   - If not: run `pip install -e .` then `virtuoso-bridge init`, and ask the user to fill in their SSH host.

2. **Check SSH** — can we reach the remote machine?
   ```bash
   ssh <VB_REMOTE_HOST> echo ok
   ```
   - If this fails: SSH is not configured. Tell the user to fix SSH first (keys, config, jump host). The bridge cannot help with SSH setup — it assumes `ssh <host>` already works.

3. **Check Virtuoso** — is a Virtuoso process running on the remote?
   ```bash
   ssh <VB_REMOTE_HOST> "pgrep -f virtuoso"
   ```
   - If no process: tell the user to start Virtuoso on the remote machine first.

4. **Start bridge** — `virtuoso-bridge start`
   - If status is "degraded": the RAMIC daemon needs loading. Tell the user to paste the `load("...")` command shown in the output into the Virtuoso CIW window.

5. **Verify** — `virtuoso-bridge status`
   - Should show: service running, tunnel alive, daemon OK.

6. **Quick test** — run a SKILL expression:
   ```python
   from virtuoso_bridge import BridgeClient
   print(BridgeClient().execute_skill("1+2"))
   ```

Only proceed with the user's actual task after these checks pass.

## Key conventions

- All SKILL execution goes through `BridgeClient`. Never SSH into the machine and run SKILL manually.
- Layout/schematic editing uses `client.layout.edit()` / `client.schematic.edit()` context managers.
- Spectre simulation uses `SpectreSimulator.from_env()`. Requires `VB_CADENCE_CSHRC` in `.env`.
- The `core/` directory is for understanding the mechanism (3 files, 180 lines). Don't use it in production — use the installed package.
- Examples are in `examples/`. They all work out of the box after bridge setup.

## How to configure PDK paths

You do **not** need to manually look up PDK paths. Instead:

1. Open any testbench in Virtuoso
2. Export the netlist: **Simulation > Netlist > Create**
3. The `.scs` file contains all the info you need:

```spectre
include "/path/to/pdk/models/spectre/toplevel.scs" section=TOP_TT

M0 (VOUT VIN VSS VSS) nch_ulvt_mac l=30n w=1u nf=1
```

From this you know: PDK model paths, device names (`nch_ulvt_mac`), library names, default parameters, and Spectre syntax. No manual configuration needed.

## Skills

The `skills/` directory contains context documents that teach agents how to use the bridge:

| Skill | File | Covers |
|---|---|---|
| `virtuoso` | `skills/virtuoso/SKILL.md` | Bridge startup, SKILL execution, layout/schematic editing |
| `spectre` | `skills/spectre/SKILL.md` | Netlist preparation, remote simulation, result parsing |

### Installation

Copy skill files into your agent's skill directory:

```bash
# Claude Code
cp -r skills/virtuoso .claude/skills/
cp -r skills/spectre  .claude/skills/

# Cursor
cp skills/virtuoso/SKILL.md .cursor/rules/virtuoso.md
cp skills/spectre/SKILL.md  .cursor/rules/spectre.md

# Other agents — place wherever your tool reads context from
```

### Skill reference files

```
skills/virtuoso/
  SKILL.md                              # main skill document
  references/
    layout.md                           # layout editing patterns and SKILL examples
    schematic.md                        # schematic editing patterns
    t28_metal_rules.md                  # metal width/spacing rules (T28 example)
    bindkey_operation_index.md          # Virtuoso bindkey reference
  assets/
    cfmom_unary_cdac_reference.py       # real-world layout example

skills/spectre/
  SKILL.md                              # Spectre simulation workflow
```
