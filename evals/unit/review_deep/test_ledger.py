"""ledger.py: the reviewable path list for review-full (repomix) and review-diff (git diff)."""
import os
import subprocess

import ledger

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env={**os.environ, **ENV},
                           check=True).stdout.strip()


def test_from_repomix_unescapes_xml_entities():
    xml = (
        '<files>'
        '<file path="src/a.ts">content</file>'
        '<file path="src/a&amp;b.ts">content</file>'
        '<file path="src/&quot;quoted&quot;.ts">content</file>'
        '</files>'
    )
    assert ledger.from_repomix(xml) == ['src/"quoted".ts', "src/a&b.ts", "src/a.ts"]


def test_from_diff_gives_the_new_path_for_a_rename_and_drops_a_plain_deletion(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    (r / "keep.ts").write_text("keep\n")
    (r / "old_name.ts").write_text("renamed content\n")
    (r / "gone.ts").write_text("bye\n")
    git(r, "init", "-q")
    git(r, "add", ".")
    git(r, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "base")
    base = git(r, "rev-parse", "HEAD")

    (r / "old_name.ts").rename(r / "new_name.ts")
    (r / "gone.ts").unlink()
    (r / "untracked.ts").write_text("new file\n")
    git(r, "add", "-A")
    git(r, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "changes")
    commit = git(r, "rev-parse", "HEAD")

    paths = ledger.from_diff(str(r), base, commit)
    assert paths == ["new_name.ts", "untracked.ts"]
    assert "old_name.ts" not in paths
    assert "gone.ts" not in paths


def test_write_creates_ledger_and_prints_count(tmp_path, capsys):
    state = tmp_path / "state"
    n = ledger.write(str(state), ["b.ts", "a.ts", "a.ts"])
    assert n == 3
    assert (state / "ledger.txt").read_text().splitlines() == ["b.ts", "a.ts", "a.ts"]
    assert capsys.readouterr().out.strip() == "LEDGER=3"
