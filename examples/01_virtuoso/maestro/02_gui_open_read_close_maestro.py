#!/usr/bin/env python3
"""Open a maestro GUI window, read config, then close the window.

Edit LIB and CELL below.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import read_config

LIB  = "PLAYGROUND_AMP"
CELL = "TB_AMP_5T_D2S_DC_AC"


def main() -> int:
    client = VirtuosoClient.from_env()

    # GUI open
    r = client.execute_skill(f'''
let((before after session)
  before = maeGetSessions()
  deOpenCellView("{LIB}" "{CELL}" "maestro" "maestro" nil "r")
  after = maeGetSessions()
  session = nil
  foreach(s after unless(member(s before) session = s))
  printf("[%s MaestroOpen] %s/%s  session=%s\\n" nth(2 parseString(getCurrentTime())) "{LIB}" "{CELL}" session)
  session
)
''')
    ses = (r.output or "").strip('"')
    if not ses or ses in ("nil", "t"):
        print(f"MaestroOpen failed for {LIB}/{CELL}")
        return 1

    for key, (skill_expr, raw) in read_config(client, ses).items():
        print(f"[{key}] {skill_expr}")
        print(raw)

    # GUI close
    client.execute_skill(f'''
foreach(win hiGetWindowList()
  let((n) n = hiGetWindowName(win)
    when(and(n rexMatchp("{CELL}" n) rexMatchp("maestro" n))
      errset(hiCloseWindow(win))
      let((form) form = hiGetCurrentForm()
        when(form errset(hiFormCancel(form)))
      )
    )
  )
)
printf("[%s MaestroClose] %s/%s closed\\n" nth(2 parseString(getCurrentTime())) "{LIB}" "{CELL}")
''')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
