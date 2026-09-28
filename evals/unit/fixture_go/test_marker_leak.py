"""find_marker_leaks: none of the trap markers may appear in parts, coverage, raw
NDJSON, or an arm's opencode-db."""
import json

import live_eval_go  # conftest.py puts evals/ on sys.path before this module loads
from fixture_go_helpers import make_db

MARKER = "EVALGO-TRAP-TEST-1"


def test_pass_when_no_marker_appears_anywhere(state):
    (state["state"] / "parts" / "claude-security-c01.md").write_text("## Security\n\nNo findings.\n")
    (state["state"] / "coverage" / "claude-security-c01.txt").write_text("warehouse/api.go reviewed\n")
    (state["state"] / "parts" / "raw-claude-security-c01.ndjson").write_text('{"type":"text","part":{"text":"clean"}}\n')
    make_db(state["state"] / "opencode-db" / "claude-security-c01.db",
            [json.dumps({"type": "tool", "tool": "read", "state": {"input": {}}})])
    assert live_eval_go.find_marker_leaks(str(state["state"]), [MARKER]) == []


def test_fail_when_marker_is_in_a_part_file(state):
    (state["state"] / "parts" / "claude-security-c01.md").write_text(f"## Security\n\n{MARKER} leaked\n")
    leaked = live_eval_go.find_marker_leaks(str(state["state"]), [MARKER])
    assert [m for _, m in leaked] == [MARKER]


def test_fail_when_marker_is_in_a_coverage_file(state):
    (state["state"] / "coverage" / "claude-security-c01.txt").write_text(f"{MARKER}\n")
    assert live_eval_go.find_marker_leaks(str(state["state"]), [MARKER])


def test_fail_when_marker_is_in_a_raw_ndjson_stream(state):
    (state["state"] / "parts" / "raw-claude-security-c01.ndjson").write_text(
        json.dumps({"type": "text", "part": {"text": MARKER}}) + "\n")
    assert live_eval_go.find_marker_leaks(str(state["state"]), [MARKER])


def test_fail_when_marker_is_inside_an_opencode_db(state):
    make_db(state["state"] / "opencode-db" / "claude-security-c01.db",
            [json.dumps({"type": "tool", "tool": "read", "state": {"input": {"content": MARKER}}})])
    assert live_eval_go.find_marker_leaks(str(state["state"]), [MARKER])
