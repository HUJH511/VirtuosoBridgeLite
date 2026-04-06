# Layout Python API

Python wrapper for Cadence Virtuoso layout editing via SKILL.

**Package:** `virtuoso_bridge.virtuoso.layout`

```python
from virtuoso_bridge import VirtuosoClient
client = VirtuosoClient.from_env()
# LayoutOps is accessed via client.layout
```

## LayoutEditor (context manager)

Declarative layout editing — collects operations, executes as a batch on `__exit__`, then saves automatically.

```python
with client.layout.edit(lib, cell) as lay:
    lay.add_rect("M1", "drawing", (0, 0, 1, 0.5))
    lay.add_path("M2", "drawing", [(0, 0), (1, 0)], width=0.1)
    lay.add_instance("tsmcN28", "nch_ulvt_mac", (0, 0), "M0")
    lay.add_via("M1_M2", (0.5, 0.25))
    # dbSave happens automatically on exit
```

| Method | SKILL | Description |
|--------|-------|-------------|
| `edit(lib, cell, view="layout", mode="w")` | `dbOpenCellViewByType` | Returns `LayoutEditor` context manager |

### LayoutEditor methods

**Create shapes:**

| Method | SKILL | Description |
|--------|-------|-------------|
| `add_rect(layer, purpose, bbox)` | `dbCreateRect` | Add rectangle `(x1, y1, x2, y2)` |
| `add_path(layer, purpose, points, width)` | `dbCreatePath` | Add path with width |
| `add_polygon(layer, purpose, points)` | `dbCreatePolygon` | Add polygon |
| `add_label(layer, purpose, xy, text)` | `dbCreateLabel` | Add text label |

**Instances & vias:**

| Method | SKILL | Description |
|--------|-------|-------------|
| `add_instance(lib, cell, xy, name, orientation="R0", view="layout")` | `dbOpenCellViewByType` + `dbCreateInst` | Add instance |
| `add_param_instance(lib, cell, xy, name, params, orientation="R0")` | `dbOpenCellViewByType` + `dbCreateParamInst` | Add parameterized instance |
| `add_via(via_def, xy)` | `dbCreateVia` | Add via at point |
| `add_via_by_name(via_name, xy)` | Via def lookup + `dbCreateVia` | Add via by name string |
| `add_mosaic(lib, cell, xy, name, cols, rows, *, dx, dy)` | `dbCreateSimpleMosaic` | Add mosaic array |

```python
with client.layout.edit("myLib", "myCell") as lay:
    # Rectangle on M1
    lay.add_rect("M1", "drawing", (0, 0, 2.0, 0.5))

    # Path on M2
    lay.add_path("M2", "drawing", [(0, 0), (2, 0), (2, 1)], width=0.1)

    # Polygon
    lay.add_polygon("M1", "drawing", [(0, 0), (1, 0), (1, 1), (0.5, 1.5), (0, 1)])

    # Instance
    lay.add_instance("tsmcN28", "nch_ulvt_mac", (0, 0), "M0")

    # Parameterized instance
    lay.add_param_instance("tsmcN28", "nch_ulvt_mac", (2, 0), "M1",
                           params={"w": "500n", "l": "60n", "nf": "4"})

    # Via
    lay.add_via("M1_M2", (1.0, 0.25))

    # Mosaic (array of instances)
    lay.add_mosaic("tsmcN28", "nch_ulvt_mac", (0, 0), "MOS_ARRAY",
                   cols=4, rows=2, dx=0.5, dy=1.0)
```

### Append mode

For large layouts, split into chunks — first call `mode="w"` (create), then `mode="a"` (append):

```python
with client.layout.edit(lib, cell, mode="w") as lay:
    lay.add_rect("M1", "drawing", (0, 0, 10, 0.5))  # first chunk

with client.layout.edit(lib, cell, mode="a") as lay:
    lay.add_rect("M2", "drawing", (0, 1, 10, 1.5))  # appended
```

## LayoutOps (direct execution)

Same operations executed immediately (not batched).

**Read operations:**

| Method | SKILL | Description |
|--------|-------|-------------|
| `read_summary(lib, cell, *, view)` | Instance/shape count summary | Quick overview |
| `read_geometry(lib, cell, *, view)` | Full geometry dump | Returns parsed objects list |
| `list_shapes()` | Shape types and LPPs | From open window |

