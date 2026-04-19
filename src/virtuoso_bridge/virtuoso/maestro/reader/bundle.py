"""Single-round-trip SKILL bundle for ``snapshot()``.

:func:`full_bundle` composes every SKILL probe ``snapshot()`` needs
into one ``let((...) ... list(...))`` expression — the wire-side
cost collapses to one round-trip.

Returns brief-shaped fields (test name, analyses names, output count,
run mode, latest-history info) plus ``raw_sections`` — an ordered
list of ``(label, raw_skill_text)`` tuples for the
``state_from_skill.txt`` dump.  No XML→dict / SKILL alist→dict
parsing — raw text is the canonical format.

Caller extracts ``sess`` / ``lib`` / ``cell`` / ``view`` from the
focused window title via :func:`_fetch_window_state` first — that's
a tiny separate SKILL call.
"""

from __future__ import annotations

from collections import namedtuple

from virtuoso_bridge import VirtuosoClient

from ._parse_skill import _parse_skill_str_list, _tokenize_top_level


# ---------------------------------------------------------------------------
# Shared helpers — SKILL output text wrangling
# ---------------------------------------------------------------------------

def _split_top_level(raw: str, expected: int) -> list[str]:
    """Strip outer parens, tokenize top-level into ``expected`` slots,
    pad with empty strings if the response was truncated.
    """
    body = (raw or "").strip()
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1]
    slots = _tokenize_top_level(
        body,
        include_strings=True, include_atoms=True, include_groups=True,
        max_tokens=expected,
    )
    while len(slots) < expected:
        slots.append("")
    return slots


def _unquote(s: str) -> str:
    s = (s or "").strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return "" if s in ("", "nil") else s


def _unwrap_errset(s: str) -> str:
    """``errset(X)`` returns ``(X)`` on success or ``nil`` on error.
    Strip the outer parens (or return "" on error)."""
    s = (s or "").strip()
    if s in ("", "nil"):
        return ""
    if s.startswith("(") and s.endswith(")"):
        return s[1:-1].strip()
    return s


def _scratch_root_from_run_dir(run_dir: str, lib: str, cell: str, view: str) -> str:
    """Strip ``/{lib}/{cell}/{view}/results/maestro/...`` suffix from
    ``asiGetAnalogRunDir`` output to recover the install prefix."""
    if not (run_dir and lib and cell and view):
        return ""
    marker = f"/{lib}/{cell}/{view}/results/maestro"
    idx = run_dir.find(marker)
    return run_dir[:idx] if idx > 0 else ""


# ---------------------------------------------------------------------------
# Slot table — single source of truth for the SKILL bundle
# ---------------------------------------------------------------------------

# ``name``  — key in the parsed-slot dict.
# ``expr``  — SKILL value expression (references the let-bindings
#             below; ``{sess}``/``{lib}``/etc. are .format()-substituted).
# ``label`` — ``state_from_skill.txt`` section header template (same
#             substitutions).  ``None`` = brief-data-only, no section.
_Slot = namedtuple("_Slot", "name expr label")


# Order MUST match the ``list(...)`` body of the SKILL expression below.
# Adding a slot = add one entry here.  No other code edits needed.
_SLOTS: tuple[_Slot, ...] = (
    _Slot('libpath',     'car(libPath)',                                                'ddGetObj("{lib}")~>readPath'),
    _Slot('tests',       'tests',                                                       'maeGetSetup(?session "{sess}")'),
    _Slot('test',        'test',                                                        None),
    _Slot('enabled',     'enabled',                                                     'maeGetEnabledAnalysis("{test}")'),
    _Slot('analyses',    'mapcar(lambda((a) maeGetAnalysis(test a ?session "{sess}")) enabled)',
                                                                                        None),  # special: one section per ana
    _Slot('env',         'if(test maeGetEnvOption(test ?session "{sess}") nil)',        'maeGetEnvOption("{test}")'),
    _Slot('sim',         'if(test maeGetSimOption(test ?session "{sess}") nil)',        'maeGetSimOption("{test}")'),
    _Slot('outputs',     'outsExpr',                                                    'maeGetTestOutputs("{test}") expanded'),
    _Slot('runmode',     'maeGetCurrentRunMode(?session "{sess}")',                     'maeGetCurrentRunMode(?session "{sess}")'),
    _Slot('jobcontrol',  'maeGetJobControlMode(?session "{sess}")',                     'maeGetJobControlMode(?session "{sess}")'),
    _Slot('runplan',     'errset(maeGetRunPlan(?session "{sess}"))',                    'maeGetRunPlan(?session "{sess}")'),
    _Slot('currhist',    'errset(axlGetCurrentHistory("{sess}"))',                      'axlGetCurrentHistory("{sess}")'),
    _Slot('errors',      'errset(maeGetSimulationMessages(?session "{sess}" ?msgType "error"))',
                                                                                        'maeGetSimulationMessages error'),
    _Slot('warnings',    'errset(maeGetSimulationMessages(?session "{sess}" ?msgType "warning"))',
                                                                                        'maeGetSimulationMessages warning'),
    _Slot('infos',       'errset(maeGetSimulationMessages(?session "{sess}" ?msgType "info"))',
                                                                                        'maeGetSimulationMessages info'),
    _Slot('histfiles',   'if(isDir(histDir) getDirFiles(histDir) nil)',                 'getDirFiles(<results/maestro>)'),
    _Slot('rundir',      'car(runDirOK)',                                               'asiGetAnalogRunDir(asiGetSession("{sess}"))'),
)


