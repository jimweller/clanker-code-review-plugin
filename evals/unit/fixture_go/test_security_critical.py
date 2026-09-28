"""check_security_critical: some arm rates the security defect Critical.

The reviewer agents' current output format allows only High, Medium, or Low
severities (agents/reviewer-security.md, "Output"), so a live run can never satisfy
this check today. These tests exercise the scorer's own logic with a synthetic
Critical bullet, independent of that limitation.
"""
import live_eval_go  # conftest.py puts evals/ on sys.path before this module loads

DEFECT = {"locations": [{"path": "warehouse/api.go", "anchor": "if true {"}]}


def test_pass_when_some_arm_rates_it_critical(state):
    (state["state"] / "parts" / "openai-security-c01.md").write_text(
        "## Security\n\n- **Critical** `warehouse/api.go:4` `Authenticate` Hardcoded bypass grants access.\n")
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert live_eval_go.check_security_critical(str(state["state"]), repo_root, DEFECT)


def test_fail_when_only_high_or_lower_is_reported(state):
    (state["state"] / "parts" / "openai-security-c01.md").write_text(
        "## Security\n\n- **High** `warehouse/api.go:4` `Authenticate` Hardcoded bypass grants access.\n")
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert not live_eval_go.check_security_critical(str(state["state"]), repo_root, DEFECT)


def test_fail_when_the_critical_finding_cites_a_different_file(state):
    (state["state"] / "parts" / "openai-security-c01.md").write_text(
        "## Security\n\n- **Critical** `shipping/rate.go:4` `ShippingCost` unrelated critical finding.\n")
    repo_root = live_eval_go.repo_root_of(str(state["state"]))
    assert not live_eval_go.check_security_critical(str(state["state"]), repo_root, DEFECT)
