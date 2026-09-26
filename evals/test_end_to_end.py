"""Replay the recorded model answers through every stage and compare with the golden set.

    cd evals && uv run --with pytest pytest -q test_end_to_end.py

No model calls and no cost. A changed prompt fails with "prompt changed" and needs a new recording
(pipeline.py --mode record, then golden.py save). A changed script that alters any output fails the
golden comparison, which is the point: review the difference, then save a new golden set on purpose.

Parametrized over kind: full and clean-diff (base equals the reviewed commit) replay from the same
--cassettes as deep, at zero calls, because every prompt depends only on the checkout content and
the finding text, neither of which changes with kind.

A dirty diff is different: the snapshot commit's checkout carries an uncommitted edit and an
untracked file no clean-kind checkout has, so collate and merge still hit the shared --cassettes
(the finding text is unchanged) but verify, judge, critical, and sibling see different checkout
content and need their own recording, in --cassettes-diff (pipeline.py --mode record --kind diff
--dirty --cassettes cassettes-diff, then golden.py save RUN_DIR --kind diff-dirty). Recorded once
at about $2.95 at list price (34 calls); replays here at zero cost from then on.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
CASSETTES_DIFF = os.path.join(HERE, "cassettes-diff")
sys.path.insert(0, HERE)
import golden  # noqa: E402
import pipeline  # noqa: E402


@pytest.mark.parametrize("kind", ["deep", "full", "diff"])
def test_replay_reproduces_the_golden_run(tmp_path, kind):
    run = pipeline.run(str(tmp_path / "work"), "replay", pipeline.CASSETTES, kind)
    assert golden.diff(run, kind) == []


def test_replay_reproduces_the_dirty_diff_golden_run(tmp_path):
    run = pipeline.run(str(tmp_path / "work"), "replay", CASSETTES_DIFF, "diff", dirty=True)
    assert golden.diff(run, "diff-dirty") == []


def test_findings_issues_verify_and_units_match_across_the_three_kinds(tmp_path):
    runs = {kind: pipeline.run(str(tmp_path / kind), "replay", pipeline.CASSETTES, kind)
            for kind in ("deep", "full", "diff")}
    for rel in ("findings.jsonl", "issues.jsonl", "verify/results.jsonl", "tickets/units.jsonl"):
        contents = {kind: open(os.path.join(d, rel), encoding="utf-8").read() for kind, d in runs.items()}
        assert contents["deep"] == contents["full"] == contents["diff"], f"{rel} differs across kinds"
