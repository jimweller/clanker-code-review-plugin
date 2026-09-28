#!/usr/bin/env python3
"""Make the scrubbed export every review-deep arm copies. No model calls.

    python3 export.py RUN_DIR

Exports the reviewed commit into a new temporary directory with checkout.make, so it holds what a
judge sees: no agent-instruction files, no agent or editor config, no review state. Then commits it
as a one-commit repository of its own, so opencode, Serena, and ocr find their project root at the
export rather than in any repository around it. The commit ignores the operator's git config,
which may require signing or run hooks. Prints EXPORT. Each arm reviews its own copy of it, never
the live repository.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checkout import make  # noqa: E402
from common import load_run, run_dir  # noqa: E402

GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_AUTHOR_NAME": "review-deep",
           "GIT_AUTHOR_EMAIL": "review-deep@localhost", "GIT_COMMITTER_NAME": "review-deep",
           "GIT_COMMITTER_EMAIL": "review-deep@localhost", "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
           "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z"}


def main():
    run = load_run(run_dir())
    dest = os.path.realpath(tempfile.mkdtemp(prefix="review-deep-export."))
    removed = make(run, dest)
    env = {**os.environ, **GIT_ENV}
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-verify", "-m", f"review-deep export of {run['commit'][:12]}"]):
        subprocess.run(["git", "-C", dest, *args], check=True, env=env, capture_output=True)
    print(f"EXPORT={dest}")
    print(f"export holds {run['commit'][:12]}, removed {len(removed)} excluded paths")


if __name__ == "__main__":
    main()
