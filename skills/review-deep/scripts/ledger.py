#!/usr/bin/env python3
"""Build ledger.txt, the reviewable path list, for review-full and review-diff. No model calls.

    python3 ledger.py STATE_DIR --repomix REPOMIX_XML
    python3 ledger.py STATE_DIR --diff REPO BASE COMMIT

--repomix reads every `<file path="...">` entry out of a repomix XML pack and unescapes the XML
entities in the path. --diff runs `git diff --name-only --no-renames --diff-filter=d BASE COMMIT`
in REPO: --no-renames turns a rename into a delete of the old path plus an add of the new one, and
--diff-filter=d drops the delete side (and every other deletion), so a rename leaves only the new
path and a plain deletion leaves nothing. An untracked file present in COMMIT (for instance one
folded into a review-full or review-diff snapshot commit) is an add relative to BASE and is kept.
Writes STATE_DIR/ledger.txt, one sorted path per line. Prints LEDGER=n.
"""
import argparse
import os
import re
import subprocess
from xml.sax.saxutils import unescape

FILE_TAG = re.compile(r'<file path="(?P<path>[^"]*)">')
ENTITIES = {"&apos;": "'", "&quot;": '"'}


def from_repomix(xml):
    return sorted({unescape(m.group("path"), ENTITIES) for m in FILE_TAG.finditer(xml)})


def from_diff(repo, base, commit):
    out = subprocess.run(["git", "-C", repo, "diff", "--name-only", "--no-renames", "--diff-filter=d", base, commit],
                         capture_output=True, text=True, check=True).stdout
    return sorted({l for l in out.splitlines() if l.strip()})


def write(state_dir, paths):
    os.makedirs(state_dir, exist_ok=True)
    open(f"{state_dir}/ledger.txt", "w", encoding="utf-8").write("".join(f"{p}\n" for p in paths))
    print(f"LEDGER={len(paths)}")
    return len(paths)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("state_dir")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--repomix")
    g.add_argument("--diff", nargs=3, metavar=("REPO", "BASE", "COMMIT"))
    a = ap.parse_args()
    state_dir = os.path.abspath(os.path.expanduser(a.state_dir))
    if a.repomix:
        paths = from_repomix(open(a.repomix, encoding="utf-8").read())
    else:
        paths = from_diff(*a.diff)
    write(state_dir, paths)


if __name__ == "__main__":
    main()
