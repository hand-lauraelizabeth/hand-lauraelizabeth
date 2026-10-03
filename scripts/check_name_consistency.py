from __future__ import annotations

from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OLD_TEXT = "Laura Hand"
OLD_FILENAME_TOKENS = ("Laura Hand", "Laura_Hand")
TEXT_EXTENSIONS = {
    ".md", ".txt", ".json", ".yml", ".yaml", ".py", ".html", ".css", ".js", ".xml", ".csv", ".tsv"
}
OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx"}

issues: list[str] = []

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue

    rel = path.relative_to(ROOT)
    rel_text = str(rel)

    if any(token in rel_text for token in OLD_FILENAME_TOKENS):
        issues.append(f"filename: {rel_text}")

    suffix = path.suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if OLD_TEXT in text:
            for line_no, line in enumerate(text.splitlines(), start=1):
                if OLD_TEXT in line:
                    issues.append(f"text: {rel_text}:{line_no}: {line.strip()[:220]}")

    elif suffix in OFFICE_EXTENSIONS:
        try:
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if not name.lower().endswith(".xml"):
                        continue
                    try:
                        root = ET.fromstring(archive.read(name))
                    except ET.ParseError:
                        continue
                    visible_text = "".join(root.itertext())
                    if OLD_TEXT in visible_text:
                        issues.append(f"office: {rel_text} -> {name}")
        except zipfile.BadZipFile:
            issues.append(f"invalid Office package: {rel_text}")

if issues:
    print("Found disallowed shortened-name references:")
    for issue in issues:
        print(f"- {issue}")
    sys.exit(1)

print("Name consistency check passed: no 'Laura Hand' text or filenames found.")
