"""windows.cut: overlapping window index groups, with no empty window for 0 or 1 issues."""
from windows import cut


def test_cut_returns_nothing_for_zero_issues():
    assert cut([], 150, 25) == {}


def test_cut_returns_nothing_for_one_issue():
    assert cut([0], 150, 25) == {}


def test_cut_windows_twelve_issues_with_overlap():
    order = list(range(12))
    windows = cut(order, 5, 2)
    assert list(windows) == ["g-01", "g-02", "g-03", "g-04"]
    assert windows["g-01"] == [0, 1, 2, 3, 4]
    assert windows["g-02"] == [3, 4, 5, 6, 7]
    assert windows["g-03"] == [6, 7, 8, 9, 10]
    assert windows["g-04"] == [9, 10, 11]
    covered = {i for idx in windows.values() for i in idx}
    assert covered == set(order)