def full_bundle(client: VirtuosoClient, *,
                sess: str, lib: str, cell: str, view: str) -> dict:
    """Single SKILL round-trip → brief fields + raw SKILL section dump.

    Returns::

        {"lib_path": str, "test": str, "analyses": [...],
         "outputs_count": int, "run_mode": str, "job_control": str,
         "errors_count": int, "hist_files": [...], "scratch_root": str,
         "raw_sections": [(label, raw_text), ...]}

    ``raw_sections`` is suitable for serializing to
    ``state_from_skill.txt``.  No alist→dict parsing — raw SKILL text
    is preserved verbatim.

    The user's design cellview (config vs schematic) is not fetched —
    no SKILL path returns the unresolved cellview reliably; truth lives
    in ``active.state``'s adeInfo.designInfo (read the filtered XML).
    """
    if not sess:
        return {}

    # SKILL ``let`` bindings shared across slots, plus the ``list(...)``
    # whose body order matches ``_SLOTS``.  Per-slot exprs may reference
    # ``{sess}`` / ``{lib}`` / ``{cell}`` / ``{view}`` — substituted here.
    fmt_skill = {"sess": sess, "lib": lib, "cell": cell, "view": view}
    list_body = "\n    ".join(s.expr.format(**fmt_skill) for s in _SLOTS)
    expr = f'''
let((tests test enabled libPath histDir runDirOK outsExpr)
  tests    = maeGetSetup(?session "{sess}")
  test     = if(tests car(tests) "")
  enabled  = if(test maeGetEnabledAnalysis(test ?session "{sess}") nil)
  libPath  = errset(ddGetObj("{lib}")~>readPath)
  histDir  = strcat(car(libPath) "/{cell}/{view}/results/maestro")
  runDirOK = errset(asiGetAnalogRunDir(asiGetSession("{sess}")))
  outsExpr = if(test
    let((outs result)
      outs = maeGetTestOutputs(test ?session "{sess}")
      result = list()
      foreach(o outs
        result = append1(result
          list(o~>name o~>type o~>signal o~>expression
               o~>plot o~>save o~>evalType o~>yaxisUnit o~>spec)))
      result)
    nil)
  list(
    {list_body}
  ))
'''
    r = client.execute_skill(expr)
    raw = _split_top_level(r.output or "", expected=len(_SLOTS))
    slot = dict(zip((s.name for s in _SLOTS), raw))

    test_name = _unquote(slot["test"])
    enabled = _parse_skill_str_list(_unwrap_errset(slot["enabled"]))

    # Per-analysis raw alist texts — parallel to enabled list, split out
    # so each maeGetAnalysis call gets its own section (vs nested list).
    per_analysis_raw = (_split_top_level(slot["analyses"], expected=len(enabled))
                        if enabled else [])

    # Build raw_sections from the slot table.  ``analyses`` is special:
    # one section per enabled analysis.  Slots with ``label=None``
    # are brief-data-only and don't get a section.
    fmt = {"sess": sess, "lib": lib, "test": test_name}
    sections: list[tuple[str, str]] = []
    for spec in _SLOTS:
        if spec.name == "analyses":
            for ana, ana_raw in zip(enabled, per_analysis_raw):
                sections.append((f'maeGetAnalysis("{test_name}" "{ana}")', ana_raw))
            continue
        if spec.label is None:
            continue
        sections.append((spec.label.format(**fmt), slot[spec.name]))

    # outputs_count: count top-level groups in the expanded outputs slot.
    outputs_count = len(_tokenize_top_level(
        _unwrap_errset(slot["outputs"]),
        include_groups=True, include_strings=False, include_atoms=False,
    ))
    # errors_count: empty messages ("") shouldn't count.
    errors_count = sum(1 for m in _parse_skill_str_list(_unwrap_errset(slot["errors"]))
                       if m.strip())

    return {
        "lib_path":      _unquote(slot["libpath"]),
        "test":          test_name,
        "analyses":      enabled,
        "outputs_count": outputs_count,
        "run_mode":      _unquote(slot["runmode"]),
        "job_control":   _unquote(slot["jobcontrol"]),
        "errors_count":  errors_count,
        "hist_files":    _parse_skill_str_list(_unwrap_errset(slot["histfiles"])),
        "scratch_root":  _scratch_root_from_run_dir(
            _unquote(slot["rundir"]), lib, cell, view),
        "raw_sections":  sections,
    }
