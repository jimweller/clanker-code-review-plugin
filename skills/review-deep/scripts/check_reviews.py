#!/usr/bin/env python3
"""Check that every area's review-full or review-diff output file is well-formed. No model calls.

    python3 check_reviews.py RUN_DIR LABEL

For each of the nine areas (architecture, correctness, data, ops, performance, quality, security,
solid, testing), checks that STATE_DIR/LABEL-<area>.md exists, has an H2 heading, holds at least
one finding bullet or is exactly "No findings.", and that every "- **" line parses with
normalize.FULL or normalize.BARE. Prints one line per area and exits 1 when any area fails, so the
calling skill knows which areas to re-dispatch.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_run, run_dir  # noqa: E402
from normalize import BARE, FULL  # noqa: E402

AREAS = ["architecture", "correctness", "data", "ops", "performance", "quality", "security", "solid", "testing"]


def check(path):
    if not os.path.exists(path):
        return ["missing"]
    lines = open(path, encoding="utf-8").read().splitlines()
    problems = []
    if not any(l.startswith("## ") for l in lines):
        problems.append("no H2 heading")
    bullets = [l.strip() for l in lines if l.strip().startswith("- **")]
    body = "\n".join(l for l in lines if not l.startswith("## ")).strip()
    if not bullets and body != "No findings.":
        problems.append('no findings and body is not exactly "No findings."')
    for l in bullets:
        if not (FULL.match(l) or BARE.match(l)):
            problems.append(f"unparsable: {l[:160]}")
    return problems


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__.split("\n\n")[1])
    d = run_dir(sys.argv[:2])
    run = load_run(d)
    label = sys.argv[2]
    failed = []
    for area in AREAS:
        problems = check(f"{run['state_dir']}/{label}-{area}.md")
        print(f"{'ok' if not problems else 'FAIL'} {area}" + (f": {'; '.join(problems)}" if problems else ""))
        if problems:
            failed.append(area)
    if failed:
        print(f"failed areas: {' '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
