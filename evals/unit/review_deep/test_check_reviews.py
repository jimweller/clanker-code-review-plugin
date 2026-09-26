"""check_reviews.py: validates each area's review-full/review-diff output file. No model calls."""
import json
import sys

import check_reviews


def test_missing_file_fails():
    assert check_reviews.check("/no/such/file.md") == ["missing"]


def test_no_h2_heading_fails(tmp_path):
    f = tmp_path / "claude-security.md"
    f.write_text("No findings.\n")
    assert "no H2 heading" in check_reviews.check(str(f))


def test_no_findings_and_not_exactly_no_findings_fails(tmp_path):
    f = tmp_path / "claude-security.md"
    f.write_text("## Security\n\nLooks fine to me.\n")
    problems = check_reviews.check(str(f))
    assert any("not exactly" in p for p in problems)


def test_unparsable_bullet_fails(tmp_path):
    f = tmp_path / "claude-security.md"
    f.write_text("## Security\n\n- **High** no location at all\n")
    problems = check_reviews.check(str(f))
    assert any("unparsable" in p for p in problems)


def test_exactly_no_findings_passes(tmp_path):
    f = tmp_path / "claude-security.md"
    f.write_text("## Security\n\nNo findings.\n")
    assert check_reviews.check(str(f)) == []


def test_valid_findings_pass(tmp_path):
    f = tmp_path / "claude-security.md"
    f.write_text("## Security\n\n- **High** `src/a.ts:12` `login` Trusts the header with no check.\n"
                  "- **Medium** `src/b.ts:3` Missing timeout on fetch.\n")
    assert check_reviews.check(str(f)) == []


def test_main_exits_nonzero_and_names_every_failed_area(tmp_path, capsys):
    state = tmp_path / "state"
    state.mkdir()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run.json").write_text(json.dumps({"repo": str(tmp_path), "commit": "deadbeef", "state_dir": str(state)}))
    for area in check_reviews.AREAS:
        if area == "security":
            continue
        (state / f"claude-{area}.md").write_text("## Area\n\nNo findings.\n")
    (state / "claude-security.md").write_text("## Security\n\nnot valid\n")
    old_argv = sys.argv
    sys.argv = ["check_reviews.py", str(run_dir), "claude"]
    try:
        check_reviews.main()
        raised = False
    except SystemExit as e:
        raised = True
        code = e.code
    finally:
        sys.argv = old_argv
    assert raised and code == 1
    out = capsys.readouterr().out
    assert "FAIL security" in out
    assert "failed areas: security" in out
