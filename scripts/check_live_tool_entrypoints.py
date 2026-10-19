#!/usr/bin/env python3
"""Validate visitor-facing entry points for browser-based portfolio tools.

This contract checks source links and local tool discovery without requiring the
public website or an external API to be reachable during repository CI.
End-to-end interface behavior needs a separate browser QA pass.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"

TOOL_URLS = {
    "audience-lifecycle-crm-migration": "https://www.lauraelizabethhand.com/resources/project-operations-tools/audience-lifecycle-crm-migration-planner/",
    "college-career-matching": "https://www.lauraelizabethhand.com/resources/data-decision-making-tools/college-career-explorer/",
    "curriculum-planning-canvas": "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/curriculum-planning-canvas/",
    "ethical-ai-scenario-auditor": "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/ethical-ai-scenario-auditor/",
    "evidence-safe-prompt-lab": "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/evidence-safe-prompt-lab/",
    "prompt-literacy-debugger": "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/prompt-literacy-debugger/",
    "reverse-ats-role-evidence-engine": "https://www.lauraelizabethhand.com/resources/career-professional-development-tools/reverse-ats/",
    "standards-check": "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/standards-check/",
    "text-lens": "https://www.lauraelizabethhand.com/resources/research-writing-tools/text-lens/",
}


def main() -> int:
    errors: list[str] = []
    gallery_path = PROJECTS / "README.md"
    gallery = gallery_path.read_text(encoding="utf-8") if gallery_path.exists() else ""
    profile_path = ROOT / "README.md"
    profile = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""

    if "](projects/)" not in profile:
        errors.append("Profile README does not link to projects/ gallery.")
    if not gallery:
        errors.append("Missing audience-facing projects/README.md gallery.")

    actual_html_dirs = {
        path.parent.name for path in PROJECTS.glob("*/index.html") if path.is_file()
    }
    unmapped = actual_html_dirs - TOOL_URLS.keys()
    for slug in sorted(unmapped):
        errors.append(f"Browser tool {slug} lacks a registered live interface.")

    for slug, url in TOOL_URLS.items():
        folder = PROJECTS / slug
        readme = folder / "README.md"
        if not readme.is_file():
            errors.append(f"{slug}: missing README.md")
            continue
        readme_text = readme.read_text(encoding="utf-8")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "www.lauraelizabethhand.com":
            errors.append(f"{slug}: link not an HTTPS portfolio URL.")
        if url not in readme_text:
            errors.append(f"{slug}: README missing live interface link {url}")
        if url not in gallery:
            errors.append(f"{slug}: project gallery missing live interface link {url}")
        html = folder / "index.html"
        if html.is_file() and "<script" not in html.read_text(encoding="utf-8").lower():
            errors.append(f"{slug}: HTML entry point lacks a script.")
        if "\\n" in readme_text:
            errors.append(f"{slug}: README contains literal backslash-n escape sequences.")

    if errors:
        print("Live tool documentation validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Validated {len(TOOL_URLS)} visitor-facing tool links, gallery entries, and local HTML coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
