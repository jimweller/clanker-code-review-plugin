"""check_cross_component: only a sweep part counts, and only near one of the two anchors."""
import live_eval_go  # conftest.py puts evals/ on sys.path before this module loads

DEFECT = {"locations": [{"path": "warehouse/api.go", "anchor": "if true {"},
                         {"path": "shipping/rate.go", "anchor": "return weight * 0.004"}]}


def test_pass_when_a_sweep_part_cites_either_location(state):
    (state["state"] / "parts" / "claude-correctness-sweep.md").write_text(
        "## Correctness\n\n- **Medium** `shipping/rate.go:4` `ShippingCost` treats kilograms as grams.\n")
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert live_eval_go.check_cross_component(str(state["state"]), repo_root, DEFECT)


def test_fail_when_only_a_component_part_cites_it(state):
    (state["state"] / "parts" / "claude-correctness-c02.md").write_text(
        "## Correctness\n\n- **Medium** `shipping/rate.go:4` `ShippingCost` treats kilograms as grams.\n")
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert not live_eval_go.check_cross_component(str(state["state"]), repo_root, DEFECT)


def test_fail_when_the_sweep_finding_is_far_from_both_anchors(state):
    (state["state"] / "parts" / "claude-correctness-sweep.md").write_text(
        "## Correctness\n\n- **Medium** `shipping/rate.go:400` `ShippingCost` unrelated, far away.\n")
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert not live_eval_go.check_cross_component(str(state["state"]), repo_root, DEFECT)
