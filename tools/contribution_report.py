#!/usr/bin/env python
"""Per-author contribution table generated from the git log.

The contribution statement is only credible if it can be regenerated, so this
script reads the commit history and prints what each author actually touched.
It is a reporting tool: it never writes to the repository.

Usage:
    python tools/contribution_report.py
    python tools/contribution_report.py --json
"""
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Module ownership, by path prefix. Ownership is not the same as authorship:
# a file can be imported by one person and written by another, and the log
# alone cannot tell the difference. This map says who owns which module.
OWNERS = {
    "src/l1.py": "Jiale Zhang",
    "src/common.py": "Jiale Zhang",
    "reproduce.py": "Jiale Zhang",
    "src/l2.py": "Zijian Zhou",
    "src/l3.py": "Zijian Zhou",
    "docs/brief_note_L2.md": "Zijian Zhou",
    "docs/brief_note_L3.md": "Zijian Zhou",
    "README.md": "Jiale Zhang",
}


def _git(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)


def collect():
    log = _git("log", "--numstat", "--format=%x01%H%x02%an%x02%ae%x02%ad%x02%s",
               "--date=short")
    commits = []
    current = None
    for line in log.splitlines():
        if line.startswith("\x01"):
            if current:
                commits.append(current)
            h, an, ae, ad, s = line[1:].split("\x02", 4)
            current = {"hash": h, "author": an, "email": ae, "date": ad,
                       "subject": s, "added": 0, "removed": 0, "files": []}
        elif line.strip() and current is not None:
            parts = line.split("\t")
            if len(parts) == 3:
                a, r, path = parts
                try:
                    current["added"] += int(a)
                    current["removed"] += int(r)
                except ValueError:
                    pass
                current["files"].append(path)
    if current:
        commits.append(current)
    return commits


def summarise(commits):
    per_author = defaultdict(lambda: {"commits": 0, "added": 0, "removed": 0,
                                      "files": set(), "hashes": []})
    for c in commits:
        p = per_author[c["author"]]
        p["commits"] += 1
        p["added"] += c["added"]
        p["removed"] += c["removed"]
        p["files"].update(c["files"])
        p["hashes"].append(c["hash"][:7])
    owned = defaultdict(set)
    for path, owner in OWNERS.items():
        owned[owner].add(path)
    return per_author, owned


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        commits = collect()
    except Exception:
        print("not a git checkout (or git is not installed); nothing to report")
        return 1

    per_author, owned = summarise(commits)
    rows = []
    for author, stats in sorted(per_author.items(), key=lambda kv: -kv[1]["commits"]):
        rows.append({
            "author": author,
            "commits": stats["commits"],
            "added": stats["added"],
            "removed": stats["removed"],
            "hashes": stats["hashes"],
            "owned_files": sorted(owned.get(author, [])),
        })

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print("commits per author (regenerate this table, do not retype it)\n")
    print(f"{'author':24} {'commits':>7} {'added':>7} {'removed':>8}  commits")
    for r in rows:
        print(f"{r['author']:24} {r['commits']:>7} {r['added']:>7} "
              f"{r['removed']:>8}  {', '.join(r['hashes'])}")
    print("\nmodule ownership (from OWNERS in this file)\n")
    owners = defaultdict(set)
    for path, owner in OWNERS.items():
        owners[owner].add(path)
    for owner, files in sorted(owners.items()):
        print(f"{owner}: {', '.join(sorted(files))}")
    print("\nnote: authorship in the log and ownership of a module are different "
          "claims; docs/AUTHORSHIP.md explains where they diverge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
