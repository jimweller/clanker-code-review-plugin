#!/usr/bin/env python3
"""Score a review-deep run against the goeval fixture's truth table.

    python3 live_eval_go.py STATE_DIR

STATE_DIR is a review-deep run's <repo>/.llmtmp/review-deep. The repo root is
STATE_DIR/../.. Unlike live_eval.py, this scores a real Steps 1-4 run rather than a
canned one, and it exists to prove the current one-repo-for-every-arm design leaks
arms into each other's territory. Checks, from fixture-go/truth.json:

1. area defects: each non-cross defect is found by an arm of its own area, citing its
   file within +/-5 lines of its anchor. Cited paths are matched by suffix so an
   absolute path, a path under a temp copy, or a bare repo-relative path all count.
2. cross-component defect: appears in some parts/*-sweep.md, near either of its two
   locations. A component arm sees only one side of it and cannot report it whole.
3. security severity: some arm rates the security defect Critical. The reviewer
   agents' current output format allows only High, Medium, or Low, so this check
   cannot pass until that format changes; it is included anyway, as specified.
4. no marker leak: none of the trap markers appears in parts/*.md, coverage/*,
   parts/raw-*.ndjson, or opencode-db/*.db.
5. no path escape: no tool call recorded in an arm's opencode-db reads or writes
   outside that arm's allowed root. The allowed root is STATE_DIR/arms/<base>.root
   when that file exists (the future one-copy-per-arm design), else the repo root,
   in which case anything under <repo>/.llmtmp/ also counts as outside. Tool inputs
   checked: filePath, path, relative_path (Serena), and glob/grep paths.
6. full coverage: every line of tasks.txt and sweeps.txt (if present) has a matching
   non-empty parts/<label>-<area>-<comp>.md.

Prints every check and a total, and exits 1 when any check fails.
"""
import glob
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = json.load(open(os.path.join(HERE, "fixture-go", "truth.json")))

LABELS = ["openai", "gemini", "claude"]
AREAS = ["security", "architecture", "solid", "correctness", "testing", "ops", "performance", "quality", "data"]
PART_RE = re.compile(r"^(?P<label>" + "|".join(LABELS) + r")-(?P<area>" + "|".join(AREAS) + r")-(?P<comp>.+)\.md$")
BULLET_RE = re.compile(r"^- \*\*(?P<severity>[A-Za-z]+)\*\*\s+`(?P<loc>[^`]+)`(?:\s+`(?P<symbol>[^`]+)`)?\s+(?P<text>.*)$")


def repo_root_of(state_dir):
    return os.path.abspath(os.path.join(state_dir, "..", ".."))


def line_of(repo_root, path, anchor):
    for n, line in enumerate(open(os.path.join(repo_root, path), encoding="utf-8").read().split("\n"), 1):
        if anchor in line:
            return n
    raise SystemExit(f"anchor not found in {path}: {anchor}")


def norm_slashes(p):
    return p.replace("\\", "/").rstrip("/")


def path_matches(cited, relpath):
    cited, relpath = norm_slashes(cited), norm_slashes(relpath)
    return cited == relpath or cited.endswith("/" + relpath)


def parse_loc(loc):
    m = re.search(r":(\d+)(?:-\d+)?$", loc)
    return (loc[: m.start()], int(m.group(1))) if m else (loc, None)


def iter_parts(state_dir):
    for path in sorted(glob.glob(os.path.join(state_dir, "parts", "*.md"))):
        m = PART_RE.match(os.path.basename(path))
        if not m:
            continue
        for raw in open(path, encoding="utf-8", errors="replace"):
            bm = BULLET_RE.match(raw.rstrip("\n"))
            if not bm:
                continue
            loc_path, loc_line = parse_loc(bm.group("loc"))
            yield {"file": path, "label": m.group("label"), "area": m.group("area"), "comp": m.group("comp"),
                   "severity": bm.group("severity"), "path": loc_path, "line": loc_line, "text": bm.group("text")}


def check_area_defect(state_dir, repo_root, defect):
    loc = defect["locations"][0]
    anchor_line = line_of(repo_root, loc["path"], loc["anchor"])
    for f in iter_parts(state_dir):
        if f["area"] == defect["area"] and f["line"] is not None and path_matches(f["path"], loc["path"]) \
                and abs(f["line"] - anchor_line) <= 5:
            return True
    return False


def check_cross_component(state_dir, repo_root, defect):
    anchors = [(loc, line_of(repo_root, loc["path"], loc["anchor"])) for loc in defect["locations"]]
    for f in iter_parts(state_dir):
        if f["comp"] != "sweep" or f["line"] is None:
            continue
        for loc, anchor_line in anchors:
            if path_matches(f["path"], loc["path"]) and abs(f["line"] - anchor_line) <= 5:
                return True
    return False