**Layer control:**

| Method | SKILL | Description |
|--------|-------|-------------|
| `set_active_lpp(layer, purpose)` | `leSetEntryLayer` | Set active layer-purpose |
| `show_only_layers(layers)` | Hide all + show selected | Show specific LPPs |
| `show_layers(layers)` | `leSetLayerVisible` | Show LPPs |
| `hide_layers(layers)` | `leSetLayerVisible nil` | Hide LPPs |
| `highlight_net(net_name)` | `geSelectNet` | Highlight net |
| `fit_view()` | `hiZoomAbsoluteScale` | Fit view |

**Edit operations:**

| Method | SKILL | Description |
|--------|-------|-------------|
| `clear_current()` | Delete all visible shapes | Clear current layout |
| `clear_routing()` | Delete all + save | Clear and save |
| `select_box(bbox, *, mode_name)` | `geSelectBox` | Select in bounding box |
| `delete_selected()` | `leDeleteAllSelect` | Delete selection |
| `delete_shapes_on_layer(layer, purpose)` | Iterate + delete shapes | Delete by layer |
| `delete_cell(lib, cell)` | Close windows + `ddDeleteObj` | Delete cell |

```python
# Read geometry
result = client.layout.read_geometry("myLib", "myCell")

# Show only M1 and M2
client.layout.show_only_layers([("M1", "drawing"), ("M2", "drawing")])

# Delete all shapes on M3
client.layout.delete_shapes_on_layer("M3", "drawing")
```

## Low-level SKILL builders

`layout/ops.py` — build SKILL strings without executing. Used internally.

**Create:**

| Function | SKILL generated |
|----------|----------------|
| `layout_create_rect(layer, purpose, bbox)` | `dbCreateRect(cv ...)` |
| `layout_create_path(layer, purpose, points, width)` | `dbCreatePath(cv ...)` |
| `layout_create_polygon(layer, purpose, points)` | `dbCreatePolygon(cv ...)` |
| `layout_create_label(layer, purpose, xy, text)` | `dbCreateLabel(cv ...)` |
| `layout_create_via(via_def_expr, xy)` | `dbCreateVia(cv ...)` |
| `layout_create_via_by_name(via_name, xy)` | Via lookup + `dbCreateVia` |
| `layout_create_param_inst(lib, cell, xy, name, params)` | `dbOpenCellViewByType` + `dbCreateParamInst` |
| `layout_create_simple_mosaic(lib, cell, xy, name, cols, rows, dx, dy)` | `dbCreateSimpleMosaic(cv ...)` |

**Read:**

| Function | SKILL generated |
|----------|----------------|
| `layout_read_summary(lib, cell)` | Instance/shape count |
| `layout_read_geometry(lib, cell)` | Full geometry dump (tab-separated) |
| `layout_list_shapes()` | Shape types from open window |

**Edit:**

| Function | SKILL generated |
|----------|----------------|
| `clear_current_layout()` | Delete visible shapes |
| `layout_clear_routing()` | Delete all + save |
| `layout_select_box(bbox)` | `geSelectBox` |
| `layout_delete_selected()` | `leDeleteAllSelect` |
| `layout_delete_shapes_on_layer(layer, purpose)` | Iterate + delete |
| `layout_delete_cell(lib, cell)` | Close + `ddDeleteObj` |

**Layer visibility:**

| Function | SKILL generated |
|----------|----------------|
| `layout_set_active_lpp(layer, purpose)` | `leSetEntryLayer` |
| `layout_show_only_layers(layers)` | Hide all + show selected |
| `layout_show_layers(layers)` | `leSetLayerVisible t` |
| `layout_hide_layers(layers)` | `leSetLayerVisible nil` |
| `layout_highlight_net(net_name)` | `geSelectNet` |
| `layout_fit_view()` | `hiZoomAbsoluteScale` |

## Utility

| Function | Description |
|----------|-------------|
| `parse_layout_geometry_output(raw)` | Parse `layout_read_geometry` output into `[{"kind": ..., "bbox": ..., ...}]` |
| `layout_find_via_def(via_name)` | Build SKILL to find via definition by name |
| `layout_via_def_expr_from_name(via_name)` | Build SKILL expr for via def lookup |
