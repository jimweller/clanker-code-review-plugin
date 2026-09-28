"""common.ticket_label and common.category."""
import pytest

from common import category, ticket_label


def test_old_runs_with_no_ticket_label_give_review_deep():
    assert ticket_label({}) == "review-deep"
    assert ticket_label({"kind": "deep"}) == "review-deep"


def test_explicit_ticket_label_is_returned():
    assert ticket_label({"kind": "full", "ticket_label": "review-full"}) == "review-full"
    assert ticket_label({"kind": "diff", "ticket_label": "review-diff"}) == "review-diff"


@pytest.mark.parametrize("area,label", [("bug", "correctness"), ("maintainability", "quality"), ("test", "testing"),
                                        ("documentation", "quality"), ("security", "security"), ("solid", "solid"),
                                        ("other", "quality"), ("unknown", "quality"), ("style", "quality")])
def test_category_maps_every_area_into_the_label_set(area, label):
    assert category(area) == label
