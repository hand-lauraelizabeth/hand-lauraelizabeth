#!/usr/bin/env python3
"""Validate public Office resource files for basic integrity and publication safety."""

from pathlib import Path
from zipfile import ZipFile, BadZipFile
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
OFFICE_FILES = sorted(
    p for p in RESOURCES.rglob("*")
    if p.suffix.lower() in {".xlsx", ".docx"}
)

errors = []

def check_rels(zf: ZipFile, path: Path) -> None:
    for name in zf.namelist():
        if not name.endswith(".rels"):
            continue
        try:
            root = ET.fromstring(zf.read(name))
        except ET.ParseError as exc:
            errors.append(f"{path.relative_to(ROOT)}: malformed relationships XML {name}: {exc}")
            continue
        for rel in root:
            target = (rel.attrib.get("Target") or "").strip()
            mode = (rel.attrib.get("TargetMode") or "").strip().lower()
            lower = target.lower()
            if lower.startswith("file:") or lower.startswith("\\\\") or lower.startswith("/users/") or ":\\users\\" in lower:
                errors.append(f"{path.relative_to(ROOT)}: local-file relationship target in {name}: {target}")
            if mode == "external" and (lower.startswith("file:") or lower.startswith("\\\\")):
                errors.append(f"{path.relative_to(ROOT)}: external local-file relationship in {name}: {target}")

for path in OFFICE_FILES:
    rel = path.relative_to(ROOT)
    try:
        with ZipFile(path) as zf:
            names = set(zf.namelist())
            if path.suffix.lower() == ".xlsx":
                if "xl/workbook.xml" not in names:
                    errors.append(f"{rel}: missing xl/workbook.xml")
                if any(name.startswith("xl/externalLinks/") for name in names):
                    errors.append(f"{rel}: contains Excel external-link package parts")
            elif path.suffix.lower() == ".docx":
                if "word/document.xml" not in names:
                    errors.append(f"{rel}: missing word/document.xml")

            macro_parts = [
                name for name in names
                if name.lower().endswith("vbaproject.bin")
                or "activex/" in name.lower()
                or "embeddings/" in name.lower()
            ]
            if macro_parts:
                errors.append(f"{rel}: contains macro/embedded executable-style parts: {', '.join(macro_parts)}")

            check_rels(zf, path)
    except BadZipFile:
        errors.append(f"{rel}: not a valid Office Open XML ZIP package")

if not OFFICE_FILES:
    errors.append("No .xlsx or .docx files found under resources/")

if errors:
    print("Office resource validation failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(f"Validated {len(OFFICE_FILES)} Office resource files.")
