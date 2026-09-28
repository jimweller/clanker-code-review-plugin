"""Integration check: build the real goeval fixture, synthesize a STATE_DIR that
answers every real truth.json defect correctly, and confirm live_eval_go.score()
passes every check except the one the current agent output format can never satisfy.

This is what proves truth.json's anchors are real and resolvable, not just that the
scorer's helpers work in isolation (the other test_*.py files in this directory).
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

EVALS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, EVALS_DIR)
import live_eval_go  # noqa: E402
from fixture_go_helpers import make_db  # noqa: E402

# evals/pipeline.py already does `import build` for the harbor fixture's build.py, so
# the bare name "build" may already be cached in sys.modules pointing at that other
# file. Load fixture-go/build.py by path under its own name instead of risking that
# collision.
_spec = importlib.util.spec_from_file_location("fixture_go_build", os.path.join(EVALS_DIR, "fixture-go", "build.py"))
build_go = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_go)

TRUTH = json.load(open(os.path.join(EVALS_DIR, "fixture-go", "truth.json")))


def write_bullet(part_path, area, severity, path, line, text):
    heading = f"## {area.title()}\n\n"
    if part_path.exists():
        part_path.write_text(part_path.read_text() + f"- **{severity}** `{path}:{line}` {text}\n")
    else:
        part_path.write_text(heading + f"- **{severity}** `{path}:{line}` {text}\n")


def test_a_fully_answered_run_passes_every_check_but_the_critical_severity_one(tmp_path):
    repo, state_dir, _commit = build_go.build(str(tmp_path))
    state_dir = Path(state_dir)
    for d in ("parts", "coverage", "opencode-db"):
        (state_dir / d).mkdir(parents=True)

    tasks = []
    for defect in TRUTH["defects"]:
        area = defect["area"]
        loc = defect["locations"][0]
        anchor_line = live_eval_go.line_of(repo, loc["path"], loc["anchor"])
        comp = "sweep" if defect["cross_component"] else "c01"
        part = state_dir / "parts" / f"claude-{area}-{comp}.md"
        write_bullet(part, area, "High", loc["path"], anchor_line, f"{defect['id']} finding, real and cited.")
        if defect["cross_component"]:
            second = defect["locations"][1]
            second_line = live_eval_go.line_of(repo, second["path"], second["anchor"])
            write_bullet(part, area, "High", second["path"], second_line, f"{defect['id']} finding, other side.")
        tasks.append(f"claude az-anthropic/claude-opus-5-5 {area} {comp}")
        make_db(state_dir / "opencode-db" / f"claude-{area}-{comp}.db",
                [json.dumps({"type": "tool", "tool": "read", "state": {"input": {"filePath": os.path.join(repo, loc["path"])}}})])

    security_part = state_dir / "parts" / "claude-security-c01.md"
    security_loc = next(d for d in TRUTH["defects"] if d["id"] == "security")["locations"][0]
    security_line = live_eval_go.line_of(repo, security_loc["path"], security_loc["anchor"])

    (state_dir / "tasks.txt").write_text("\n".join(tasks) + "\n")

    checks, leaked, outside, missing = live_eval_go.score(str(state_dir))
    for name, ok in checks:
        if "rated Critical" in name:
            assert not ok, "expected the Critical check to fail under the High/Medium/Low agent format"
        else:
            assert ok, f"expected to pass: {name}"
    assert leaked == []
    assert outside == []
    assert missing == []

    # Now show the Critical check can pass once an arm's output actually says Critical.
    write_bullet(security_part, "security", "Critical", security_loc["path"], security_line, "escalated by a second arm.")
    checks, _, _, _ = live_eval_go.score(str(state_dir))
    assert all(ok for _, ok in checks), dict(checks)
