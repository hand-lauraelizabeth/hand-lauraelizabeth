"""Fail-closed path audit for institutional exports in this public repository.

This is a path-exposure detector, not independent verification, a publication
approval mechanism, a content scanner, or a Git-history audit. It intentionally
fails while unapproved real-record exports remain in the public tree.
"""
from __future__ import annotations

import argparse
from pathlib import Path

PROJECT = Path("projects/college-career-matching")
RECORD_SUFFIXES = (
    ".json", ".json.gz", ".jsonl", ".ndjson", ".csv", ".tsv",
    ".parquet", ".sqlite", ".db", ".xlsx", ".geojson",
)
METADATA_ALLOWLIST = frozenset({
    "data/national/manifest.v1.json",
    "data/sprint1/manifest.json",
})
EXTRA_BLOCKED = frozenset({
    "ny-pilot-20-public-reference.json",
    "ny-pilot-20-directory.fragment.html",
})


def inspect_repository(repo_root: Path) -> list[str]:
    """Report candidate institutional exports without opening their contents."""
    project = Path(repo_root).resolve() / PROJECT
    if not project.is_dir():
        return ["matcher project directory missing; containment cannot be verified"]
    issues: set[str] = set()
    for relative in EXTRA_BLOCKED:
        path = project / relative
        if path.exists() or path.is_symlink():
            issues.add(f"unapproved institutional export: {PROJECT / relative}")
    for prefix in ("data", "private_review"):
        subtree = project / prefix
        if subtree.is_symlink():
            issues.add(f"symlinked evidence directory: {PROJECT / prefix}")
            continue
        if not subtree.is_dir():
            continue
        for path in subtree.rglob("*"):
            relative = path.relative_to(project).as_posix()
            if path.is_symlink():
                issues.add(f"symlink in evidence tree: {PROJECT / relative}")
            elif (
                path.is_file()
                and relative not in METADATA_ALLOWLIST
                and relative.lower().endswith(RECORD_SUFFIXES)
            ):
                issues.add(f"unapproved institutional export: {PROJECT / relative}")
    return sorted(issues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    issues = inspect_repository(args.repo_root)
    for issue in issues:
        print("BLOCK:", issue)
    if issues:
        return 1
    print("PASS: no unapproved export paths detected; history/content review still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
