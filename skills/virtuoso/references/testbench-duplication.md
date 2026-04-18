# Duplicate a Testbench Cell (Same or Different Library)

Workflow for cloning an existing testbench — schematic + config + maestro —
to a new cell name, **same library or a different one**. The mechanism is
file-level copy plus a couple of targeted text patches. Both same-lib and
cross-lib cases share the same flow; the only extra work for cross-lib is
one additional substitution (the library name).

## Why not rebuild from scratch

If you already have a working TB, **do not** rebuild it via
`schematic.edit()` + `maeCreateTest` / `maeSetAnalysis` / `maeAddOutput`.
That path silently drops fidelity:

- Plot window layout, spec ordering, spec targets
- Save-all / save-node preferences per analysis
- Fine-grained CDF instance params that weren't explicitly scripted
- Maestro corner definitions, per-corner variable overrides
- Output expressions (`dB20(VF(x)/VF(y))`, `phaseMargin(...)`, etc.)

`dbCopyCellView` + shell `cp` + targeted sed preserves the sdb verbatim.
Start there. Only reach for "rebuild" when the source is unrecoverable.

## The three views, three copy mechanisms

| View | Mechanism | Why |
|------|-----------|-----|
| `schematic` | `dbCopyCellView` | Standard DFII cellview |
| `config` | shell `cp -r` + text patch | CDB, not db; `dbCopyCellView` returns nil |
| `maestro` | shell `cp -r` + text patch | SDB (XML), not db; `dbCopyCellView` returns nil |

`dbCopyCellView` on config or maestro **silently returns nil** — no error
raised. You must shell-cp those directories.

## Procedure

Parameters used below:

```python
SRC_LIB = "PLAYGROUND_AGENTS"; SRC = "_TB_CMP_PNOISE"
DST_LIB = "PLAYGROUND_LLM";    DST = "_TB_CMP_PNOISE_COPY"
# Same-lib case: DST_LIB == SRC_LIB
```

### 1. Sanity check

```python
r = client.execute_skill(f'ddGetObj("{SRC_LIB}" "{SRC}")~>views~>name')
# e.g. ("maestro" "schematic" "config")

r = client.execute_skill(f'if(ddGetObj("{DST_LIB}") "EXISTS" "missing")')
assert r.output.strip('"') == "EXISTS"

r = client.execute_skill(f'if(ddGetObj("{DST_LIB}" "{DST}") "EXISTS" "free")')
assert r.output.strip('"') == "free"
```

### 2. Copy schematic via SKILL

```python
r = client.execute_skill(f'''
let((src new)
  src = dbOpenCellViewByType("{SRC_LIB}" "{SRC}" "schematic" nil "r")
  new = dbCopyCellView(src "{DST_LIB}" "{DST}" "schematic" nil)
  dbClose(src)
  when(new dbClose(new))
  if(new "OK" "FAIL"))
''')
assert r.output.strip('"') == "OK"
```

This creates `{DST_LIB}/{DST}/schematic/` on the filesystem and registers
the new cell in the destination library.

### 3. Copy config + maestro directories via shell

```python
src = f"/path/to/{SRC_LIB}/{SRC}"   # from ddGetObj(SRC_LIB, SRC)~>readPath
dst = f"/path/to/{DST_LIB}/{DST}"   # from ddGetObj(DST_LIB)~>readPath + "/" + DST
client.run_shell_command(
    f'cp -r {src}/config {dst}/config && cp -r {src}/maestro {dst}/maestro')
```

### 4. Refresh the destination library index

```python
client.execute_skill(f'ddSyncWriteLock(ddGetObj("{DST_LIB}"))')

r = client.execute_skill(f'ddGetObj("{DST_LIB}" "{DST}")~>views~>name')
# ("maestro" "schematic" "config")
```

Skip this and Library Manager won't show the new views until Virtuoso
restarts.

### 5. Patch `config/expand.cfg`

The config file has exactly two refs to the old cell (+ the old lib, if
cross-lib):

```
config {SRC};
design {SRC_LIB}.{SRC}:schematic;
```

Use `sed -i` in one shot — this is the recommended path. Pick a delimiter
(`#` below) that doesn't appear in either library or cell name to avoid
escape noise:

