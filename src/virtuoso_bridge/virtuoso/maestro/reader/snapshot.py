"""Top-level aggregator: ``snapshot()``.

Two modes via ``output_root=``:

- ``None`` (default) → SKILL-only sparse dict (~150ms, 2 round-trips).
- path             → also writes the disk dump (raw + YAML-filtered
                     XMLs, raw SKILL section dump, newest run's
                     artifacts) and sets ``output_dir`` on the dict.

Three non-overlapping tracks on disk: ``state_from_skill.txt`` (raw
SKILL alists verbatim) / ``state_from_sdb.xml`` (YAML-filtered sdb) /
``state_from_active_state.xml`` (YAML-filtered active.state).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from virtuoso_bridge import VirtuosoClient

from ._parse_sdb import _sdb_active_tests, filter_active_state_xml, filter_sdb_xml
from .bundle import full_bundle
from .session import _fetch_window_state, natural_sort_histories


# ---------------------------------------------------------------------------
# Path builders + disk-dump primitives
# ---------------------------------------------------------------------------

def latest_run_paths(*, lib_path: str, scratch_root: str,
                      lib: str, cell: str, view: str,
                      history: str, test: str) -> dict:
    """Canonical remote paths for the newest history's run.

    Keys always present (``""`` when not derivable):

    * ``log`` — ``{lib_path}/{cell}/{view}/results/maestro/{history}.log``
    * ``scs`` — ``{scratch_root}/{lib}/{cell}/{view}/results/maestro/
                {history}/1/{test}/netlist/input.scs``
    * ``out`` — same scratch base, ``/psf/spectre.out``

    The ``/1/`` is the run index (``1`` for single-point, per-corner
    for sweeps); we care only about the primary run.
    """
    if not (history and lib_path):
        return {"log": "", "scs": "", "out": ""}
    log = f"{lib_path}/{cell}/{view}/results/maestro/{history}.log"
    if not (scratch_root and test):
        return {"log": log, "scs": "", "out": ""}
    scr = f"{scratch_root}/{lib}/{cell}/{view}/results/maestro/{history}/1/{test}"
    return {"log": log,
            "scs": f"{scr}/netlist/input.scs",
            "out": f"{scr}/psf/spectre.out"}


def _scp(client: VirtuosoClient, remote: str, local: Path) -> bool:
    """scp ``remote`` → ``local``; swallow errors.  ``True`` on success."""
    if not remote:
        return False
    try:
        client.download_file(remote, str(local))
    except Exception:
        return False
    return local.exists()


def _filter_to(local_raw: Path, target: Path, filter_fn) -> None:
    """Read ``local_raw`` → ``filter_fn(xml)`` → ``target``.  No-op if
    raw missing or filter returns empty."""
    if not local_raw.exists():
        return
    try:
        filt = filter_fn(local_raw.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return
    if filt:
        target.write_text(filt, encoding="utf-8")


def _dump_setup_xmls(client: VirtuosoClient, snap_dir: Path,
                     lib_path: str, cell: str, view: str) -> None:
    """scp + filter ``maestro.sdb`` and ``active.state``.  The
    active.state filter reads sdb's ``<active><tests>`` to drop
    Cadence tombstones (removed-test state the GUI doesn't clean up)."""
    if not lib_path:
        return
    local_sdb = snap_dir / "maestro.sdb"
    valid_tests: set[str] = set()
    if _scp(client, f"{lib_path}/{cell}/{view}/{view}.sdb", local_sdb):
        _filter_to(local_sdb, snap_dir / "state_from_sdb.xml", filter_sdb_xml)
        try:
            valid_tests = _sdb_active_tests(
                local_sdb.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    local_state = snap_dir / "active.state"
    if _scp(client, f"{lib_path}/{cell}/{view}/active.state", local_state):
        _filter_to(local_state, snap_dir / "state_from_active_state.xml",
                   lambda x: filter_active_state_xml(
                       x, valid_test_names=valid_tests or None))


def _dump_skill_text(snap_dir: Path, sections: list[tuple[str, str]]) -> None:
    """Write ``state_from_skill.txt`` — raw SKILL outputs, one per
    ``[label]`` section, verbatim.  No alist→dict parsing."""
    if not sections:
        return
    text = "\n".join(
        part
        for label, raw in sections
        for part in (f"[{label}]", (raw or "").rstrip(), "")
    ).rstrip() + "\n"
    (snap_dir / "state_from_skill.txt").write_text(text, encoding="utf-8")


def _dump_run_artifacts(client: VirtuosoClient, snap_dir: Path,
                         history: str, paths: dict) -> None:
    """scp the newest run's ``.log`` / ``input.scs`` / ``spectre.out``
    into ``snap_dir/<history>/``.  Each scp is best-effort."""
    if not paths.get("log"):
        return
    hist_dir = snap_dir / history
    hist_dir.mkdir(parents=True, exist_ok=True)
    _scp(client, paths["log"], hist_dir / f"{history}.log")
    if paths.get("scs"):
        _scp(client, paths["scs"], hist_dir / "input.scs")
    if paths.get("out"):
        _scp(client, paths["out"], hist_dir / "spectre.out")


def _dump_to_dir(client: VirtuosoClient, *, bundle: dict, lib: str, cell: str,
                 view: str, sess: str, latest_history: str,
                 output_root: str) -> Path:
    """Orchestrate the 3 disk tracks → return the snapshot directory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_dir = Path(output_root) / f"{ts}__{lib}__{cell}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    lib_path = bundle.get("lib_path") or ""
    _dump_setup_xmls(client, snap_dir, lib_path, cell, view)
    _dump_skill_text(snap_dir, bundle.get("raw_sections") or [])
    _dump_run_artifacts(
        client, snap_dir, latest_history,
        latest_run_paths(lib_path=lib_path,
                         scratch_root=bundle.get("scratch_root") or "",
                         lib=lib, cell=cell, view=view,
                         history=latest_history, test=bundle.get("test") or ""),
    )
    return snap_dir


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def snapshot(client: VirtuosoClient, *,
             output_root: str | None = None) -> dict:
    """Snapshot the focused maestro session.

    ``output_root=None`` (default) → SKILL-only sparse dict
    (~150ms, 2 SKILL round-trips, 0 scp).
    ``output_root="..."`` → also writes the disk dump to
    ``{output_root}/{YYYYMMDD_HHMMSS}__{lib}__{cell}/`` (raw + filtered
    XMLs, ``state_from_skill.txt``, newest-run artifacts) and sets
    ``output_dir`` on the returned dict.

    Returned dict keys: ``session / app / lib / cell / view / mode /
    unsaved / test / enabled_analyses / outputs_count / run_mode /
    job_control / errors_count / scratch_root / lib_path /
    results_base / latest_history / history_list``.

    Setup details (variables / corners / parameters / per-analysis
    settings / env options) are NOT in the dict — pass ``output_root``
    and read the XML / .txt files (the canonical format).
    """
    win  = _fetch_window_state(client)
    sess = win["session"]
    lib, cell = win["lib"], win["cell"]
    view = win["view"] or "maestro"

    bundle = full_bundle(client, sess=sess, lib=lib, cell=cell, view=view) \
             if sess else {}

    lib_path = bundle.get("lib_path") or ""
    history_list = natural_sort_histories(bundle.get("hist_files") or [])
    latest_history = history_list[-1] if history_list else ""

    out: dict = {
        "session":          sess,
        "app":              win["application"],
        "lib":              lib, "cell": cell, "view": view,
        "mode":             win["mode"],
        "unsaved":          win["unsaved"],
        "test":             bundle.get("test", ""),
        "enabled_analyses": bundle.get("analyses") or [],
        "outputs_count":    bundle.get("outputs_count", 0),
        "run_mode":         bundle.get("run_mode", ""),
        "job_control":      bundle.get("job_control", ""),
        "errors_count":     bundle.get("errors_count", 0),
        "scratch_root":     bundle.get("scratch_root") or None,
        "lib_path":         lib_path,
        "results_base":     (f"{lib_path}/{cell}/{view}/results/maestro"
                             if lib_path and cell and view else ""),
        "latest_history":   latest_history,
        "history_list":     history_list,
    }

    if output_root is not None:
        if not sess:
            raise RuntimeError("No focused maestro window.")
        snap_dir = _dump_to_dir(
            client, bundle=bundle, lib=lib, cell=cell, view=view,
            sess=sess, latest_history=latest_history,
            output_root=output_root,
        )
        out["output_dir"] = str(snap_dir)

    return out
