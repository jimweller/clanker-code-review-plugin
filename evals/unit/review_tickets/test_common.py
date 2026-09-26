"""common.ticket_label: the Jira label naming which review kind produced a run."""
from common import ticket_label


def test_old_runs_with_no_ticket_label_give_review_deep():
    assert ticket_label({}) == "review-deep"
    assert ticket_label({"kind": "deep"}) == "review-deep"


def test_explicit_ticket_label_is_returned():
    assert ticket_label({"kind": "full", "ticket_label": "review-full"}) == "review-full"
    assert ticket_label({"kind": "diff", "ticket_label": "review-diff"}) == "review-diff"
