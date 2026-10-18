#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check that every relative link in the public documents resolves (standard library only).

    python -I scripts/check_docs.py

Covers the Markdown files at the repository root and under docs/, packages/, examples/, deploy/ and deployments/. The specification (spec/) has its own
link check inside spec/tools/check_all.py. External links are not fetched. A `#anchor` is checked against the headings of the target file.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^```")


def files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    for rel in out:
        if rel.endswith(".md") and (("/" not in rel) or rel.split("/")[0] in ("docs", "packages", "examples", "deploy", "deployments", ".github")):
            if (ROOT / rel).is_file():
                yield rel


def slug(heading):
    s = re.sub(r"`", "", heading.strip().lower())
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s", "-", s)


def anchors(path):
    found = set()
    in_code = False
    for line in path.read_bytes().decode("utf-8", errors="replace").split("\n"):
        if FENCE.match(line):
            in_code = not in_code
        if not in_code:
            m = re.match(r"^#{1,6}\s+(.*)", line)
            if m:
                found.add(slug(m.group(1)))
    return found


def main():
    problems = []
    n = 0
    for rel in files():
        try:
            text = (ROOT / rel).read_bytes().decode("utf-8")
        except UnicodeDecodeError as e:
            problems.append(f"{rel}: not valid UTF-8 (byte {e.start}); GitHub would show it as garbage and its links cannot be checked")
            continue
        if text.startswith("﻿"):
            problems.append(f"{rel}: starts with a byte-order mark; store Markdown as UTF-8 without one")
            text = text[1:]
        in_code = False
        for i, line in enumerate(text.split("\n"), 1):
            if FENCE.match(line):
                in_code = not in_code
                continue
            if in_code:
                continue
            for m in LINK.finditer(re.sub(r"`[^`]*`", "", line)):
                target = m.group(1)
                if re.match(r"^(https?:|mailto:)", target):
                    continue
                n += 1
                path, _, frag = target.partition("#")
                dest = (ROOT / rel).parent / path if path else ROOT / rel
                dest = dest.resolve()
                if path and not dest.exists():
                    problems.append(f"{rel}:{i}: {target} does not exist")
                elif frag and dest.is_file() and dest.suffix == ".md" and slug(frag) not in anchors(dest):
                    problems.append(f"{rel}:{i}: {target}: no heading for #{frag}")
    for p in problems:
        print("BROKEN", p)
    print(f"check_docs: {'FAILED' if problems else 'ok'} ({n} relative links checked, {len(problems)} broken)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
