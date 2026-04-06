# Maestro Python API

Python wrapper for Cadence Maestro (ADE Assembler) SKILL functions.

**Package:** `virtuoso_bridge.virtuoso.maestro`

```python
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_session, close_session, read_config
```

## Session Management

`maestro/session.py`

| Python | SKILL | Description |
|--------|-------|-------------|
| `open_session(client, lib, cell) -> str` | `maeOpenSetup` | Background open, returns session string |
| `close_session(client, ses)` | `maeCloseSession` | Background close |
| `find_open_session(client) -> str \| None` | `maeGetSessions` + `maeGetSetup` | Find first active session with valid test |

```python
ses = open_session(client, "PLAYGROUND_AMP", "TB_AMP_5T_D2S_DC_AC")
# ... do work ...
close_session(client, ses)
```

## Read Config

`maestro/reader.py`

| Python | SKILL functions called |
|--------|-----------------------|
| `read_config(client, ses, verbose=1) -> dict[str, tuple[str, str]]` | See below |

Returns a dict where key = label, value = `(skill_expr, raw_output)`.
- `skill_expr` — exact SKILL expression, can be pasted into CIW to reproduce
- `raw_output` — raw SKILL return value

### Verbosity levels

| verbose | What it reads | Use case |
|---------|---------------|----------|
| **0** | tests, enabled analyses, outputs, variables | Quick overview |
| **1** (default) | + per-analysis params, parameters, corners | Full setup |
| **2** | + envOption, simOption, runMode, jobControl, simulation results | Everything |

### Queries by level

**Level 0** — quick overview:

| Key | SKILL |
|-----|-------|
| `maeGetSetup` | `maeGetSetup(?session ses)` |
| `maeGetEnabledAnalysis` | `maeGetEnabledAnalysis(test ?session ses)` |
| `maeGetTestOutputs` | `maeGetTestOutputs(test ?session ses)` — returns `(name type signal expression)` |
| `variables` | `maeGetSetup(?session ses ?typeName "variables")` |

**Level 1** — adds full setup:

| Key | SKILL |
|-----|-------|
| `maeGetAnalysis:<name>` | `maeGetAnalysis(test name ?session ses)` — one per enabled analysis |
| `parameters` | `maeGetSetup(?session ses ?typeName "parameters")` |
| `corners` | `maeGetSetup(?session ses ?typeName "corners")` |

**Level 2** — adds env/sim/results:

| Key | SKILL |
|-----|-------|
| `maeGetEnvOption` | `maeGetEnvOption(test ?session ses)` — all env options (model files, view lists, ...) |
| `maeGetSimOption` | `maeGetSimOption(test ?session ses)` — all sim options (reltol, temp, ...) |
| `maeGetCurrentRunMode` | `maeGetCurrentRunMode(?session ses)` |
| `maeGetJobControlMode` | `maeGetJobControlMode(?session ses)` |
| `maeGetResultTests` | `maeGetResultTests()` — only if results exist |
| `maeGetResultOutputs:<test>` | `maeGetResultOutputs(?testName test)` |
| `maeGetOutputValue:<test>:<output>` | `maeGetOutputValue(output test)` |
| `maeGetSpecStatus:<test>:<output>` | `maeGetSpecStatus(output test)` |
| `maeGetOverallSpecStatus` | `maeGetOverallSpecStatus()` |
| `maeGetOverallYield` | `maeGetOverallYield(history)` |
| `maeGetSimulationMessages` | `maeGetSimulationMessages(?session ses)` |

```python
ses = open_session(client, "PLAYGROUND_AMP", "TB_AMP_5T_D2S_DC_AC")

# Quick overview
for key, (skill_expr, raw) in read_config(client, ses, verbose=0).items():
    print(f"[{key}] {skill_expr}")
    print(raw)

# Full setup (default)
read_config(client, ses)

# Everything including env options and simulation results
read_config(client, ses, verbose=2)

close_session(client, ses)
```

## Write — Test

`maestro/writer.py`

| Python | SKILL | Description |
|--------|-------|-------------|
| `create_test(client, test, *, lib, cell, view="schematic", simulator="spectre", ses="")` | `maeCreateTest` | Create a new test |
| `set_design(client, test, *, lib, cell, view="schematic", ses="")` | `maeSetDesign` | Change DUT for existing test |

```python
create_test(client, "TRAN2", lib="myLib", cell="myCell")
set_design(client, "TRAN2", lib="myLib", cell="newCell")
```

## Write — Analysis

| Python | SKILL | Description |
|--------|-------|-------------|
| `set_analysis(client, test, analysis, *, enable=True, options="", ses="")` | `maeSetAnalysis` | Enable/disable analysis, set options |

```python
# Enable transient with stop=60n
set_analysis(client, "TRAN2", "tran", options='(("stop" "60n") ("errpreset" "conservative"))')

# Enable AC
set_analysis(client, "TRAN2", "ac", options='(("start" "1") ("stop" "10G") ("dec" "20"))')

# Disable tran
set_analysis(client, "TRAN2", "tran", enable=False)
```

## Write — Outputs & Specs

