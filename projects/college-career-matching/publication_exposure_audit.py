"""Fail-closed audit of public institution-data exposure.

An explicit source release is not publication authorization. This audit detects
embedded records and external national loaders in a public explorer document.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._current = {"attrs": dict(attrs), "body": ""}

    def handle_data(self, data):
        if self._current is not None:
            self._current["body"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._current is not None:
            self.scripts.append(self._current)
            self._current = None


def inspect_public_explorer(html: str) -> list[str]:
    """Return blocking issues; empty list means no known institution exposure."""
    parser = _Scripts()
    parser.feed(html)
    issues = []
    if re.search(r'id\s*=\s*["\']ccx-real-institutions["\']', html, re.I):
        issues.append("real-institution UI is present")
    for script in parser.scripts:
        attrs, body = script["attrs"], script["body"]
        if attrs.get("id") == "ny20-embedded-data":
            issues.append("unapproved institution data embedded in public HTML")
        if re.search(r'national/manifest\.v\d+\.json|national-[0-9]{2,3}\.json', body):
            issues.append("national institution-data loader in public HTML")
    return issues


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    issues = inspect_public_explorer(args.html.read_text(encoding="utf-8"))
    for issue in issues:
        print("BLOCK:", issue)
    if issues:
        return 1
    print("PASS: no known public institution-data exposure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
