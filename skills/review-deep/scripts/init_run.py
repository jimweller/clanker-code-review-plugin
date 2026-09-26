#!/usr/bin/env python3
"""Create the run directory for one review and write run.json. No model calls.

    python3 init_run.py PROJECT_ROOT TARGET_PATH STATE_DIR [--kind deep|full|diff] [--base SHA]

The run directory is ${XDG_CACHE_HOME:-~/.cache}/review-<kind>/<repo>-<commit12>, outside the
reviewed repository, so nothing the later stages write can be read by a judge. run.json records
the repository, the reviewed commit, the real HEAD, whether the commit is a snapshot, the kind,
the base (diff only), the branch, the target path, the review state directory, the judge checkout
path, the default models, the files a judge must not see, the ticket label, and the commit
sentence tickets carry.

--kind selects deep (default), full, or diff. --base names the commit review-diff compares
against and is required for --kind diff. deep reviews HEAD directly and prints a dirty-tree
warning, exactly as before. full and diff instead read whatever snapshot() returns, so a reviewer
looking at the live tree and a judge looking at the reviewed commit see the same uncommitted
edits. Prints RUN_DIR and COMMIT. A rerun against an existing run directory with a different
--base or TARGET_PATH exits 1, rather than silently changing what an existing run means.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DEFAULT_MODELS, JUDGE_EXCLUDE  # noqa: E402

IDENTITY = {"GIT_AUTHOR_NAME": "clanker-code-review", "GIT_AUTHOR_EMAIL": "clanker-code-review@localhost",
            "GIT_COMMITTER_NAME": "clanker-code-review", "GIT_COMMITTER_EMAIL": "clanker-code-review@localhost"}


def git(root, *args, env=None):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, env=env).stdout.strip()


def snapshot(root):
    """The commit a full or diff review should read.

    A clean tree returns (HEAD, False) unchanged. A dirty tree builds a temporary index seeded
    from HEAD, adds every modified, added, and deleted path except ignored files, .llmtmp, and
    .serena, writes that as a tree, and commits it over HEAD with a fixed author/committer identity
    dated at HEAD's own committer date, so the same working tree always produces the same SHA. The
    commit is never referenced by a branch or tag, so it costs no ref, no index, and no reflog
    change to the real repository, and git gc can reclaim it once nothing points at it. Returns
    (commit, True).
    """
    head = git(root, "rev-parse", "HEAD")
    if not git(root, "status", "--porcelain"):
        return head, False
    index = os.path.join(root, ".git", f"index.review-snapshot.{os.getpid()}")
    env = {**os.environ, "GIT_INDEX_FILE": index}
    try:
        git(root, "read-tree", "HEAD", env=env)
        git(root, "add", "-A", "--", ".", ":(exclude).llmtmp", ":(exclude).serena", env=env)
        tree = git(root, "write-tree", env=env)
        when = git(root, "show", "-s", "--format=%cI", "HEAD")
        commit_env = {**env, **IDENTITY, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        commit = git(root, "commit-tree", "--no-gpg-sign", tree, "-p", "HEAD", "-m", "clanker-code-review snapshot",
                     env=commit_env)
        if not commit:
            sys.exit(f"{root}: git commit-tree produced no snapshot commit")
        return commit, True
    finally:
        if os.path.exists(index):
            os.remove(index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("target")
    ap.add_argument("state")
    ap.add_argument("--kind", choices=["deep", "full", "diff"], default="deep")
    ap.add_argument("--base")
    a = ap.parse_args()
    if a.kind == "diff" and not a.base:
        sys.exit("--base is required for --kind diff")
    root, target, state = (os.path.abspath(os.path.expanduser(p)) for p in (a.root, a.target, a.state))
    head = git(root, "rev-parse", "HEAD")
    if not head:
        sys.exit(f"{root} has no commit")
    if a.kind == "deep":
        commit, is_snapshot = head, False
    else:
        commit, is_snapshot = snapshot(root)
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    run = os.path.join(cache, f"review-{a.kind}", f"{os.path.basename(root)}-{commit[:12]}")
    os.makedirs(run, exist_ok=True)
    existing = json.load(open(f"{run}/run.json")) if os.path.exists(f"{run}/run.json") else {}
    if existing and (existing.get("base") != a.base or existing.get("target_path") != target):
        sys.exit(f"{run}/run.json already exists for a different base or target_path; remove it first")
    data = {
        "repo": root, "commit": commit, "head": head, "snapshot": is_snapshot, "kind": a.kind, "base": a.base,
        "branch": branch, "target_path": target, "state_dir": state,
        "run_dir": run, "checkout": f"{run}/checkout",
        "ticket_label": existing.get("ticket_label", f"review-{a.kind}"),
        "models": existing.get("models", DEFAULT_MODELS), "concurrency": existing.get("concurrency", 50),
        "judge_exclude": existing.get("judge_exclude", JUDGE_EXCLUDE),
        "commit_sentence": existing.get("commit_sentence",
                                        f"Paths and line numbers refer to commit {{{{{commit}}}}} on {branch}."),
    }
    json.dump(data, open(f"{run}/run.json", "w"), indent=1)
    print(f"RUN_DIR={run}")
    print(f"COMMIT={commit}")
    if a.kind == "deep":
        dirty = [l for l in git(root, "status", "--porcelain").splitlines() if not l[3:].startswith((".llmtmp", ".serena"))]
        if dirty:
            print(f"WARNING {len(dirty)} uncommitted changes. Reviewers read the live tree, judges read commit {commit[:12]}:")
            for l in dirty[:10]:
                print(f"  {l}")


if __name__ == "__main__":
    main()