| Python | SKILL | Description |
|--------|-------|-------------|
| `add_output(client, name, test, *, output_type="", signal_name="", expr="", ses="")` | `maeAddOutput` | Add waveform or expression output |
| `set_spec(client, name, test, *, lt="", gt="", ses="")` | `maeSetSpec` | Set pass/fail spec |

```python
# Waveform output
add_output(client, "OutPlot", "TRAN2", output_type="net", signal_name="/OUT")

# Expression output
add_output(client, "maxOut", "TRAN2", output_type="point", expr='ymax(VT(\\"/OUT\\"))')

# Spec: maxOut < 400mV
set_spec(client, "maxOut", "TRAN2", lt="400m")

# Spec: BW > 1GHz
set_spec(client, "BW", "AC", gt="1G")
```

## Write — Variables

| Python | SKILL | Description |
|--------|-------|-------------|
| `set_var(client, name, value, *, type_name="", type_value="", ses="")` | `maeSetVar` | Set global variable or corner sweep |
| `get_var(client, name, *, ses="")` | `maeGetVar` | Get variable value |

```python
set_var(client, "vdd", "1.35")
get_var(client, "vdd")  # => '"1.35"'

# Corner sweep
set_var(client, "vdd", "1.2 1.4", type_name="corner", type_value='("myCorner")')
```

## Write — Parameters (Parametric Sweep)

| Python | SKILL | Description |
|--------|-------|-------------|
| `get_parameter(client, name, *, type_name="", type_value="", ses="")` | `maeGetParameter` | Read parameter value |
| `set_parameter(client, name, value, *, type_name="", type_value="", ses="")` | `maeSetParameter` | Add/update parameter |

```python
set_parameter(client, "cload", "1p")
set_parameter(client, "cload", "1p 2p", type_name="corner", type_value='("myCorner")')
```

## Write — Environment & Simulator Options

| Python | SKILL | Description |
|--------|-------|-------------|
| `set_env_option(client, test, options, *, ses="")` | `maeSetEnvOption` | Set model files, view lists, etc. |
| `set_sim_option(client, test, options, *, ses="")` | `maeSetSimOption` | Set reltol, temp, gmin, etc. |

```python
# Change model file section
set_env_option(client, "TRAN2",
    '(("modelFiles" (("/path/model.scs" "ff"))))')

# Change temperature
set_sim_option(client, "TRAN2", '(("temp" "85"))')
```

## Write — Corners

| Python | SKILL | Description |
|--------|-------|-------------|
| `set_corner(client, name, *, disable_tests="", ses="")` | `maeSetCorner` | Create/modify corner |
| `load_corners(client, filepath, *, sections="corners", operation="overwrite")` | `maeLoadCorners` | Load corners from CSV |

```python
set_corner(client, "myCorner", disable_tests='("AC" "TRAN")')
load_corners(client, "my_corners.csv")
```

## Write — Run Mode & Job Control

| Python | SKILL | Description |
|--------|-------|-------------|
| `set_current_run_mode(client, run_mode, *, ses="")` | `maeSetCurrentRunMode` | Switch run mode |
| `set_job_control_mode(client, mode, *, ses="")` | `maeSetJobControlMode` | Set Local/LSF/etc. |
| `set_job_policy(client, policy, *, test_name="", job_type="", ses="")` | `maeSetJobPolicy` | Set job policy |

```python
set_current_run_mode(client, "Single Run, Sweeps and Corners")
set_job_control_mode(client, "Local")
```

## Write — Simulation

| Python | SKILL | Description |
|--------|-------|-------------|
| `run_simulation(client, *, ses="")` | `maeRunSimulation` | Run (async) |
| `wait_until_done(client, timeout=300)` | `maeWaitUntilDone` | Block until done |

```python
run_simulation(client)
wait_until_done(client, timeout=600)
```

## Write — Export

| Python | SKILL | Description |
|--------|-------|-------------|
| `create_netlist_for_corner(client, test, corner, output_dir)` | `maeCreateNetlistForCorner` | Export netlist for one corner |
| `export_output_view(client, filepath, *, view="Detail")` | `maeExportOutputView` | Export results to CSV |
| `write_script(client, filepath)` | `maeWriteScript` | Export setup as SKILL script |

```python
create_netlist_for_corner(client, "TRAN2", "myCorner_2", "./myNetlistDir")
export_output_view(client, "./results.csv")
write_script(client, "mySetupScript.il")
```

## Write — Migration

| Python | SKILL | Description |
|--------|-------|-------------|
| `migrate_adel_to_maestro(client, lib, cell, state)` | `maeMigrateADELStateToMaestro` | ADE L → Maestro |
| `migrate_adexl_to_maestro(client, lib, cell, view="adexl", *, maestro_view="maestro")` | `maeMigrateADEXLToMaestro` | ADE XL → Maestro |

```python
migrate_adel_to_maestro(client, "myLib", "myCell", "spectre_state1")
migrate_adexl_to_maestro(client, "myLib", "myCell")
```

## Write — Save

| Python | SKILL | Description |
|--------|-------|-------------|
| `save_setup(client, lib, cell, *, ses="")` | `maeSaveSetup` | Save maestro to disk |

```python
save_setup(client, "myLib", "myCell", ses=ses)
```
