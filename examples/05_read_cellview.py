#!/usr/bin/env python3
"""Read back an open cellview's contents: instances, shapes, properties.

Demonstrates how to inspect existing designs — useful for AI agents that
need to understand what's already in a layout or schematic before editing.

Usage:
    python examples/05_read_cellview.py
    python examples/05_read_cellview.py --lib MYLIB --cell MYCELL --view layout
"""

from __future__ import annotations

import argparse
import json

from virtuoso_bridge import BridgeClient


def read_cellview(client: BridgeClient, lib: str, cell: str, view: str) -> None:
    # Open the cellview
    client.open_cell_view(lib, cell, view)
    print(f"Opened: {lib}/{cell}/{view}")

    # Instance count and names
    r = client.execute_skill("geGetEditCellView()~>instances~>name")
    instances = r["result"]["output"]
    print(f"\nInstances: {instances[:200]}")

    # Instance count
    r = client.execute_skill("length(geGetEditCellView()~>instances)")
    print(f"Instance count: {r['result']['output']}")

    # Shape count
    r = client.execute_skill("length(geGetEditCellView()~>shapes)")
    print(f"Shape count: {r['result']['output']}")

    # Bounding box
    r = client.execute_skill("geGetEditCellView()~>bBox")
    print(f"Bounding box: {r['result']['output']}")

    # Cell properties
    r = client.execute_skill(
        'mapcar(lambda((p) list(p~>name p~>value)) geGetEditCellView()~>prop)'
    )
    print(f"Properties: {r['result']['output'][:200]}")

    # For layout: list layers used
    if view == "layout":
        r = client.execute_skill(
            'let((layers) layers=nil '
            'foreach(s geGetEditCellView()~>shapes '
            '  when(s~>layerName && !member(s~>layerName layers) '
            '    layers=cons(s~>layerName layers))) '
            'sort(layers nil))'
        )
        print(f"Layers used: {r['result']['output']}")

    # For schematic: list nets
    if view == "schematic":
        r = client.execute_skill("geGetEditCellView()~>nets~>name")
        print(f"Nets: {r['result']['output'][:200]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lib", default="", help="Library (default: current design)")
    parser.add_argument("--cell", default="", help="Cell (default: current design)")
    parser.add_argument("--view", default="layout", help="View name")
    args = parser.parse_args()

    client = BridgeClient()
    if not client.test_connection().get("alive"):
        print("Bridge not running. Run: virtuoso-bridge start")
        return 1

    if args.lib and args.cell:
        read_cellview(client, args.lib, args.cell, args.view)
    else:
        lib, cell, view = client.get_current_design()
        if not lib:
            print("No cellview open. Pass --lib and --cell, or open one in Virtuoso.")
            return 1
        read_cellview(client, lib, cell, view)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
