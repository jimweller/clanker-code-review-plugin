"""report.py: the kind-aware header and coverage section for full and diff, deep unchanged."""
import json
import sys

import report


def test_header_deep_is_unchanged_by_kind_fields():
    run = {"repo": "/x/myrepo", "commit": "abcdef123456", "kind": "deep", "snapshot": False, "head": "abcdef123456"}
    assert report.header(run) == "# Review of myrepo at abcdef123456"


def test_header_full_names_the_snapshot_head():
    run = {"repo": "/x/myrepo", "commit": "1111111111112222", "kind": "full", "snapshot": True, "head": "aaaaaaaaaaaabbbb"}
    assert report.header(run) == "# Review of myrepo at 111111111111 (a snapshot of HEAD aaaaaaaaaaaa)"


def test_header_diff_names_base_and_snapshot():
    run = {"repo": "/x/myrepo", "commit": "1111111111112222", "kind": "diff", "base": "ccccccccccccdddd",
           "snapshot": True, "head": "aaaaaaaaaaaabbbb"}
    assert report.header(run) == ("# Review of myrepo at 111111111111 "
                                   "(against base cccccccccccc, a snapshot of HEAD aaaaaaaaaaaa)")


def test_header_diff_without_snapshot_names_only_base():
    run = {"repo": "/x/myrepo", "commit": "1111111111112222", "kind": "diff", "base": "ccccccccccccdddd", "snapshot": False}
    assert report.header(run) == "# Review of myrepo at 111111111111 (against base cccccccccccc)"


def build_run(tmp_path, kind, **extra):
    state = tmp_path / "state"
    state.mkdir()
    (state / "ledger.txt").write_text("src/a.ts\nsrc/b.ts\n")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run = {"repo": str(tmp_path / "repo"), "commit": "abcdef123456", "state_dir": str(state), "kind": kind, **extra}
    (run_dir / "run.json").write_text(json.dumps(run))
    (run_dir / "findings.jsonl").write_text("")
    (run_dir / "issues.jsonl").write_text("")
    return run_dir, state


def test_main_deep_coverage_lists_never_reviewed(tmp_path, monkeypatch):
    run_dir, state = build_run(tmp_path, "deep")
    (state / "reviewed.txt").write_text("src/a.ts\n")
    monkeypatch.setattr(sys, "argv", ["report.py", str(run_dir)])
    report.main()
    out = (run_dir / "report.md").read_text()
    assert "## Coverage" in out
    assert "never marked reviewed by any arm" in out
    assert "never reviewed `src/b.ts`" in out


def test_main_full_coverage_lists_scope_and_area_files_present(tmp_path, monkeypatch):
    run_dir, state = build_run(tmp_path, "full", snapshot=False)
    (state / "claude-security.md").write_text("## Security\n\nNo findings.\n")
    (state / "claude-testing.md").write_text("## Testing\n\nNo findings.\n")
    monkeypatch.setattr(sys, "argv", ["report.py", str(run_dir)])
    report.main()
    out = (run_dir / "report.md").read_text()
    assert "## Coverage" in out
    assert "2 files in scope." in out
    assert "Area files present: security, testing." in out
    assert "- `src/a.ts`" in out and "- `src/b.ts`" in out
