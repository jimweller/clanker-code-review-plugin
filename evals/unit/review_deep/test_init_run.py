"""init_run.snapshot: an unreferenced commit over the live tree, for full and diff reviews."""
import os
import subprocess

import evidence
import init_run

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(root, *args, env=None):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env=env, check=True).stdout.strip()


def make_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-such-gitconfig"))
    monkeypatch.delenv("GIT_CONFIG_SYSTEM", raising=False)
    r = tmp_path / "repo"
    r.mkdir()
    (r / "a.txt").write_text("one\n")
    (r / "b.txt").write_text("delete me\n")
    (r / ".gitignore").write_text("ignored.txt\n")
    git(r, "init", "-q")
    git(r, "add", ".")
    git(r, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "one", env={**os.environ, **ENV})
    return r


def ls_tree(root, sha):
    return set(git(root, "ls-tree", "-r", "--name-only", sha).splitlines())


def test_clean_tree_returns_head_with_no_snapshot(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    head = git(r, "rev-parse", "HEAD")
    commit, is_snap = init_run.snapshot(str(r))
    assert (commit, is_snap) == (head, False)


def test_dirty_tree_reflects_modified_untracked_and_deleted_and_excludes_ignored_and_llmtmp(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    head = git(r, "rev-parse", "HEAD")
    (r / "a.txt").write_text("one\nmodified\n")
    (r / "b.txt").unlink()
    (r / "untracked.txt").write_text("new file\n")
    (r / "ignored.txt").write_text("skip me\n")
    (r / ".llmtmp").mkdir()
    (r / ".llmtmp" / "scratch.txt").write_text("scratch\n")
    commit, is_snap = init_run.snapshot(str(r))
    assert is_snap and commit != head
    paths = ls_tree(r, commit)
    assert paths == {"a.txt", ".gitignore", "untracked.txt"}
    assert git(r, "show", f"{commit}:a.txt") == "one\nmodified"
    assert git(r, "rev-parse", f"{commit}^") == head


def test_snapshot_is_deterministic(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    (r / "a.txt").write_text("one\nmodified\n")
    first, _ = init_run.snapshot(str(r))
    second, _ = init_run.snapshot(str(r))
    assert first == second


def test_snapshot_leaves_the_real_repository_state_untouched(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    (r / "a.txt").write_text("one\nmodified\n")
    (r / "untracked.txt").write_text("new file\n")
    before_status = git(r, "status", "--porcelain")
    before_refs = git(r, "for-each-ref")
    before_head = git(r, "rev-parse", "HEAD")
    before_reflog = git(r, "reflog", "show", "--all")
    before_index = (r / ".git" / "index").read_bytes()
    init_run.snapshot(str(r))
    assert git(r, "status", "--porcelain") == before_status
    assert git(r, "for-each-ref") == before_refs
    assert git(r, "rev-parse", "HEAD") == before_head
    assert git(r, "reflog", "show", "--all") == before_reflog
    assert (r / ".git" / "index").read_bytes() == before_index
    assert not os.path.exists(r / ".git" / f"index.review-snapshot.{os.getpid()}")


def test_snapshot_works_with_gpgsign_on_a_missing_key_and_no_user_identity(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    git(r, "config", "commit.gpgsign", "true")
    git(r, "config", "user.signingkey", "/no/such/signing/key")
    (r / "a.txt").write_text("one\nmodified\n")
    commit, is_snap = init_run.snapshot(str(r))
    assert is_snap and commit


def test_archive_and_evidence_read_the_uncommitted_edit(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    (r / "a.txt").write_text("one\nmodified\n")
    commit, _ = init_run.snapshot(str(r))
    archived = subprocess.run(["git", "-C", str(r), "archive", commit, "a.txt"], capture_output=True, check=True).stdout
    assert b"modified" in archived
    assert evidence.lines_at(str(r), commit, "a.txt") == ["one", "modified", ""]


HERE = os.path.dirname(os.path.abspath(init_run.__file__))


def run_cli(r, tmp_path, *args, env_extra=None):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(tmp_path / "no-such-gitconfig"),
           "XDG_CACHE_HOME": str(tmp_path / "cache"), **(env_extra or {})}
    env.pop("GIT_CONFIG_SYSTEM", None)
    state = tmp_path / "state"
    state.mkdir(exist_ok=True)
    return subprocess.run(["python3", f"{HERE}/init_run.py", str(r), str(r), str(state), *args],
                           capture_output=True, text=True, env=env)


def test_cli_writes_kind_head_snapshot_base_and_ticket_label_for_full(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    (r / "a.txt").write_text("one\nmodified\n")
    p = run_cli(r, tmp_path, "--kind", "full")
    assert p.returncode == 0, p.stderr
    run_dir = next(l.split("=", 1)[1] for l in p.stdout.splitlines() if l.startswith("RUN_DIR="))
    import json
    data = json.load(open(f"{run_dir}/run.json"))
    assert data["kind"] == "full"
    assert data["snapshot"] is True
    assert data["base"] is None
    assert data["ticket_label"] == "review-full"
    assert data["head"] != data["commit"]


def test_cli_requires_base_for_diff(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    p = run_cli(r, tmp_path, "--kind", "diff")
    assert p.returncode != 0
    assert "--base" in p.stderr + p.stdout


def test_cli_diff_records_base_and_review_diff_label(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    base = git(r, "rev-parse", "HEAD")
    p = run_cli(r, tmp_path, "--kind", "diff", "--base", base)
    assert p.returncode == 0, p.stderr
    run_dir = next(l.split("=", 1)[1] for l in p.stdout.splitlines() if l.startswith("RUN_DIR="))
    import json
    data = json.load(open(f"{run_dir}/run.json"))
    assert data["kind"] == "diff" and data["base"] == base and data["ticket_label"] == "review-diff"


def test_cli_default_kind_is_deep_and_matches_the_old_run_dir_shape(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    head = git(r, "rev-parse", "HEAD")
    p = run_cli(r, tmp_path)
    assert p.returncode == 0, p.stderr
    run_dir = next(l.split("=", 1)[1] for l in p.stdout.splitlines() if l.startswith("RUN_DIR="))
    assert run_dir.endswith(f"review-deep/repo-{head[:12]}")
    import json
    data = json.load(open(f"{run_dir}/run.json"))
    assert data["kind"] == "deep" and data["snapshot"] is False and data["commit"] == head


def test_cli_rerun_with_a_different_target_path_exits_nonzero(tmp_path, monkeypatch):
    r = make_repo(tmp_path, monkeypatch)
    p1 = run_cli(r, tmp_path, "--kind", "full")
    assert p1.returncode == 0, p1.stderr
    other = tmp_path / "state2"
    other.mkdir()
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(tmp_path / "no-such-gitconfig"), "XDG_CACHE_HOME": str(tmp_path / "cache")}
    env.pop("GIT_CONFIG_SYSTEM", None)
    p2 = subprocess.run(["python3", f"{HERE}/init_run.py", str(r), str(other), str(other), "--kind", "full"],
                         capture_output=True, text=True, env=env)
    assert p2.returncode != 0