```python
client.run_shell_command(
    f"sed -i "
    f"-e 's#config {SRC};#config {DST};#g' "
    f"-e 's#design {SRC_LIB}\\.{SRC}:schematic;#design {DST_LIB}.{DST}:schematic;#g' "
    f"{dst}/config/expand.cfg"
)
```

For same-lib (`DST_LIB == SRC_LIB`), the second substitution still works
— it just swaps in the identical lib name.

### 6. Patch `maestro/maestro.sdb`

Two substitutions:

1. **Cell name everywhere**: `{SRC}` → `{DST}`, ~10-30 occurrences
   (authoritative design bindings + historical breadcrumb paths).
2. **Library name in XML bindings only** (cross-lib only):
   `<value>{SRC_LIB}</value>` → `<value>{DST_LIB}</value>`.

Crucial: for #2, substitute **only inside `<value>` tags**, not raw
`{SRC_LIB}` strings. The sdb also holds references to other libraries as
sub-cells (e.g. `<value>Async_SAR_11b</value>`), and URL-path strings
that may contain `{SRC_LIB}` as a path segment. You don't want to touch
those.

#### Method A (recommended): remote `sed`

For both substitutions — simple literal replacement, idempotent enough
for a one-shot clone:

```python
# Substitution 1: cell name (runs on all occurrences)
# Substitution 2: lib name — ONLY in <value> tags
client.run_shell_command(
    f"sed -i "
    f"-e 's#{SRC}#{DST}#g' "
    f"-e 's#<value>{SRC_LIB}</value>#<value>{DST_LIB}</value>#g' "
    f"{dst}/maestro/maestro.sdb"
)
```

Zero scp, zero local artifacts. Works for this case because neither cell
name nor lib name contains `!`, `/`, `#`, or any other csh-hostile char.

**If you need to re-run**, sed will turn `{DST}` into `{DST}_2_suffix`
style concatenations. For one-shot duplication that's fine. For
idempotent flows, see Method B.

#### Method B: upload a Python patcher, run it remotely

Use when you need Perl-style regex (negative lookahead for idempotency,
backreferences, multiline) that basic POSIX sed can't express:

```python
patcher = r'''
import re, sys
p, src, dst, src_lib, dst_lib = sys.argv[1:6]
t = open(p, "r", encoding="utf-8").read()
t = re.sub(rf"{re.escape(src)}(?!{re.escape(dst[len(src):])})", dst, t)   # idempotent
if src_lib != dst_lib:
    t = t.replace(f"<value>{src_lib}</value>", f"<value>{dst_lib}</value>")
open(p, "w", encoding="utf-8").write(t)
'''
client.upload_text(patcher, "/tmp/patch_sdb.py")
client.run_shell_command(
    f"python3 /tmp/patch_sdb.py {dst}/maestro/maestro.sdb "
    f"'{SRC}' '{DST}' '{SRC_LIB}' '{DST_LIB}'"
)
```

Small script upload + one shell exec. Python regex is unrestricted.

#### Method C (last resort): download-edit-upload

Only when you need **local verifiability**: count substitutions before
committing, produce a diff, or keep a local backup. Has real overhead
(two scp trips for a potentially multi-MB sdb) and leaves local
artifacts.

```python
import re, shutil
client.download_file(f"{dst}/maestro/maestro.sdb", "tmp/sdb.edit")
text = open("tmp/sdb.edit", "r", encoding="utf-8").read()
before = text.count(SRC)
new = re.sub(rf'{re.escape(SRC)}(?!_COPY)', DST, text)
if SRC_LIB != DST_LIB:
    new = new.replace(f"<value>{SRC_LIB}</value>",
                      f"<value>{DST_LIB}</value>")
print(f"cell subs: {before} → {new.count(DST)} (orphans: "
      f"{len(re.findall(rf'{re.escape(SRC)}(?!_COPY)', new))})")
shutil.copy("tmp/sdb.edit", "tmp/maestro.sdb")   # rename before upload!
open("tmp/maestro.sdb", "w", encoding="utf-8", newline="").write(new)
client.upload_file("tmp/maestro.sdb", f"{dst}/maestro/maestro.sdb")
```

