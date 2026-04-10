"""X11 dialog detection and dismissal via SSH (bypasses SKILL channel).

When a modal dialog blocks the Virtuoso CIW event loop, all execute_skill()
calls time out.  This module uses direct SSH + remote Python2/Xlib to find
and dismiss those dialogs without touching the SKILL channel.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
from pathlib import Path
from typing import Any

from virtuoso_bridge.transport.ssh import SSHRunner

logger = logging.getLogger(__name__)

_HELPER_SCRIPT = Path(__file__).parent.parent / "resources" / "x11_dismiss_dialog.py"


def _get_display(display: str | None) -> str | None:
    """Resolve display: explicit arg > VB_DISPLAY env var > auto-detect (None)."""
    if display:
        return display
    return os.getenv("VB_DISPLAY") or None


def _ensure_helper(runner: SSHRunner, user: str) -> str:
    """Upload the helper script if not already present."""
    remote_path = f"/tmp/virtuoso_bridge_{user}/x11_dismiss_dialog.py"
    remote_dir = str(Path(remote_path).parent)
    runner.run_command(f"mkdir -p {remote_dir}")
    runner.upload(_HELPER_SCRIPT, remote_path)
    return remote_path


def find_dialogs(
    runner: SSHRunner,
    user: str,
    display: str | None = None,
) -> list[dict[str, Any]]:
    """Find blocking dialog windows on the remote X11 display.

    Returns list of dicts: [{"window_id", "title", "x", "y", "w", "h"}, ...]
    """
    script = _ensure_helper(runner, user)
    resolved = _get_display(display)
    cmd = f"python2 {script}"
    if resolved:
        cmd += f" {resolved}"
    result = runner.run_command(cmd, timeout=15)
    return _parse_output(result.stdout)


def dismiss_dialogs(
    runner: SSHRunner,
    user: str,
    display: str | None = None,
) -> list[dict[str, Any]]:
    """Find and dismiss all blocking dialog windows.

    Returns list of result dicts (found dialogs + dismissal results).
    """
    script = _ensure_helper(runner, user)
    resolved = _get_display(display)
    env_prefix = ""
    for key in ("VB_SAVE_DIALOG_POLICY", "VB_SAVE_DIALOG_CONTEXT"):
        val = os.getenv(key)
        if val is not None and val != "":
            env_prefix += f"{key}={shlex.quote(val)} "

    cmd = f"{env_prefix}python2 {script} --dismiss"
    if resolved:
        cmd += f" {resolved}"
    result = runner.run_command(cmd, timeout=15)
    return _parse_output(result.stdout)


def _parse_output(stdout: str) -> list[dict[str, Any]]:
    """Parse JSON-lines output from the helper script."""
    results = []
    for line in (stdout or "").strip().splitlines():
        line = line.strip()
        if line:
            try:
                results.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                logger.debug("Non-JSON line from helper: %s", line)
    return results
