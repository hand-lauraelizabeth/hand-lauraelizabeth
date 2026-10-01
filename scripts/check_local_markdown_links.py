#!/usr/bin/env python3
"""Fail when a local Markdown link points to a missing file or directory."""

from pathlib import Path
from urllib.parse import unquote
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")

errors = []

for md in ROOT.rglob("*.md"):
    text = md.read_text(encoding="utf-8")
    for raw in LINK_RE.findall(text):
        target = raw.strip().split()[0].strip("<>")
        if not target or target.startswith(SKIP_PREFIXES):
            continue
        target = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not target:
            continue
        resolved = (md.parent / target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{md.relative_to(ROOT)}: link escapes repository: {raw}")
            continue
        if not resolved.exists():
            errors.append(f"{md.relative_to(ROOT)}: missing local target: {raw}")

if errors:
    print("Broken local Markdown links:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("All local Markdown links resolve.")
