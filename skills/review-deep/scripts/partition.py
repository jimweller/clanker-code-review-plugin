#!/usr/bin/env python3
"""Split a ledger into components of at most SIZE files, directory-aware. No model calls.

    python3 partition.py STATE_DIR [SIZE]

Reads STATE_DIR/ledger.txt, one reviewable path per line, and writes STATE_DIR/components/cNN.txt,
each holding at most SIZE paths (default 25). Paths are grouped by directory first, so a component
stays inside one directory tree unless that tree alone holds more than SIZE files, in which case it
is recursively split by the next path segment. Deterministic: the same ledger always produces the
same components in the same order. Prints COMPONENTS=n.
"""
import os
import sys
from collections import OrderedDict


def split_paths(paths, size=25):
    def split(ps, depth):
        if len(ps) <= size:
            return [ps]
        groups = OrderedDict()
        for p in ps:
            parts = p.split("/")
            groups.setdefault(parts[depth] if depth < len(parts) - 1 else p, []).append(p)
        out, cur = [], []
        for g in groups.values():
            if len(g) > size:
                if cur:
                    out.append(cur)
                    cur = []
                out.extend(split(g, depth + 1))
            elif len(cur) + len(g) <= size:
                cur += g
            else:
                out.append(cur)
                cur = g
        if cur:
            out.append(cur)
        return out

    comps = []
    for c in split(sorted(paths), 0):
        if comps and len(comps[-1]) + len(c) <= size:
            comps[-1] += c
        else:
            comps.append(c)
    return comps


def main(state_dir, size=25):
    os.makedirs(f"{state_dir}/components", exist_ok=True)
    paths = sorted(l.strip() for l in open(f"{state_dir}/ledger.txt") if l.strip())
    comps = split_paths(paths, size)
    for i, c in enumerate(comps, 1):
        open(f"{state_dir}/components/c{i:02d}.txt", "w").write("\n".join(c) + "\n")
    print(f"COMPONENTS={len(comps)}")
    return len(comps)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.split("\n\n")[1])
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    main(os.path.abspath(os.path.expanduser(sys.argv[1])), size)
