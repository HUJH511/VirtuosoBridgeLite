# Schematic Python API

Python wrapper for Cadence Virtuoso schematic editing via SKILL.

**Package:** `virtuoso_bridge.virtuoso.schematic`

```python
from virtuoso_bridge import VirtuosoClient
client = VirtuosoClient.from_env()
# SchematicOps is accessed via client.schematic
```

## SchematicEditor (context manager)

Declarative schematic editing — collects operations, executes them as a batch on `__exit__`, then runs `schCheck` + `dbSave` automatically.

```python
with client.schematic.edit(lib, cell) as sch:
    sch.add_instance(...)
    sch.add_wire_between_instance_terms(...)
    sch.add_pin(...)
    # schCheck + dbSave happen automatically on exit
```

| Method | SKILL | Description |
|--------|-------|-------------|
| `edit(lib, cell, view="schematic", mode="w")` | `dbOpenCellViewByType` | Returns `SchematicEditor` context manager |

### SchematicEditor methods

| Method | SKILL | Description |
|--------|-------|-------------|
| `add_instance(lib, cell, xy, orientation="R0", view="symbol", name="")` | `dbCreateInst` | Add instance by master name |
| `add_wire(points)` | `schCreateWire` | Add wire from point list |
| `add_label(xy, text, justification="lowerLeft", rotation="R0")` | `schCreateWireLabel` | Add wire label |
| `add_pin(name, xy, orientation="R0", direction="inputOutput")` | `schCreatePin` | Add pin |
| `add_pin_to_instance_term(inst, term, pin_name, *, direction, orientation)` | `schCreatePin` at terminal center | Add pin at instance terminal |
| `add_wire_between_instance_terms(from_inst, from_term, to_inst, to_term)` | `schCreateWire` between terminal centers | Wire two terminals directly |
| `add_net_label_to_instance_term(inst, term, net_name)` | `schCreateWire` + `schCreateWireLabel` | Labeled wire stub at terminal |
| `add_net_label_to_transistor(inst, drain, gate, source, body)` | Multiple `schCreateWire` + `schCreateWireLabel` | Label all MOS terminals (D/G/S/B) |

```python
with client.schematic.edit("myLib", "myCell") as sch:
    sch.add_instance("analogLib", "vdc", (0, 0), name="V0")
    sch.add_instance("analogLib", "gnd", (0, -0.625), name="GND0")
    sch.add_instance("analogLib", "res", (1.5, 0.5), orientation="R90", name="R0")
    sch.add_wire_between_instance_terms("V0", "PLUS", "R0", "PLUS")
    sch.add_pin("OUT", (3.0, 0.5))
    sch.add_net_label_to_instance_term("R0", "MINUS", "OUT")
```

## SchematicOps (direct execution)

Same operations as `SchematicEditor` but executed immediately (not batched).

```python
client.schematic.add_instance("analogLib", "vdc", (0, 0), name="V0")
client.schematic.add_wire_between_instance_terms("V0", "PLUS", "R0", "PLUS")
```

| Method | SKILL | Description |
|--------|-------|-------------|
| `open(lib, cell, *, view, mode)` | `dbOpenCellViewByType` | Open cellview |
| `save()` | `dbSave(cv)` | Save current cellview |
| `check()` | `schCheck(cv)` | Run schematic check |
| `add_instance(lib, cell, xy, *, orientation, view, name)` | `dbCreateInst` | Add instance |
| `add_wire(points)` | `schCreateWire` | Add wire |
| `add_label(xy, text, *, justification, rotation)` | `schCreateWireLabel` | Add label |
| `add_pin(name, xy, *, orientation, direction)` | `schCreatePin` | Add pin |
| `add_pin_to_instance_term(inst, term, pin_name, *, direction, orientation)` | `schCreatePin` at terminal | Add pin at terminal |
| `add_wire_between_instance_terms(from_inst, from_term, to_inst, to_term)` | `schCreateWire` between terminals | Wire two terminals |
| `add_net_label_to_instance_term(inst, term, net_name)` | Wire stub + label | Label terminal |
| `add_net_label_to_transistor(inst, drain, gate, source, body)` | Multiple wire stubs | Label MOS D/G/S/B |

## Low-level SKILL builders

`schematic/ops.py` — build SKILL strings without executing. Used internally by `SchematicOps` and `SchematicEditor`.

| Function | SKILL generated |
|----------|----------------|
| `schematic_create_inst(master_expr, name, x, y, orient)` | `dbCreateInst(cv master ...)` |
| `schematic_create_inst_by_master_name(lib, cell, view, name, x, y, orient)` | `dbOpenCellViewByType` + `dbCreateInst` |
| `schematic_create_wire(points)` | `schCreateWire(cv "route" "full" ...)` |
| `schematic_create_wire_label(x, y, text, just, rot)` | `schCreateWireLabel(cv ...)` |
| `schematic_create_pin(name, x, y, orient)` | `schCreatePin(cv ...)` |
| `schematic_create_pin_at_instance_term(inst, term, pin)` | Terminal center lookup + `schCreatePin` |
| `schematic_create_wire_between_instance_terms(from_inst, from_term, to_inst, to_term)` | Terminal center lookup + `schCreateWire` |
| `schematic_label_instance_term(inst, term, net)` | Terminal center + MOS-aware stub + `schCreateWireLabel` |
| `schematic_check()` | `schCheck(cv)` |

## Terminal-aware helpers

`add_wire_between_instance_terms` and `add_net_label_to_instance_term` resolve pin positions from the database — no need to guess coordinates.

`add_net_label_to_transistor` is MOS-aware: it knows drain/source go up/down (flipped for PMOS), gate goes left, body goes right. The stub direction adapts to the transistor orientation.