def check_security_critical(state_dir, repo_root, defect):
    loc = defect["locations"][0]
    anchor_line = line_of(repo_root, loc["path"], loc["anchor"])
    for f in iter_parts(state_dir):
        if f["severity"] == "Critical" and f["line"] is not None and path_matches(f["path"], loc["path"]) \
                and abs(f["line"] - anchor_line) <= 5:
            return True
    return False


def find_marker_leaks(state_dir, markers):
    leaked = []
    patterns = [os.path.join(state_dir, "parts", "*.md"), os.path.join(state_dir, "coverage", "*"),
                os.path.join(state_dir, "parts", "raw-*.ndjson"), os.path.join(state_dir, "opencode-db", "*.db")]
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if not os.path.isfile(path):
                continue
            data = open(path, "rb").read()
            for marker in markers:
                if marker.encode() in data:
                    leaked.append((path, marker))
    return leaked


def allowed_root_for(state_dir, base, repo_root):
    root_file = os.path.join(state_dir, "arms", f"{base}.root")
    if os.path.exists(root_file):
        return open(root_file, encoding="utf-8").read().strip(), None
    return repo_root, ".llmtmp"


def tool_call_paths(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute("select data from part where json_extract(data,'$.type')='tool'").fetchall()
    finally:
        con.close()
    out = []
    for (data,) in rows:
        rec = json.loads(data)
        inp = (rec.get("state") or {}).get("input") or {}
        for key in ("filePath", "path", "relative_path"):
            if inp.get(key):
                out.append((rec.get("tool", ""), key, inp[key]))
    return out


def is_outside(candidate, allowed_root, extra_exclude):
    if not os.path.isabs(candidate):
        candidate = os.path.join(allowed_root, candidate)
    candidate = os.path.normpath(candidate)
    allowed_root = os.path.normpath(allowed_root)
    try:
        rel = os.path.relpath(candidate, allowed_root)
    except ValueError:
        return True
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return True
    return bool(extra_exclude) and (rel == extra_exclude or rel.startswith(extra_exclude + os.sep))


def find_outside_paths(state_dir, repo_root):
    offenses = []
    for db_path in sorted(glob.glob(os.path.join(state_dir, "opencode-db", "*.db"))):
        base = os.path.basename(db_path)[: -len(".db")]
        allowed_root, extra_exclude = allowed_root_for(state_dir, base, repo_root)
        for tool, key, value in tool_call_paths(db_path):
            if is_outside(value, allowed_root, extra_exclude):
                offenses.append((base, tool, key, value))
    return offenses


def find_missing_parts(state_dir):
    missing = []
    for fname in ("tasks.txt", "sweeps.txt"):
        path = os.path.join(state_dir, fname)
        if not os.path.exists(path):
            if fname == "tasks.txt":
                missing.append(f"{fname} not found in {state_dir}")
            continue
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            label, _model, area, comp = line.split()
            part = os.path.join(state_dir, "parts", f"{label}-{area}-{comp}.md")
            if not (os.path.exists(part) and os.path.getsize(part) > 0):
                missing.append(f"{label} {area} {comp}: {part}")
    return missing


def score(state_dir):
    repo_root = repo_root_of(state_dir)
    checks = []
    for d in TRUTH["defects"]:
        if d["cross_component"]:
            continue
        checks.append((f"area defect found ({d['id']}): {d['locations'][0]['path']}", check_area_defect(state_dir, repo_root, d)))
    (cross,) = [d for d in TRUTH["defects"] if d["cross_component"]]
    checks.append((f"cross-component defect in a sweep ({cross['id']})", check_cross_component(state_dir, repo_root, cross)))
    security = next(d for d in TRUTH["defects"] if d["id"] == "security")
    checks.append(("security defect rated Critical by some arm", check_security_critical(state_dir, repo_root, security)))
    markers = [m["marker"] for m in TRUTH["markers"]]
    leaked = find_marker_leaks(state_dir, markers)
    checks.append((f"no trap marker leaked ({len(markers)} markers)", not leaked))
    outside = find_outside_paths(state_dir, repo_root)
    checks.append(("no tool call path escapes its arm's allowed root", not outside))
    missing = find_missing_parts(state_dir)
    checks.append(("every tasks.txt/sweeps.txt line has a non-empty parts file", not missing))
    return checks, leaked, outside, missing


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.split("\n\n")[1])
    state_dir = os.path.abspath(sys.argv[1])
    checks, leaked, outside, missing = score(state_dir)
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    for path, marker in leaked:
        print(f"      marker {marker} found in {path}")
    for base, tool, key, value in outside:
        print(f"      {base}: {tool} {key}={value} escapes its allowed root")
    for m in missing:
        print(f"      missing or empty: {m}")
    passed = sum(ok for _, ok in checks)
    print(f"{passed} of {len(checks)} checks pass")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
