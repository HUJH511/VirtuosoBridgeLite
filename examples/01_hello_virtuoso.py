#!/usr/bin/env python3
"""Connect to Virtuoso and run basic SKILL commands.

Prerequisites:
  - .env configured with VB_REMOTE_HOST
  - virtuoso-bridge start

Usage:
    python examples/01_hello_virtuoso.py
"""

from virtuoso_bridge import BridgeClient


def main() -> int:
    client = BridgeClient()

    # 1. Test connection
    alive = client.test_connection()
    print(f"Connection: {'alive' if alive.get('alive') else 'dead'}")
    if not alive.get("alive"):
        print("Start the bridge first: virtuoso-bridge start")
        return 1

    # 2. Simple arithmetic
    r = client.execute_skill("1 + 2")
    print(f"1 + 2 = {r['result']['output']}")

    # 3. Query Virtuoso state
    r = client.execute_skill("hiGetCurrentWindow()")
    print(f"Current window: {r['result']['output']}")

    # 4. Get current design (if any cellview is open)
    lib, cell, view = client.get_current_design()
    if lib:
        print(f"Current design: {lib}/{cell}/{view}")
    else:
        print("No cellview open")

    # 5. Print to CIW
    client.ciw_print("Hello from virtuoso-bridge-lite!")
    print("Sent message to CIW")

    # 6. List libraries
    r = client.execute_skill("ddGetLibList()~>name")
    print(f"Libraries: {r['result']['output'][:120]}...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
