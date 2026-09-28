"""find_outside_paths: no tool call in an arm's opencode-db reads or writes outside
that arm's allowed root. Fallback root is the repo root with .llmtmp/ excluded;
STATE_DIR/arms/<base>.root, when present, narrows the allowed root to that path."""
import json

import live_eval_go  # conftest.py puts evals/ on sys.path before this module loads
from fixture_go_helpers import make_db


def test_pass_when_every_tool_call_stays_inside_the_repo(state):
    db = state["state"] / "opencode-db" / "claude-security-c01.db"
    make_db(db, [json.dumps({"type": "tool", "tool": "read",
                             "state": {"input": {"filePath": str(state["repo"] / "warehouse" / "api.go")}}})])
    offenses = live_eval_go.find_outside_paths(str(state["state"]), str(state["repo"]))
    assert offenses == []


def test_fail_when_a_tool_reads_under_the_repos_llmtmp_dir(state):
    db = state["state"] / "opencode-db" / "claude-security-c01.db"
    stray = state["repo"] / ".llmtmp" / "review-deep-previous" / "parts" / "claude-security-c01.md"
    make_db(db, [json.dumps({"type": "tool", "tool": "read", "state": {"input": {"filePath": str(stray)}}})])
    offenses = live_eval_go.find_outside_paths(str(state["state"]), str(state["repo"]))
    assert len(offenses) == 1 and offenses[0][0] == "claude-security-c01"


def test_fail_when_a_tool_path_is_outside_the_repo_entirely(state, tmp_path):
    db = state["state"] / "opencode-db" / "claude-security-c01.db"
    decoy = tmp_path / "decoy-sibling" / "types.go"
    make_db(db, [json.dumps({"type": "tool", "tool": "read", "state": {"input": {"filePath": str(decoy)}}})])
    offenses = live_eval_go.find_outside_paths(str(state["state"]), str(state["repo"]))
    assert offenses


def test_fail_when_a_relative_glob_scope_points_at_llmtmp(state):
    db = state["state"] / "opencode-db" / "claude-security-c01.db"
    make_db(db, [json.dumps({"type": "tool", "tool": "glob",
                             "state": {"input": {"path": ".llmtmp/review-deep-previous/parts", "pattern": "*"}}})])
    offenses = live_eval_go.find_outside_paths(str(state["state"]), str(state["repo"]))
    assert offenses


def test_pass_when_an_arms_root_file_narrows_the_allowed_root(state, tmp_path):
    arm_root = tmp_path / "arm-copy"
    (arm_root / "warehouse").mkdir(parents=True)
    (state["state"] / "arms").mkdir()
    (state["state"] / "arms" / "claude-security-c01.root").write_text(str(arm_root))
    db = state["state"] / "opencode-db" / "claude-security-c01.db"
    make_db(db, [json.dumps({"type": "tool", "tool": "read",
                             "state": {"input": {"filePath": str(arm_root / "warehouse" / "api.go")}}})])
    offenses = live_eval_go.find_outside_paths(str(state["state"]), str(state["repo"]))
    assert offenses == []


def test_fail_when_an_arms_root_file_is_present_but_the_tool_reads_the_shared_repo(state, tmp_path):
    arm_root = tmp_path / "arm-copy"
    arm_root.mkdir()
    (state["state"] / "arms").mkdir()
    (state["state"] / "arms" / "claude-security-c01.root").write_text(str(arm_root))
    db = state["state"] / "opencode-db" / "claude-security-c01.db"
    make_db(db, [json.dumps({"type": "tool", "tool": "read",
                             "state": {"input": {"filePath": str(state["repo"] / "warehouse" / "api.go")}}})])
    offenses = live_eval_go.find_outside_paths(str(state["state"]), str(state["repo"]))
    assert offenses