### 7. Verify

```python
from virtuoso_bridge.virtuoso.maestro import open_session, close_session

sess = open_session(client, DST_LIB, DST)   # background, no GUI
r = client.execute_skill(f'maeGetSetup(?session "{sess}")')
# Lists test names, session opens without errors
close_session(client, sess)
```

Or eyeball the design binding in the sdb:

```python
# Should show DST and DST_LIB as siblings under <option>cell / <option>lib
client.run_shell_command(
    f"grep -A1 '<option>cell\\|<option>lib' {dst}/maestro/maestro.sdb | head -20"
)
```

Or open the GUI:

```python
from virtuoso_bridge.virtuoso.maestro import open_gui_session
open_gui_session(client, DST_LIB, DST)
```

Confirm the design-binding row shows `{DST_LIB}/{DST}/config`.

## Gotchas

### `dbCopyCellView` silently returns nil for non-db views

No exception, no log message — just a quiet nil. Always check the
return value for `schematic`/`symbol` views, and don't bother calling it
at all for `config`/`maestro`.

### csh eats `!` in `run_shell_command`

`client.run_shell_command(cmd)` is implemented as `csh("...")` in SKILL.
csh treats `!` as history expansion and silently mangles any command
containing it before executing. Perl's negative-lookahead (`(?!foo)`)
will not work as written.

Avoid `!` entirely — either rephrase without lookahead (plain sed), or
upload a patcher script (Method B) so the shell never sees the regex
text.

### `upload_file` preserves the **source** basename

`client.upload_file(local, remote)` tars the file at `local`, extracts
into `dirname(remote)`, and keeps the source basename. If your local
file is named `sdb_edit.xml` but the target is `maestro.sdb`, you'll
end up with `sdb_edit.xml` in the target directory, not the intended
`maestro.sdb`.

**Rename locally first:**

```python
import shutil
shutil.copy("tmp/sdb.edit", "tmp/maestro.sdb")
client.upload_file("tmp/maestro.sdb", f"{dst}/maestro/maestro.sdb")
```

### `run_shell_command` stdout is not returned to Python

It returns `t` (success) or `nil` (fail) — stdout goes to the CIW log,
not back to Python. For debug / verification, either:

- Redirect to a file and `download_file` it
- Read the file via SKILL `infile` / `gets` / `close`
- Re-probe filesystem state via `getDirFiles` / `isFile` / `ddGetObj`

### Stale history paths in the new sdb are harmless

After substitution, URL-path fragments like
`/path/to/OLD_LIB/NEW_CELL/maestro/results/maestro/Interactive.N.log`
may point at directories that never existed. This is fine. Cadence
rediscovers histories by walking `{cellview_path}/results/maestro/` at
open time; the breadcrumb paths in the sdb are informational, not
load-bearing. New simulations write to the correct `{DST_LIB}/{DST}/`
tree automatically.

### Cross-lib: other-lib references must survive

The sdb may reference cells from libraries *other* than `SRC_LIB` — e.g.
sub-cells pulled in by the testbench (`<value>Async_SAR_11b</value>`,
`<value>tsmcN28</value>`). Your lib substitution must scope to
`<value>{SRC_LIB}</value>` **exactly**, not a global
`{SRC_LIB}` replace, or you'll mis-point sub-cells.

### Same-lib cloning only needs substitution #1

Skip the `<value>SRC_LIB</value>` replacement when `DST_LIB == SRC_LIB`.
The library name is already correct after file copy.

## Reference substitution counts

Typical cross-lib duplication of a testbench with ~6 analyses + ~10
historical runs:

| File | `{SRC}` → `{DST}` subs | `<value>{SRC_LIB}</value>` → `<value>{DST_LIB}</value>` subs |
|------|------------------------|------------------------------------------------------------|
| `expand.cfg` | 2 | 1 (inside the `design` line — handled together in sed) |
| `maestro.sdb` | 10-30 | 6-12 (one per test's `<option>lib` binding + aux) |

If counts are dramatically higher (100+), the sdb likely contains
Monte-Carlo or sweep bloat — still safe to substitute wholesale, just
confirms you want the full replace.
