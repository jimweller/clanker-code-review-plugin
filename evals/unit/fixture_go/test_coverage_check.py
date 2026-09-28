"""find_missing_parts: every tasks.txt/sweeps.txt line has a matching non-empty
parts/<label>-<area>-<comp>.md."""
import live_eval_go  # conftest.py puts evals/ on sys.path before this module loads


def test_pass_when_every_task_has_a_nonempty_part(state):
    (state["state"] / "tasks.txt").write_text("claude openai/x security c01\n")
    (state["state"] / "parts" / "claude-security-c01.md").write_text("## Security\n\nNo findings.\n")
    assert live_eval_go.find_missing_parts(str(state["state"])) == []


def test_fail_when_a_part_file_is_missing(state):
    (state["state"] / "tasks.txt").write_text("claude openai/x security c01\n")
    assert live_eval_go.find_missing_parts(str(state["state"]))


def test_fail_when_a_part_file_exists_but_is_empty(state):
    (state["state"] / "tasks.txt").write_text("claude openai/x security c01\n")
    (state["state"] / "parts" / "claude-security-c01.md").write_text("")
    assert live_eval_go.find_missing_parts(str(state["state"]))


def test_fail_when_tasks_txt_itself_is_missing(state):
    assert live_eval_go.find_missing_parts(str(state["state"]))


def test_sweeps_txt_lines_are_also_required(state):
    (state["state"] / "tasks.txt").write_text("")
    (state["state"] / "sweeps.txt").write_text("claude openai/x security sweep\n")
    assert live_eval_go.find_missing_parts(str(state["state"]))
    (state["state"] / "parts" / "claude-security-sweep.md").write_text("## Security\n\nNo findings.\n")
    assert live_eval_go.find_missing_parts(str(state["state"])) == []
