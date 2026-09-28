"""check_area_defect: a defect found by an arm of its own area, near its anchor line."""
import live_eval_go  # conftest.py puts evals/ on sys.path before this module loads


def test_pass_when_area_arm_cites_file_near_anchor(state):
    (state["state"] / "parts" / "claude-security-c01.md").write_text(
        "## Security\n\n- **High** `warehouse/api.go:5` `Authenticate` Hardcoded bypass grants access.\n")
    defect = {"area": "security", "locations": [{"path": "warehouse/api.go", "anchor": "if true {"}]}
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert live_eval_go.check_area_defect(str(state["state"]), repo_root, defect)


def test_pass_matches_an_absolute_cited_path_by_suffix(state):
    (state["state"] / "parts" / "openai-security-c01.md").write_text(
        "## Security\n\n- **High** `/tmp/some/copy/goeval/warehouse/api.go:4` Bypass via debug header.\n")
    defect = {"area": "security", "locations": [{"path": "warehouse/api.go", "anchor": "if true {"}]}
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert live_eval_go.check_area_defect(str(state["state"]), repo_root, defect)


def test_fail_when_no_finding_in_that_area(state):
    (state["state"] / "parts" / "claude-architecture-c01.md").write_text("## Architecture\n\nNo findings.\n")
    defect = {"area": "security", "locations": [{"path": "warehouse/api.go", "anchor": "if true {"}]}
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert not live_eval_go.check_area_defect(str(state["state"]), repo_root, defect)


def test_fail_when_citation_is_too_far_from_the_anchor(state):
    (state["state"] / "parts" / "claude-security-c01.md").write_text(
        "## Security\n\n- **High** `warehouse/api.go:99` `Other` unrelated finding far away.\n")
    defect = {"area": "security", "locations": [{"path": "warehouse/api.go", "anchor": "if true {"}]}
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert not live_eval_go.check_area_defect(str(state["state"]), repo_root, defect)


def test_fail_when_the_right_area_cites_the_wrong_file(state):
    (state["state"] / "parts" / "claude-security-c01.md").write_text(
        "## Security\n\n- **High** `shipping/rate.go:4` `ShippingCost` unrelated finding, wrong file.\n")
    defect = {"area": "security", "locations": [{"path": "warehouse/api.go", "anchor": "if true {"}]}
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert not live_eval_go.check_area_defect(str(state["state"]), repo_root, defect)
