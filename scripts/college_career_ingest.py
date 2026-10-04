from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "college-career-matching"
MANIFEST_PATH = PROJECT / "source_manifest.json"
COVERAGE_BASELINES_PATH = PROJECT / "coverage_baselines.json"
DEFAULT_DATA_DIR = PROJECT / "data"

USER_AGENT = "LauraElizabethHand-CollegeCareerMatcher/0.2 (contact: https://github.com/hand-lauraelizabeth/hand-lauraelizabeth; public research data ingestion)"
SCORECARD_FIELDS = [
    "id",
    "school.name",
    "school.city",
    "school.state",
    "school.zip",
    "school.ownership",
    "school.locale",
    "school.degrees_awarded.predominant",
    "latest.student.size",
    "latest.student.faculty_ratio",
    "latest.admissions.admission_rate.overall",
    "latest.admissions.sat_scores.average.overall",
    "latest.admissions.sat_scores.25th_percentile.critical_reading",
    "latest.admissions.sat_scores.75th_percentile.critical_reading",
    "latest.admissions.sat_scores.25th_percentile.math",
    "latest.admissions.sat_scores.75th_percentile.math",
    "latest.admissions.act_scores.25th_percentile.cumulative",
    "latest.admissions.act_scores.75th_percentile.cumulative",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.avg_net_price.overall",
    "latest.completion.consumer_rate",
    "latest.student.retention_rate",
    "latest.aid.median_debt.completers.overall",
    "latest.earnings.6_yrs_after_entry.median",
    "latest.earnings.10_yrs_after_entry.median",
]


class IngestionError(RuntimeError):
    pass


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_coverage_baselines() -> dict:
    return json.loads(COVERAGE_BASELINES_PATH.read_text(encoding="utf-8"))


def nested_metric(report: dict, path: str) -> object | None:
    current: object = report
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def evaluate_coverage_baseline(layer: str, report: dict) -> dict:
    config = load_coverage_baselines()
    layer_config = config.get("layers", {}).get(layer)
    if not isinstance(layer_config, dict):
        raise IngestionError(f"No coverage baseline configured for layer: {layer}")

    checks: list[dict[str, object]] = []
    failures: list[str] = []
    for metric, minimum in layer_config.get("minimums", {}).items():
        actual = nested_metric(report, metric)
        try:
            numeric_actual = float(actual) if actual is not None else None
        except (TypeError, ValueError):
            numeric_actual = None
        passed = numeric_actual is not None and numeric_actual >= float(minimum)
        checks.append({
            "metric": metric,
            "actual": actual,
            "minimum": minimum,
            "status": "pass" if passed else "fail",
        })
        if not passed:
            failures.append(f"{metric}: actual={actual!r}, minimum={minimum!r}")

    return {
        "layer": layer,
        "baseline_as_of": config.get("as_of"),
        "reference": layer_config.get("reference"),
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
    }


def get_source(source_id: str) -> dict:
    for source in load_manifest()["sources"]:
        if source["source_id"] == source_id:
            return source
    raise IngestionError(f"Unknown source_id: {source_id}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename_from_url(url: str, fallback: str) -> str:
    name = Path(urllib.parse.urlparse(url).path).name
    return name or fallback


def http_get(url: str, *, headers: dict[str, str] | None = None, timeout: int = 90) -> bytes:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    request_headers = {"User-Agent": USER_AGENT}
    if host == "bls.gov" or host.endswith(".bls.gov"):
        request_headers.update({
            "User-Agent": os.getenv(
                "BLS_USER_AGENT",
                "LauraElizabethHand-CollegeCareerMatcher/0.3 (https://github.com/hand-lauraelizabeth/hand-lauraelizabeth)",
            ),
            "Accept": "application/zip,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain,*/*",
        })
    request_headers.update(headers or {})
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def http_post_json(url: str, payload: dict[str, object], *, timeout: int = 90) -> bytes:
    data = json.dumps(payload).encode("utf-8")
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    user_agent = USER_AGENT
    if host == "bls.gov" or host.endswith(".bls.gov"):
        user_agent = os.getenv(
            "BLS_USER_AGENT",
            "LauraElizabethHand-CollegeCareerMatcher/0.3 (https://github.com/hand-lauraelizabeth/hand-lauraelizabeth)",
        )
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "User-Agent": user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json, application/zip, application/octet-stream, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def http_json(url: str, payload: dict[str, object] | None = None, *, timeout: int = 90) -> object:
    raw = http_get(url, headers={"Accept": "application/json"}, timeout=timeout) if payload is None else http_post_json(url, payload, timeout=timeout)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IngestionError(f"Expected JSON from {url}, received non-JSON response") from exc


def resolve_access_url(source: dict) -> str:
    if source.get("access_url"):
        return str(source["access_url"])
    if source["source_id"].startswith("ipeds_") and source.get("file_stem"):
        return f"https://nces.ed.gov/ipeds/complete-data-files/{source['file_stem']}.zip"
    raise IngestionError(f"No downloadable access URL configured for {source['source_id']}")


def normalize_unitid(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    return digits or None


def normalize_opeid(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return digits.zfill(8) if len(digits) <= 8 else digits


def normalize_cip6(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    # IPEDS/CIP codes are a two-digit series plus a four-digit detail code.
    # Source files may serialize summary codes such as 99.0000 as "99";
    # left-padding the entire token would incorrectly turn that into 000099.
    decimal_match = re.fullmatch(r"(\d{1,2})(?:\.(\d{1,4}))?", text)
    if decimal_match:
        family = decimal_match.group(1).zfill(2)
        detail = (decimal_match.group(2) or "").ljust(4, "0")
        return family + detail

    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    if len(digits) < 6:
        digits = digits.zfill(6)
    return digits if len(digits) == 6 else None


def normalize_soc6(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"(\d{2})-(\d{4})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 6:
        return f"{digits[:2]}-{digits[2:6]}"
    return None


def value_status(value: object) -> str:
    if value is None:
        return "null"
    text = str(value).strip()
    if not text:
        return "null"
    if text.lower() in {"privacysuppressed", "#", "*", "**", "***", "n/a", "na"}:
        return "suppressed"
    return "reported"


def bls_value_status(value: object) -> str:
    if value is None:
        return "null"
    text = str(value).strip()
    if not text or text in {"—", "-", "–"}:
        return "null"
    if text == "**":
        return "topcoded"
    if text in {"*", "***", "#"}:
        return "suppressed"
    return "reported"


def parse_number(value: object) -> float | None:
    if bls_value_status(value) != "reported":
        return None
    text = str(value).strip().replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(text)
    except ValueError:
        return None


def read_csv_path(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def latest_snapshot_dir(output_dir: Path, source_id: str) -> Path:
    root = output_dir / source_id
    if not root.exists():
        raise IngestionError(f"No snapshots found for {source_id}: {root}")
    candidates = sorted(p for p in root.iterdir() if p.is_dir())
    if not candidates:
        raise IngestionError(f"No timestamped snapshots found for {source_id}: {root}")
    return candidates[-1]


def read_snapshot_metadata(snapshot_dir: Path) -> dict:
    path = snapshot_dir / "source_snapshot.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_dict(record: dict, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in record.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(flatten_dict(value, path))
        else:
            out[path] = value
    return out


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def first_csv_member(archive: zipfile.ZipFile) -> str:
    members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
    if not members:
        members = [n for n in archive.namelist() if n.lower().endswith(".txt")]
    if not members:
        raise IngestionError("ZIP contains no CSV/TXT table")
    return sorted(members)[0]


def read_delimited_bytes(data: bytes, *, delimiter: str | None = None) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig", errors="replace")
    sample = text[:8192]
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",\t|").delimiter
        except csv.Error:
            delimiter = ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def read_zip_table(data: bytes) -> tuple[str, list[dict[str, str]]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        member = first_csv_member(archive)
        raw = archive.read(member)
        delimiter = "\t" if member.lower().endswith(".txt") else None
        return member, read_delimited_bytes(raw, delimiter=delimiter)


def excel_column_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref.upper())
    if not letters:
        return 0
    n = 0
    for ch in letters.group(0):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx_rows_bytes(data: bytes, *, sheet_number: int = 1) -> list[list[str]]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in root.findall("main:si", ns):
                shared.append("".join(t.text or "" for t in si.iterfind(".//main:t", ns)))

        sheet_path = f"xl/worksheets/sheet{sheet_number}.xml"
        if sheet_path not in archive.namelist():
            raise IngestionError(f"Workbook has no {sheet_path}")
        root = ET.fromstring(archive.read(sheet_path))
        rows: list[list[str]] = []
        for row in root.findall(".//main:sheetData/main:row", ns):
            values: dict[int, str] = {}
            max_col = -1
            for cell in row.findall("main:c", ns):
                ref = cell.get("r", "")
                idx = excel_column_index(ref)
                max_col = max(max_col, idx)
                kind = cell.get("t")
                value = ""
                if kind == "inlineStr":
                    value = "".join(t.text or "" for t in cell.iterfind(".//main:t", ns))
                else:
                    v = cell.find("main:v", ns)
                    if v is not None and v.text is not None:
                        raw = v.text
                        if kind == "s":
                            try:
                                value = shared[int(raw)]
                            except (ValueError, IndexError):
                                value = raw
                        else:
                            value = raw
                values[idx] = value
            if max_col >= 0:
                rows.append([values.get(i, "") for i in range(max_col + 1)])
        return rows


def find_header_row(rows: list[list[str]], required_fragments: list[str]) -> tuple[int, list[str]]:
    lowered = [fragment.lower() for fragment in required_fragments]
    for idx, row in enumerate(rows):
        joined = " | ".join(str(v).lower() for v in row)
        if all(fragment in joined for fragment in lowered):
            return idx, [str(v).strip() for v in row]
    raise IngestionError(f"Could not find header row containing {required_fragments}")


def row_dicts_from_matrix(rows: list[list[str]], header_index: int, header: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows[header_index + 1 :]:
        padded = list(row) + [""] * max(0, len(header) - len(row))
        record = {header[i]: padded[i] for i in range(len(header)) if header[i]}
        if any(str(v).strip() for v in record.values()):
            out.append(record)
    return out


def write_snapshot_metadata(
    directory: Path,
    *,
    source: dict,
    source_url: str,
    raw_filename: str,
    raw_bytes: bytes,
    row_count_raw: int | None,
    extra: dict | None = None,
) -> dict:
    metadata = {
        "source_id": source["source_id"],
        "retrieved_at": utc_now(),
        "source_release": source["release"]["label"],
        "source_url": source_url,
        "raw_filename": raw_filename,
        "sha256": sha256_bytes(raw_bytes),
        "release_type": source["release"].get("label"),
        "reference_period": source["release"].get("label"),
        "parser_version": "prototype-0.1",
        "row_count_raw": row_count_raw,
    }
    if extra:
        metadata.update(extra)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "source_snapshot.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def count_values(rows: list[dict[str, object]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = "" if row.get(field) is None else str(row.get(field)).strip()
        key = value or "(blank)"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def community_college_pathway_flags(row: dict[str, object]) -> tuple[bool, list[str]]:
    """Broad, explainable coverage proxy; not a legal/mission designation."""
    if str(row.get("CONTROL", "")).strip() != "1":
        return False, []
    reasons: list[str] = []
    if str(row.get("SECTOR", "")).strip() == "4":
        reasons.append("public_two_year_sector")
    if str(row.get("INSTCAT", "")).strip() == "4":
        reasons.append("public_associates_certificates_instcat")
    c21basic = str(row.get("C21BASIC", "")).strip()
    if c21basic in {str(value) for value in range(1, 15)} | {"23"}:
        reasons.append("public_associate_or_bacc_assoc_carnegie")
    return bool(reasons), reasons


def build_ipeds_coverage_report(rows: list[dict[str, object]], source: dict) -> dict:
    def count_where(field: str, value: str) -> int:
        return sum(1 for row in rows if str(row.get(field, "")).strip() == value)

    states = count_values(rows, "STABBR")
    sector = count_values(rows, "SECTOR")
    control = count_values(rows, "CONTROL")
    level = count_values(rows, "ICLEVEL")
    degree = count_values(rows, "DEGGRANT")
    instcat = count_values(rows, "INSTCAT")

    community_candidates = []
    four_year_recovered = 0
    for row in rows:
        candidate, reasons = community_college_pathway_flags(row)
        if candidate:
            community_candidates.append(row)
            if (
                str(row.get("SECTOR", "")).strip() == "1"
                and (
                    "public_associates_certificates_instcat" in reasons
                    or "public_associate_or_bacc_assoc_carnegie" in reasons
                )
            ):
                four_year_recovered += 1

    return {
        "source_id": source["source_id"],
        "source_release": source["release"]["label"],
        "generated_at": utc_now(),
        "total_institution_records": len(rows),
        "states_and_territories_with_records": sum(1 for k in states if k != "(blank)"),
        "institution_counts_by_state_or_territory": states,
        "institution_counts_by_control_code": control,
        "institution_counts_by_sector_code": sector,
        "institution_counts_by_level_code": level,
        "institution_counts_by_degree_granting_code": degree,
        "institution_counts_by_instcat_code": instcat,
        "coverage_markers": {
            "public_four_year_or_above_sector_1": count_where("SECTOR", "1"),
            "private_nonprofit_four_year_or_above_sector_2": count_where("SECTOR", "2"),
            "private_for_profit_four_year_or_above_sector_3": count_where("SECTOR", "3"),
            "public_two_year_sector_4": count_where("SECTOR", "4"),
            "private_nonprofit_two_year_sector_5": count_where("SECTOR", "5"),
            "private_for_profit_two_year_sector_6": count_where("SECTOR", "6"),
            "public_less_than_two_year_sector_7": count_where("SECTOR", "7"),
            "private_nonprofit_less_than_two_year_sector_8": count_where("SECTOR", "8"),
            "private_for_profit_less_than_two_year_sector_9": count_where("SECTOR", "9"),
            "all_public_control_1": count_where("CONTROL", "1"),
            "all_private_nonprofit_control_2": count_where("CONTROL", "2"),
            "all_private_for_profit_control_3": count_where("CONTROL", "3"),
            "public_associates_certificates_instcat_4": sum(
                1 for row in rows
                if str(row.get("CONTROL", "")).strip() == "1"
                and str(row.get("INSTCAT", "")).strip() == "4"
            ),
            "public_associate_or_bacc_assoc_carnegie": sum(
                1 for row in rows
                if str(row.get("CONTROL", "")).strip() == "1"
                and str(row.get("C21BASIC", "")).strip() in {str(value) for value in range(1, 15)} | {"23"}
            ),
            "community_college_pathway_proxy_union": len(community_candidates),
            "four_year_sector_recovered_by_proxy": four_year_recovered,
        },
        "interpretation_notes": [
            "IPEDS public 2-year is not a complete synonym for community college.",
            "The community-college pathway proxy is a transparent union of public SECTOR=4, public INSTCAT=4, and public 2021 Carnegie Basic associate/baccalaureate-associate categories.",
            "Carnegie Basic codes 1-14 and 23 represent associate's, special-focus two-year, or baccalaureate/associate institutions; this adds an explicit pathway signal for public institutions that may sit in a four-year IPEDS sector.",
            "The proxy is a coverage layer, not a legal, state-system, or mission designation.",
            "These counts describe the complete ingested directory snapshot before prestige, selectivity, geography, or user-profile filtering."
        ],
    }

def qa_report(source_id: str, rows: list[dict[str, object]], key_fields: list[str]) -> dict:
    null_key_rows = 0
    seen: set[tuple[str, ...]] = set()
    duplicate_keys = 0
    for row in rows:
        key = tuple("" if row.get(k) is None else str(row.get(k)) for k in key_fields)
        if any(not part for part in key):
            null_key_rows += 1
        if key in seen:
            duplicate_keys += 1
        seen.add(key)
    if len(rows) == 0:
        status = "fail"
    elif null_key_rows == 0 and duplicate_keys == 0:
        status = "pass"
    else:
        status = "review"
    return {
        "source_id": source_id,
        "generated_at": utc_now(),
        "row_count": len(rows),
        "key_fields": key_fields,
        "null_key_rows": null_key_rows,
        "duplicate_key_rows": duplicate_keys,
        "status": status,
    }


def ingest_ipeds(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    member, records = read_zip_table(raw)
    normalized: list[dict[str, object]] = []

    if source["source_id"] == "ipeds_directory_2025":
        fields = [
            "UNITID", "INSTNM", "CITY", "STABBR", "ZIP", "CONTROL", "LOCALE",
            "SECTOR", "ICLEVEL", "HLOFFER", "DEGGRANT", "CYACTIVE", "ACT", "CLOSEDAT",
            "INSTCAT", "HDEGOFR1", "UGOFFER", "OPENPUBL", "OPEID", "C21BASIC"
        ]
        for row in records:
            normalized.append({
                "UNITID": normalize_unitid(row.get("UNITID")),
                "INSTNM": row.get("INSTNM"),
                "CITY": row.get("CITY"),
                "STABBR": row.get("STABBR"),
                "ZIP": row.get("ZIP"),
                "CONTROL": row.get("CONTROL"),
                "LOCALE": row.get("LOCALE"),
                "SECTOR": row.get("SECTOR"),
                "ICLEVEL": row.get("ICLEVEL"),
                "HLOFFER": row.get("HLOFFER"),
                "DEGGRANT": row.get("DEGGRANT"),
                "CYACTIVE": row.get("CYACTIVE"),
                "ACT": row.get("ACT"),
                "CLOSEDAT": row.get("CLOSEDAT"),
                "INSTCAT": row.get("INSTCAT"),
                "HDEGOFR1": row.get("HDEGOFR1"),
                "UGOFFER": row.get("UGOFFER"),
                "OPENPUBL": row.get("OPENPUBL"),
                "OPEID": row.get("OPEID"),
                "C21BASIC": row.get("C21BASIC"),
                "source_id": source["source_id"],
                "source_release": source["release"]["label"],
            })
        out = snapshot_dir / "normalized" / "institution.csv"
        write_csv(out, fields + ["source_id", "source_release"], normalized)
        report = qa_report(source["source_id"], normalized, ["UNITID"])
        coverage = build_ipeds_coverage_report(normalized, source)
    else:
        fields = ["UNITID", "MAJORNUM", "CIP6", "CIPCODE_RAW", "AWLEVEL", "CTOTALT"]
        for row in records:
            cip_raw = row.get("CIPCODE")
            normalized.append({
                "UNITID": normalize_unitid(row.get("UNITID")),
                "MAJORNUM": row.get("MAJORNUM"),
                "CIP6": normalize_cip6(cip_raw),
                "CIPCODE_RAW": cip_raw,
                "AWLEVEL": row.get("AWLEVEL"),
                "CTOTALT": row.get("CTOTALT"),
                "source_id": source["source_id"],
                "source_release": source["release"]["label"],
            })
        out = snapshot_dir / "normalized" / "program_completion.csv"
        write_csv(out, fields + ["source_id", "source_release"], normalized)
        report = qa_report(source["source_id"], normalized, ["UNITID", "MAJORNUM", "CIP6", "AWLEVEL"])

    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=member,
        raw_bytes=raw,
        row_count_raw=len(records),
        extra={"archive_member": member},
    )
    result = {"metadata": metadata, "qa": report, "normalized_rows": len(normalized)}
    if source["source_id"] == "ipeds_directory_2025":
        result["coverage"] = coverage
    return result


def ingest_cip_soc(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    def choose(record: dict[str, str], must_include: tuple[str, ...]) -> str | None:
        for key, value in record.items():
            low = key.lower()
            if all(token in low for token in must_include):
                return value
        return None

    chosen_sheet: int | None = None
    chosen_records: list[dict[str, str]] = []
    normalized: list[dict[str, object]] = []

    # The official workbook includes introductory material before the data sheet.
    # Search available worksheet XML files and accept the first sheet that
    # yields valid CIP-SOC pairs rather than assuming sheet1.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        sheet_numbers = sorted(
            int(match.group(1))
            for name in archive.namelist()
            if (match := re.fullmatch(r"xl/worksheets/sheet(\d+)\.xml", name))
        )

    for sheet_number in sheet_numbers:
        try:
            rows = read_xlsx_rows_bytes(raw, sheet_number=sheet_number)
            header_index, header = find_header_row(rows, ["cip", "soc"])
        except IngestionError:
            continue

        records = row_dicts_from_matrix(rows, header_index, header)
        candidate: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for record in records:
            cip_raw = choose(record, ("cip", "code"))
            soc_raw = choose(record, ("soc", "code"))
            cip = normalize_cip6(cip_raw)
            soc = normalize_soc6(soc_raw)
            if not cip or not soc:
                continue
            pair = (cip, soc)
            if pair in seen:
                continue
            seen.add(pair)
            candidate.append({
                "CIP6": cip,
                "SOC6": soc,
                "CIP_RAW": cip_raw,
                "SOC_RAW": soc_raw,
                "crosswalk_version": source["release"]["label"],
                "source_id": source["source_id"],
            })

        if candidate:
            chosen_sheet = sheet_number
            chosen_records = records
            normalized = candidate
            break

    if not normalized or chosen_sheet is None:
        raise IngestionError("CIP-SOC workbook contained no parseable CIP-SOC data rows")

    write_csv(
        snapshot_dir / "normalized" / "cip_soc_bridge.csv",
        ["CIP6", "SOC6", "CIP_RAW", "SOC_RAW", "crosswalk_version", "source_id"],
        normalized,
    )
    report = qa_report(source["source_id"], normalized, ["CIP6", "SOC6"])
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=safe_filename_from_url(source_url, "cip_soc_crosswalk.xlsx"),
        raw_bytes=raw,
        row_count_raw=len(chosen_records),
        extra={"worksheet_number": chosen_sheet},
    )
    return {"metadata": metadata, "qa": report, "normalized_rows": len(normalized)}

def ingest_onet(source: dict, snapshot_dir: Path) -> dict:
    file_urls = source.get("files") or {}
    if not file_urls:
        raise IngestionError("O*NET source has no configured files")

    raw_dir = snapshot_dir / "raw"
    normalized_dir = snapshot_dir / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    file_metadata: dict[str, dict[str, object]] = {}
    extracted: dict[str, int] = {}
    table_occupation_coverage: dict[str, int] = {}
    occupation_rows: list[dict[str, object]] = []

    for table_name, url in file_urls.items():
        payload = http_get(str(url))
        raw_name = safe_filename_from_url(str(url), f"{table_name}.csv")
        (raw_dir / raw_name).write_bytes(payload)
        file_metadata[table_name] = {
            "url": url,
            "raw_filename": raw_name,
            "sha256": sha256_bytes(payload),
            "bytes": len(payload),
        }

        rows = read_delimited_bytes(payload)
        normalized_rows: list[dict[str, object]] = []
        for row in rows:
            onet = (
                row.get("O*NET-SOC Code")
                or row.get("ONET_SOC_CODE")
                or row.get("O*NET-SOC_Code")
            )
            new_row: dict[str, object] = dict(row)
            new_row["ONET_SOC_CODE"] = onet
            new_row["SOC6"] = normalize_soc6(onet)
            new_row["onet_version"] = source["release"]["label"]
            new_row["source_id"] = source["source_id"]
            normalized_rows.append(new_row)

        if normalized_rows:
            fieldnames = list(normalized_rows[0].keys())
            write_csv(normalized_dir / f"{table_name}.csv", fieldnames, normalized_rows)
        extracted[table_name] = len(normalized_rows)
        table_occupation_coverage[table_name] = len({
            str(row.get("ONET_SOC_CODE"))
            for row in normalized_rows
            if row.get("ONET_SOC_CODE")
        })
        if table_name == "occupation_data":
            occupation_rows = normalized_rows

    if not occupation_rows:
        raise IngestionError("O*NET occupation_data produced no rows")

    combined_hash_input = "\n".join(
        f"{name}:{meta['sha256']}" for name, meta in sorted(file_metadata.items())
    ).encode("utf-8")
    snapshot_metadata = {
        "source_id": source["source_id"],
        "retrieved_at": utc_now(),
        "source_release": source["release"]["label"],
        "source_url": source["official_url"],
        "raw_filename": "multiple O*NET CSV files",
        "sha256": sha256_bytes(combined_hash_input),
        "release_type": source["release"]["label"],
        "reference_period": source["release"]["label"],
        "parser_version": "prototype-0.2",
        "row_count_raw": sum(extracted.values()),
        "files": file_metadata,
        "tables_extracted": extracted,
    }
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "source_snapshot.json").write_text(
        json.dumps(snapshot_metadata, indent=2) + "\n", encoding="utf-8"
    )

    report = qa_report(source["source_id"], occupation_rows, ["ONET_SOC_CODE"])
    coverage = {
        "source_id": source["source_id"],
        "source_release": source["release"]["label"],
        "generated_at": utc_now(),
        "total_detailed_occupations": len(occupation_rows),
        "occupations_with_base_soc6": sum(1 for row in occupation_rows if row.get("SOC6")),
        "table_row_counts": extracted,
        "occupations_represented_by_table": table_occupation_coverage,
        "coverage_notes": [
            "The baseline retains the full O*NET occupation table rather than filtering by wage, growth, prestige, or posting volume.",
            "Missing content in a secondary O*NET table is treated as a coverage gap, not a reason to remove an occupation from the universe.",
            "BLS projection, OEWS wage, and CIP-SOC linkage coverage are evaluated in later cross-source join reports."
        ],
    }
    return {
        "metadata": snapshot_metadata,
        "qa": report,
        "coverage": coverage,
        "normalized_rows": extracted,
    }

class SimpleHtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            text = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append(text)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
            self._cell = None


def parse_bls_projection_html(raw: bytes) -> list[list[str]]:
    parser = SimpleHtmlTableParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return [
        row for row in parser.rows
        if len(row) >= 8 and len(row) > 1 and re.fullmatch(r"\d{2}-\d{4}", str(row[1]).strip())
    ]


def ingest_bls_projection(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    raw_is_html = raw.lstrip().startswith((b"<!DOCTYPE", b"<!doctype", b"<html", b"<HTML"))
    all_rows: list[dict[str, object]] = []
    detailed_rows: list[dict[str, object]] = []

    if raw_is_html:
        records = parse_bls_projection_html(raw)
        if not records:
            raise IngestionError("BLS projections HTML contained no occupation rows")
        for row in records:
            padded = list(row) + [""] * max(0, 14 - len(row))
            raw_code = str(padded[1]).strip()
            soc = normalize_soc6(raw_code)
            if not soc:
                continue
            title = re.split(r"Show/hide Example Job Titles", str(padded[0]), maxsplit=1)[0].strip()
            is_detailed = raw_code != "00-0000"
            wage_raw = padded[7]
            item = {
                "SOC6": soc,
                "TITLE": title,
                "OCCUPATION_TYPE": "Line item" if is_detailed else "Summary",
                "IS_DETAILED": "1" if is_detailed else "0",
                "EMPLOYMENT_2025_THOUSANDS": parse_number(padded[2]),
                "EMPLOYMENT_2035_THOUSANDS": parse_number(padded[3]),
                "EMPLOYMENT_CHANGE_2025_2035_THOUSANDS": parse_number(padded[4]),
                "EMPLOYMENT_CHANGE_PERCENT_2025_2035": parse_number(padded[5]),
                "PCT_SELF_EMPLOYED_2025": None,
                "ANNUAL_OPENINGS_2025_2035_THOUSANDS": parse_number(padded[6]),
                "MEDIAN_ANNUAL_WAGE_2025": parse_number(wage_raw),
                "MEDIAN_ANNUAL_WAGE_2025_STATUS": bls_value_status(wage_raw),
                "TYPICAL_EDUCATION": padded[8] if len(padded) > 8 else "",
                "RELATED_WORK_EXPERIENCE": padded[10] if len(padded) > 10 else "",
                "ON_THE_JOB_TRAINING": padded[12] if len(padded) > 12 else "",
                "projection_cycle": source["release"]["label"],
                "source_id": source["source_id"],
            }
            all_rows.append(item)
            if is_detailed:
                detailed_rows.append(item)
        source_representation = "BLS Occupational Projections HTML database"
    else:
        rows = read_xlsx_rows_bytes(raw)
        data_start: int | None = None
        for idx, row in enumerate(rows):
            if len(row) > 2 and re.fullmatch(r"\d{2}-\d{4}", str(row[1]).strip()):
                data_start = idx
                break
        if data_start is None:
            raise IngestionError("BLS projection workbook contained no occupation data rows")
        header_text = " | ".join(
            " | ".join(str(value) for value in row)
            for row in rows[max(0, data_start - 6):data_start]
        ).lower()
        if not all(token in header_text for token in ("employment", "2025", "2035")):
            raise IngestionError("BLS projection workbook header signature changed")
        for row in rows[data_start:]:
            padded = list(row) + [""] * max(0, 16 - len(row))
            raw_code = str(padded[1]).strip()
            if not re.fullmatch(r"\d{2}-\d{4}", raw_code):
                continue
            soc = normalize_soc6(raw_code)
            if not soc:
                continue
            occupation_type = str(padded[2]).strip()
            is_detailed = occupation_type.lower() == "line item"
            wage_raw = padded[11]
            item = {
                "SOC6": soc,
                "TITLE": padded[0],
                "OCCUPATION_TYPE": occupation_type,
                "IS_DETAILED": "1" if is_detailed else "0",
                "EMPLOYMENT_2025_THOUSANDS": parse_number(padded[3]),
                "EMPLOYMENT_2035_THOUSANDS": parse_number(padded[4]),
                "EMPLOYMENT_CHANGE_2025_2035_THOUSANDS": parse_number(padded[7]),
                "EMPLOYMENT_CHANGE_PERCENT_2025_2035": parse_number(padded[8]),
                "PCT_SELF_EMPLOYED_2025": parse_number(padded[9]),
                "ANNUAL_OPENINGS_2025_2035_THOUSANDS": parse_number(padded[10]),
                "MEDIAN_ANNUAL_WAGE_2025": parse_number(wage_raw),
                "MEDIAN_ANNUAL_WAGE_2025_STATUS": bls_value_status(wage_raw),
                "TYPICAL_EDUCATION": padded[12],
                "RELATED_WORK_EXPERIENCE": padded[13],
                "ON_THE_JOB_TRAINING": padded[14],
                "projection_cycle": source["release"]["label"],
                "source_id": source["source_id"],
            }
            all_rows.append(item)
            if is_detailed:
                detailed_rows.append(item)
        source_representation = "BLS Table 1.2 XLSX"

    fields = [
        "SOC6", "TITLE", "OCCUPATION_TYPE", "IS_DETAILED",
        "EMPLOYMENT_2025_THOUSANDS", "EMPLOYMENT_2035_THOUSANDS",
        "EMPLOYMENT_CHANGE_2025_2035_THOUSANDS", "EMPLOYMENT_CHANGE_PERCENT_2025_2035",
        "PCT_SELF_EMPLOYED_2025", "ANNUAL_OPENINGS_2025_2035_THOUSANDS",
        "MEDIAN_ANNUAL_WAGE_2025", "MEDIAN_ANNUAL_WAGE_2025_STATUS",
        "TYPICAL_EDUCATION", "RELATED_WORK_EXPERIENCE", "ON_THE_JOB_TRAINING",
        "projection_cycle", "source_id",
    ]
    write_csv(snapshot_dir / "normalized" / "occupation_outlook_all.csv", fields, all_rows)
    write_csv(snapshot_dir / "normalized" / "occupation_outlook.csv", fields, detailed_rows)

    report = qa_report(source["source_id"], detailed_rows, ["SOC6"])
    report.update({
        "all_occupation_rows": len(all_rows),
        "detailed_line_item_rows": len(detailed_rows),
        "summary_or_other_rows_excluded_from_default_join": len(all_rows) - len(detailed_rows),
        "projection_base_year": 2025,
        "projection_end_year": 2035,
        "source_representation": source_representation,
    })
    if not detailed_rows:
        report["status"] = "fail"

    coverage = {
        "source_id": source["source_id"],
        "source_release": source["release"]["label"],
        "generated_at": utc_now(),
        "all_occupation_rows": len(all_rows),
        "detailed_line_item_rows": len(detailed_rows),
        "summary_or_other_rows": len(all_rows) - len(detailed_rows),
        "detailed_soc6_count": len({str(row["SOC6"]) for row in detailed_rows}),
        "notes": [
            "Only detailed occupation rows enter detailed occupation joins by default.",
            "Employment and annual-opening values retain the BLS thousands unit in field names.",
            "The live BLS projections database does not expose percent self-employed in its visible result table; that field stays null rather than being inferred.",
        ],
    }
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=safe_filename_from_url(source_url, "occupation-projections.html"),
        raw_bytes=raw,
        row_count_raw=len(all_rows),
        extra={
            "projection_base_year": 2025,
            "projection_end_year": 2035,
            "source_representation": source_representation,
        },
    )
    return {"metadata": metadata, "qa": report, "coverage": coverage, "normalized_rows": len(detailed_rows)}



def ingest_oews_query(source: dict, snapshot_dir: Path) -> dict:
    """Ingest the May 2025 national cross-industry OEWS baseline from BLS's live query service."""
    base = str(source.get("service_base_url") or "https://data.bls.gov").rstrip("/")
    area_code = "0000000"
    industry_code = "000000"
    release_key = str(source.get("release_query_key") or "2025A01")
    desired_datatypes = {
        "01": ("TOT_EMP", "TOT_EMP_STATUS"),
        "12": ("A_PCT25", "A_PCT25_STATUS"),
        "13": ("A_MEDIAN", "A_MEDIAN_STATUS"),
        "14": ("A_PCT75", "A_PCT75_STATUS"),
    }

    raw_dir = snapshot_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    occupation_payload = {"areaCodes": [area_code], "industryCodes": [industry_code]}
    occupation_response = http_json(f"{base}/OESServices/combo/occ", occupation_payload)
    if not isinstance(occupation_response, list) or not occupation_response:
        raise IngestionError("OEWS occupation query returned no rows")
    (raw_dir / "occupations.json").write_text(
        json.dumps(occupation_response, indent=2) + "\n", encoding="utf-8"
    )

    occupation_rows = [
        row for row in occupation_response
        if isinstance(row, dict)
        and str(row.get("displayLevel") or "") == "3"
        and re.fullmatch(r"\d{2}-\d{4}", str(row.get("formattedOccupationCode") or "").strip())
    ]
    if not occupation_rows:
        raise IngestionError("OEWS occupation query returned no detailed occupations")

    occupation_codes = [str(row["occupationCode"]) for row in occupation_rows]
    occupation_meta = {
        str(row["occupationCode"]): {
            "title": str(row.get("occupationName") or ""),
            "formatted_code": str(row.get("formattedOccupationCode") or ""),
            "display_level": str(row.get("displayLevel") or ""),
        }
        for row in occupation_rows
    }

    sample_occ = occupation_codes[0]
    datatype_payload = {
        "areaCodes": [area_code],
        "industryCodes": [industry_code],
        "occupationCodes": [sample_occ],
        "occupationExclude": False,
    }
    datatype_response = http_json(f"{base}/OESServices/combo/datatype", datatype_payload)
    if not isinstance(datatype_response, list):
        raise IngestionError("OEWS datatype query did not return a list")
    datatype_names = {
        str(row.get("datatypeCode") or ""): str(row.get("datatypeName") or "")
        for row in datatype_response if isinstance(row, dict)
    }
    missing_datatypes = set(desired_datatypes) - set(datatype_names)
    if missing_datatypes:
        raise IngestionError(f"OEWS query missing required datatypes: {sorted(missing_datatypes)}")
    (raw_dir / "datatypes.json").write_text(
        json.dumps(datatype_response, indent=2) + "\n", encoding="utf-8"
    )

    year_payload = {
        **datatype_payload,
        "datatypeCodes": list(desired_datatypes),
    }
    year_response = http_json(f"{base}/OESServices/combo/year", year_payload)
    if not isinstance(year_response, list) or not year_response:
        raise IngestionError("OEWS year query returned no releases")
    releases = {
        str(row.get("releaseDate") or ""): str(row.get("description") or "")
        for row in year_response if isinstance(row, dict)
    }
    if release_key not in releases:
        raise IngestionError(
            f"OEWS release {release_key} not returned by live query service; available={sorted(releases)}"
        )
    (raw_dir / "releases.json").write_text(
        json.dumps(year_response, indent=2) + "\n", encoding="utf-8"
    )

    records: dict[str, dict[str, object]] = {}
    raw_hashes: list[str] = []
    response_rows = 0
    batch_size = int(source.get("query_batch_size") or 200)
    for batch_number, start in enumerate(range(0, len(occupation_codes), batch_size), start=1):
        batch = occupation_codes[start:start + batch_size]
        payload = {
            "areaCodes": [area_code],
            "industryCodes": [industry_code],
            "occupationCodes": batch,
            "occupationExclude": False,
            "datatypeCodes": list(desired_datatypes),
            "releaseDates": [release_key],
            "tableSuffix": "pub",
            "userId": None,
            "pwd": None,
        }
        response = http_json(f"{base}/OESServices/combo/table", payload, timeout=180)
        if not isinstance(response, list):
            raise IngestionError(f"OEWS table batch {batch_number} did not return a list")
        raw_batch = json.dumps(response, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        raw_hashes.append(sha256_bytes(raw_batch))
        (raw_dir / f"table_batch_{batch_number:03d}.json").write_bytes(raw_batch + b"\n")
        response_rows += len(response)

        for row in response:
            if not isinstance(row, dict):
                continue
            occupation_code = str(row.get("occupationCode") or "")
            if occupation_code not in occupation_meta:
                continue
            datatype_code = str(row.get("datatypeCode") or "")
            if datatype_code not in desired_datatypes:
                continue
            meta = occupation_meta[occupation_code]
            soc = normalize_soc6(meta["formatted_code"] or occupation_code)
            if not soc:
                continue
            item = records.setdefault(occupation_code, {
                "AREA": area_code,
                "AREA_TITLE": "National",
                "AREA_TYPE": "National",
                "AREA_TYPE_CODE": "N",
                "STATE_CODE": "00",
                "OCC_CODE": soc,
                "OCC_TITLE": meta["title"],
                "O_GROUP": "detailed",
                "IS_DETAILED": "1",
                "reference_period": source["release"]["label"],
                "source_id": source["source_id"],
            })
            value_field, status_field = desired_datatypes[datatype_code]
            raw_value = row.get("value")
            item[value_field] = parse_number(raw_value)
            footnote = str(row.get("footnoteCodes") or "").strip()
            if parse_number(raw_value) is not None:
                item[status_field] = "reported"
            elif footnote:
                item[status_field] = f"unreported_footnote:{footnote}"
            else:
                item[status_field] = bls_value_status(raw_value)

    normalized = list(records.values())
    for item in normalized:
        for value_field, status_field in desired_datatypes.values():
            item.setdefault(value_field, None)
            item.setdefault(status_field, "null")

    fields = [
        "AREA", "AREA_TITLE", "AREA_TYPE", "AREA_TYPE_CODE", "STATE_CODE",
        "OCC_CODE", "OCC_TITLE", "O_GROUP", "IS_DETAILED",
        "TOT_EMP", "TOT_EMP_STATUS", "A_PCT25", "A_PCT25_STATUS",
        "A_MEDIAN", "A_MEDIAN_STATUS", "A_PCT75", "A_PCT75_STATUS",
        "reference_period", "source_id",
    ]
    write_csv(snapshot_dir / "normalized" / "occupation_wage.csv", fields, normalized)

    report = qa_report(source["source_id"], normalized, ["AREA_TYPE_CODE", "AREA", "OCC_CODE"])
    ordering_failures = 0
    for row in normalized:
        values = [row.get("A_PCT25"), row.get("A_MEDIAN"), row.get("A_PCT75")]
        if all(isinstance(value, (int, float)) for value in values):
            if not (float(values[0]) <= float(values[1]) <= float(values[2])):
                ordering_failures += 1
    report.update({
        "query_release_key": release_key,
        "query_release_description": releases[release_key],
        "query_occupation_rows": len(occupation_response),
        "detailed_occupations_requested": len(occupation_rows),
        "detailed_occupation_rows_normalized": len(normalized),
        "table_response_rows": response_rows,
        "query_batches": math.ceil(len(occupation_codes) / batch_size),
        "wage_percentile_ordering_failures": ordering_failures,
        "datatype_mapping": {code: datatype_names[code] for code in desired_datatypes},
    })
    if ordering_failures or len(normalized) != len(occupation_rows):
        report["status"] = "fail"

    coverage = {
        "source_id": source["source_id"],
        "source_release": source["release"]["label"],
        "generated_at": utc_now(),
        "geography": "National",
        "area_code": area_code,
        "industry_code": industry_code,
        "query_release_key": release_key,
        "query_occupation_rows_including_aggregates": len(occupation_response),
        "detailed_occupation_rows": len(normalized),
        "occupations_with_reported_employment": sum(1 for row in normalized if row["TOT_EMP_STATUS"] == "reported"),
        "occupations_with_reported_median_wage": sum(1 for row in normalized if row["A_MEDIAN_STATUS"] == "reported"),
        "notes": [
            "This automation-safe baseline uses the official BLS OEWS query service on data.bls.gov because the bulk download host blocks GitHub-hosted runners.",
            "The national cross-industry baseline uses area 0000000, industry 000000, and the May 2025 release key 2025A01.",
            "Only source displayLevel=3 occupations enter the detailed O*NET join.",
            "State, metropolitan, and nonmetropolitan expansion remains a separate geography layer; the normalized schema preserves geography explicitly.",
        ],
    }

    metadata_hash_input = "\n".join(
        [
            sha256_bytes(json.dumps(occupation_response, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
            sha256_bytes(json.dumps(datatype_response, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
            sha256_bytes(json.dumps(year_response, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
            *raw_hashes,
        ]
    ).encode("utf-8")
    metadata = {
        "source_id": source["source_id"],
        "retrieved_at": utc_now(),
        "source_release": source["release"]["label"],
        "source_url": str(source.get("access_url") or source["official_url"]),
        "raw_filename": "multiple OEWS query-service JSON responses",
        "sha256": sha256_bytes(metadata_hash_input),
        "release_type": source["release"]["label"],
        "reference_period": source["release"]["label"],
        "parser_version": "prototype-0.4",
        "row_count_raw": response_rows,
        "query_release_key": release_key,
        "query_geography": {"areaCode": area_code, "areaName": "National"},
        "query_industry": {"industryCode": industry_code, "industryName": "Cross-Industry"},
        "query_batch_size": batch_size,
        "query_batches": math.ceil(len(occupation_codes) / batch_size),
    }
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "source_snapshot.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return {"metadata": metadata, "qa": report, "coverage": coverage, "normalized_rows": len(normalized)}


def parse_tsv_mapping(raw: bytes) -> list[dict[str, str]]:
    return read_delimited_bytes(raw, delimiter="\t")


def ingest_oews_timeseries(
    source: dict,
    payloads: dict[str, bytes],
    snapshot_dir: Path,
) -> dict:
    area_rows = parse_tsv_mapping(payloads["area"])
    areatype_rows = parse_tsv_mapping(payloads["areatype"])
    occupation_rows = parse_tsv_mapping(payloads["occupation"])
    datatype_rows = parse_tsv_mapping(payloads["datatype"])
    release_rows = parse_tsv_mapping(payloads["release"])

    areas = {
        str(row.get("area_code") or "").strip(): {
            "state_code": str(row.get("state_code") or "").strip(),
            "areatype_code": str(row.get("areatype_code") or "").strip(),
            "area_name": str(row.get("area_name") or "").strip(),
        }
        for row in area_rows
        if row.get("area_code")
    }
    areatypes = {
        str(row.get("areatype_code") or "").strip(): str(row.get("areatype_name") or "").strip()
        for row in areatype_rows
        if row.get("areatype_code")
    }
    occupations = {
        str(row.get("occupation_code") or "").strip(): {
            "occupation_name": str(row.get("occupation_name") or "").strip(),
            "display_level": str(row.get("display_level") or "").strip(),
        }
        for row in occupation_rows
        if row.get("occupation_code")
    }
    datatypes = {
        str(row.get("datatype_code") or "").strip(): str(row.get("datatype_name") or "").strip()
        for row in datatype_rows
        if row.get("datatype_code")
    }

    desired_datatypes = {
        "01": ("TOT_EMP", "TOT_EMP_STATUS"),
        "04": ("A_MEAN", "A_MEAN_STATUS"),
        "11": ("A_PCT10", "A_PCT10_STATUS"),
        "12": ("A_PCT25", "A_PCT25_STATUS"),
        "13": ("A_MEDIAN", "A_MEDIAN_STATUS"),
        "14": ("A_PCT75", "A_PCT75_STATUS"),
        "15": ("A_PCT90", "A_PCT90_STATUS"),
    }
    records: dict[tuple[str, str, str], dict[str, object]] = {}
    observations_seen = 0
    observations_used = 0
    periods_seen: set[str] = set()
    years_seen: set[str] = set()

    with io.TextIOWrapper(io.BytesIO(payloads["data"]), encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            observations_seen += 1
            series_id = str(row.get("series_id") or "").strip()
            if len(series_id) < 25 or not series_id.startswith("OE"):
                continue
            year = str(row.get("year") or "").strip()
            period = str(row.get("period") or "").strip()
            years_seen.add(year)
            periods_seen.add(period)
            if year != "2025":
                continue

            areatype_code = series_id[3:4]
            area_code = series_id[4:11]
            industry_code = series_id[11:17]
            occupation_code = series_id[17:23]
            datatype_code = series_id[23:25]
            if industry_code != "000000" or datatype_code not in desired_datatypes:
                continue

            area = areas.get(area_code, {})
            occ = occupations.get(occupation_code, {})
            key = (areatype_code, area_code, occupation_code)
            item = records.setdefault(key, {
                "AREA": area_code,
                "AREA_TITLE": area.get("area_name", ""),
                "AREA_TYPE": areatypes.get(areatype_code, areatype_code),
                "AREA_TYPE_CODE": areatype_code,
                "STATE_CODE": area.get("state_code", ""),
                "OCC_CODE": normalize_soc6(occupation_code) or occupation_code,
                "OCC_TITLE": occ.get("occupation_name", ""),
                "O_GROUP": "detailed" if occ.get("display_level") == "3" else "aggregate",
                "IS_DETAILED": "1" if occ.get("display_level") == "3" else "0",
                "reference_period": source["release"]["label"],
                "source_id": source["source_id"],
            })
            value_field, status_field = desired_datatypes[datatype_code]
            raw_value = row.get("value")
            item[value_field] = parse_number(raw_value)
            footnote = str(row.get("footnote_codes") or "").strip()
            if parse_number(raw_value) is not None:
                item[status_field] = "reported"
            elif footnote:
                item[status_field] = f"unreported_footnote:{footnote}"
            else:
                item[status_field] = bls_value_status(raw_value)
            observations_used += 1

    normalized = list(records.values())
    for item in normalized:
        for value_field, status_field in desired_datatypes.values():
            item.setdefault(value_field, None)
            item.setdefault(status_field, "null")

    fields = [
        "AREA", "AREA_TITLE", "AREA_TYPE", "AREA_TYPE_CODE", "STATE_CODE",
        "OCC_CODE", "OCC_TITLE", "O_GROUP", "IS_DETAILED",
        "TOT_EMP", "TOT_EMP_STATUS", "A_MEAN", "A_MEAN_STATUS",
        "A_PCT10", "A_PCT10_STATUS", "A_PCT25", "A_PCT25_STATUS",
        "A_MEDIAN", "A_MEDIAN_STATUS", "A_PCT75", "A_PCT75_STATUS",
        "A_PCT90", "A_PCT90_STATUS", "reference_period", "source_id",
    ]
    write_csv(snapshot_dir / "normalized" / "occupation_wage.csv", fields, normalized)

    report = qa_report(source["source_id"], normalized, ["AREA_TYPE_CODE", "AREA", "OCC_CODE"])
    detailed = [row for row in normalized if row["IS_DETAILED"] == "1"]
    ordering_failures = 0
    for row in detailed:
        values = [row.get("A_PCT25"), row.get("A_MEDIAN"), row.get("A_PCT75")]
        if all(isinstance(value, (int, float)) for value in values):
            if not (float(values[0]) <= float(values[1]) <= float(values[2])):
                ordering_failures += 1

    area_title_pairs: dict[tuple[str, str], set[str]] = {}
    for row in normalized:
        key = (str(row.get("AREA_TYPE_CODE") or ""), str(row.get("AREA") or ""))
        area_title_pairs.setdefault(key, set()).add(str(row.get("AREA_TITLE") or ""))
    area_title_conflicts = sum(1 for titles in area_title_pairs.values() if len(titles) > 1)

    report.update({
        "observations_seen": observations_seen,
        "observations_used_cross_industry_2025": observations_used,
        "years_seen": sorted(years_seen),
        "periods_seen": sorted(periods_seen),
        "detailed_occupation_rows": len(detailed),
        "aggregate_occupation_rows": len(normalized) - len(detailed),
        "wage_percentile_ordering_failures": ordering_failures,
        "area_title_conflicts": area_title_conflicts,
        "datatype_mapping": {code: datatypes.get(code, "") for code in desired_datatypes},
    })
    if ordering_failures or area_title_conflicts or not detailed:
        report["status"] = "fail"

    area_type_groups: dict[str, dict[str, object]] = {}
    for row in detailed:
        area_type = str(row.get("AREA_TYPE") or "(blank)")
        group = area_type_groups.setdefault(area_type, {"rows": 0, "areas": set(), "soc6": set()})
        group["rows"] = int(group["rows"]) + 1
        group["areas"].add(str(row["AREA"]))
        group["soc6"].add(str(row["OCC_CODE"]))
    coverage_by_area_type = {
        key: {
            "detailed_rows": int(value["rows"]),
            "unique_areas": len(value["areas"]),
            "unique_detailed_soc6": len(value["soc6"]),
        }
        for key, value in sorted(area_type_groups.items())
    }
    coverage = {
        "source_id": source["source_id"],
        "source_release": source["release"]["label"],
        "generated_at": utc_now(),
        "all_cross_industry_rows": len(normalized),
        "detailed_occupation_rows": len(detailed),
        "coverage_by_area_type": coverage_by_area_type,
        "release_mapping": release_rows,
        "notes": [
            "The current OEWS time-series file is decoded from documented series-id positions; the 1.2 GB oe.series file is not required.",
            "Only industry_code 000000 (cross-industry) observations for reference year 2025 are normalized.",
            "Source display_level=3 defines detailed occupations; aggregate occupation rows remain available but are excluded from detailed O*NET joins.",
            "Suppressed or otherwise unreported estimates remain null numerically with an explicit status/footnote state.",
        ],
    }

    file_metadata = {
        name: {
            "url": source["files"][name],
            "raw_filename": safe_filename_from_url(source["files"][name], name),
            "sha256": sha256_bytes(payload),
            "bytes": len(payload),
        }
        for name, payload in payloads.items()
    }
    combined_hash_input = "\n".join(
        f"{name}:{meta['sha256']}" for name, meta in sorted(file_metadata.items())
    ).encode("utf-8")
    metadata = {
        "source_id": source["source_id"],
        "retrieved_at": utc_now(),
        "source_release": source["release"]["label"],
        "source_url": source["official_url"],
        "raw_filename": "multiple BLS OEWS time-series files",
        "sha256": sha256_bytes(combined_hash_input),
        "release_type": source["release"]["label"],
        "reference_period": source["release"]["label"],
        "parser_version": "prototype-0.3",
        "row_count_raw": observations_seen,
        "files": file_metadata,
        "periods_seen": sorted(periods_seen),
    }
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "source_snapshot.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"metadata": metadata, "qa": report, "coverage": coverage, "normalized_rows": len(normalized)}

def _row_value(row: dict[str, str], *names: str) -> str | None:
    normalized = {
        re.sub(r"[^a-z0-9]", "", str(key).lower()): value
        for key, value in row.items()
    }
    for name in names:
        value = normalized.get(re.sub(r"[^a-z0-9]", "", name.lower()))
        if value is not None:
            return value
    return None

def ingest_dapip(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    expected = {
        "institutioncampus.csv": "institution_campus",
        "accreditationrecords.csv": "accreditation_records",
        "accreditationactions.csv": "accreditation_actions",
    }
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        by_basename = {Path(name).name.lower(): name for name in archive.namelist()}
        missing = set(expected) - set(by_basename)
        if missing:
            raise IngestionError(f"DAPIP ZIP missing expected files: {sorted(missing)}")
        source_tables = {
            table_name: read_delimited_bytes(archive.read(by_basename[filename]))
            for filename, table_name in expected.items()
        }

    def pick(row: dict[str, str], *names: str) -> str | None:
        return _row_value(row, *names)

    campus_rows: list[dict[str, object]] = []
    bridge_rows: list[dict[str, object]] = []
    seen_bridge: set[tuple[str, str]] = set()
    for row in source_tables["institution_campus"]:
        dapip_id = pick(row, "DapipId", "DAPIPID", "DAPIP ID")
        unitids_raw = pick(
            row,
            "IpedsUnitIds",
            "IPEDSUnitIds",
            "IPEDS Unit IDs",
            "IPEDSUnitID",
            "IPEDS Unit ID",
            "IPEDSUnitId",
        )
        unitids = []
        for token in re.split(r"[,;|]", str(unitids_raw or "")):
            unitid = normalize_unitid(token)
            if unitid and unitid not in unitids:
                unitids.append(unitid)
        campus_rows.append({
            "DAPIP_ID": dapip_id,
            "PARENT_DAPIP_ID": pick(row, "ParentDapipId", "Parent Dapip Id", "Parent DAPIP ID"),
            "IPEDS_UNIT_IDS_RAW": unitids_raw,
            "IPEDS_UNIT_ID_COUNT": len(unitids),
            "INSTITUTION_NAME": pick(row, "InstitutionName", "ParentName", "Institution Name"),
            "LOCATION_NAME": pick(row, "LocationName", "Location Name"),
            "LOCATION_TYPE": pick(row, "LocationType", "Location Type"),
            "ADDRESS": pick(row, "Address"),
            "OPEID": pick(row, "OpeId", "OPEID", "OPE ID"),
            "source_id": source["source_id"],
        })
        for unitid in unitids:
            pair = (str(dapip_id or ""), unitid)
            if not pair[0] or pair in seen_bridge:
                continue
            seen_bridge.add(pair)
            bridge_rows.append({
                "DAPIP_ID": pair[0],
                "UNITID": unitid,
                "source_id": source["source_id"],
            })

    accreditation_rows: list[dict[str, object]] = []
    for row in source_tables["accreditation_records"]:
        program_id = pick(row, "ProgramId", "Program ID")
        program_name = pick(row, "ProgramName", "Program Name")
        end_date = pick(row, "AccreditationEndDate", "Accreditation End Date", "EndDate", "End Date")
        status = pick(row, "AccreditationStatus", "Status")
        institutional = (
            str(program_id or "").strip() == "1"
            or "institutional" in str(program_name or "").lower()
        )
        status_text = str(status or "").lower()
        source_current = not end_date and not any(
            term in status_text for term in ("expired", "withdrawn", "terminated", "inactive", "closed")
        )
        accreditation_rows.append({
            "DAPIP_ID": pick(row, "DapipId", "DAPIPID", "DAPIP ID"),
            "AGENCY_ID": pick(row, "AgencyId", "Agency ID"),
            "AGENCY_NAME": pick(row, "AgencyName", "Agency Name"),
            "PROGRAM_ID": program_id,
            "PROGRAM_NAME": program_name,
            "ACCREDITATION_STATUS": status,
            "ACCREDITATION_DATE": pick(row, "AccreditationDate", "Accreditation Date", "InitialDate"),
            "ACCREDITATION_END_DATE": end_date,
            "NEXT_REVIEW_DATE": pick(row, "NextReviewDate", "Next Review Date", "DateOfNextReview"),
            "IS_INSTITUTIONAL": "1" if institutional else "0",
            "IS_CURRENT_BY_EXPORT_RULE": "1" if source_current else "0",
            "source_id": source["source_id"],
        })

    action_rows: list[dict[str, object]] = []
    for row in source_tables["accreditation_actions"]:
        action_rows.append({
            "DAPIP_ID": pick(row, "DapipId", "DAPIPID", "DAPIP ID"),
            "AGENCY_ID": pick(row, "AgencyId", "Agency ID"),
            "AGENCY_NAME": pick(row, "AgencyName", "Agency Name"),
            "PROGRAM_ID": pick(row, "ProgramId", "Program ID"),
            "PROGRAM_NAME": pick(row, "ProgramName", "Program Name"),
            "ACTION_DESCRIPTION": pick(row, "ActionDescription", "Action Description"),
            "ACTION_DATE": pick(row, "ActionDate", "Action Date"),
            "END_DATE": pick(row, "EndDate", "End Date"),
            "JUSTIFICATION": pick(row, "Justification"),
            "source_id": source["source_id"],
        })

    write_csv(
        snapshot_dir / "normalized" / "institution_campus.csv",
        ["DAPIP_ID", "PARENT_DAPIP_ID", "IPEDS_UNIT_IDS_RAW", "IPEDS_UNIT_ID_COUNT", "INSTITUTION_NAME", "LOCATION_NAME", "LOCATION_TYPE", "ADDRESS", "OPEID", "source_id"],
        campus_rows,
    )
    write_csv(
        snapshot_dir / "normalized" / "dapip_ipeds_bridge.csv",
        ["DAPIP_ID", "UNITID", "source_id"],
        bridge_rows,
    )
    write_csv(
        snapshot_dir / "normalized" / "accreditation_records.csv",
        ["DAPIP_ID", "AGENCY_ID", "AGENCY_NAME", "PROGRAM_ID", "PROGRAM_NAME", "ACCREDITATION_STATUS", "ACCREDITATION_DATE", "ACCREDITATION_END_DATE", "NEXT_REVIEW_DATE", "IS_INSTITUTIONAL", "IS_CURRENT_BY_EXPORT_RULE", "source_id"],
        accreditation_rows,
    )
    write_csv(
        snapshot_dir / "normalized" / "accreditation_actions.csv",
        ["DAPIP_ID", "AGENCY_ID", "AGENCY_NAME", "PROGRAM_ID", "PROGRAM_NAME", "ACTION_DESCRIPTION", "ACTION_DATE", "END_DATE", "JUSTIFICATION", "source_id"],
        action_rows,
    )

    campus_ids = {str(row["DAPIP_ID"]) for row in campus_rows if row.get("DAPIP_ID")}
    action_ids = {str(row["DAPIP_ID"]) for row in action_rows if row.get("DAPIP_ID")}
    report = {
        "source_id": source["source_id"],
        "generated_at": utc_now(),
        "campus_rows": len(campus_rows),
        "accreditation_record_rows": len(accreditation_rows),
        "action_rows": len(action_rows),
        "campus_rows_with_unitid": sum(1 for row in campus_rows if int(row.get("IPEDS_UNIT_ID_COUNT") or 0) > 0),
        "dapip_ipeds_bridge_rows": len(bridge_rows),
        "actions_with_campus_dapip_match": sum(1 for row in action_rows if str(row.get("DAPIP_ID") or "") in campus_ids),
        "action_dapip_ids_not_in_campus_table": len(action_ids - campus_ids),
        "status": "pass" if campus_rows and accreditation_rows else "fail",
    }
    coverage = {
        "source_id": source["source_id"],
        "source_release": source["release"]["label"],
        "generated_at": utc_now(),
        "unique_dapip_ids": len(campus_ids),
        "unique_ipeds_unitids": len({str(row["UNITID"]) for row in bridge_rows if row.get("UNITID")}),
        "institutional_accreditation_records": sum(1 for row in accreditation_rows if row["IS_INSTITUTIONAL"] == "1"),
        "current_institutional_records_by_export_rule": sum(
            1 for row in accreditation_rows
            if row["IS_INSTITUTIONAL"] == "1" and row["IS_CURRENT_BY_EXPORT_RULE"] == "1"
        ),
        "interpretation_notes": [
            "DAPIP and IPEDS identifiers are retained separately because one DAPIP entity can map to multiple IPEDS UNITIDs.",
            "The current-by-export rule is intentionally conservative and is not a substitute for verifying a specific institution with DAPIP or the accreditor.",
            "Programmatic accreditation is retained separately from institutional accreditation.",
        ],
    }
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename="DAPIPData.zip",
        raw_bytes=raw,
        row_count_raw=sum(len(rows) for rows in source_tables.values()),
        extra={"archive_members": sorted(by_basename.values())},
    )
    return {"metadata": metadata, "qa": report, "coverage": coverage, "normalized_rows": {
        "institution_campus": len(campus_rows),
        "dapip_ipeds_bridge": len(bridge_rows),
        "accreditation_records": len(accreditation_rows),
        "accreditation_actions": len(action_rows),
    }}


def build_career_join_report(output_dir: Path, *, enforce_baseline: bool = False) -> dict:
    onet_dir = latest_snapshot_dir(output_dir, "onet_31_0")
    ep_dir = latest_snapshot_dir(output_dir, "bls_employment_projections_2025_2035")
    oews_dir = latest_snapshot_dir(output_dir, "bls_oews_may_2025")

    onet = read_csv_path(onet_dir / "normalized" / "occupation_data.csv")
    projections = read_csv_path(ep_dir / "normalized" / "occupation_outlook.csv")
    oews = read_csv_path(oews_dir / "normalized" / "occupation_wage.csv")

    onet_soc = {str(row.get("SOC6") or "") for row in onet if row.get("SOC6")}
    ep_soc = {str(row.get("SOC6") or "") for row in projections if row.get("SOC6")}
    projection_overlap = onet_soc & ep_soc

    oews_by_area_type: dict[str, set[str]] = {}
    oews_areas_by_type: dict[str, set[str]] = {}
    for row in oews:
        if str(row.get("IS_DETAILED") or "") != "1":
            continue
        area_type = str(row.get("AREA_TYPE") or "(blank)")
        oews_by_area_type.setdefault(area_type, set()).add(str(row.get("OCC_CODE") or ""))
        oews_areas_by_type.setdefault(area_type, set()).add(str(row.get("AREA") or ""))

    def rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 6) if denominator else None

    oews_coverage = {}
    for area_type, socs in sorted(oews_by_area_type.items()):
        overlap = onet_soc & socs
        oews_coverage[area_type] = {
            "unique_areas": len(oews_areas_by_type.get(area_type, set())),
            "oews_detailed_soc6": len(socs),
            "onet_soc6_overlap": len(overlap),
            "onet_base_soc6_match_rate": rate(len(overlap), len(onet_soc)),
        }

    report = {
        "generated_at": utc_now(),
        "sources": {
            "onet_snapshot": str(onet_dir),
            "employment_projections_snapshot": str(ep_dir),
            "oews_snapshot": str(oews_dir),
        },
        "onet": {
            "occupation_rows": len(onet),
            "unique_base_soc6": len(onet_soc),
        },
        "onet_to_bls_employment_projections": {
            "bls_detailed_soc6": len(ep_soc),
            "overlap_soc6": len(projection_overlap),
            "onet_base_soc6_match_rate": rate(len(projection_overlap), len(onet_soc)),
            "unmatched_onet_soc6": sorted(onet_soc - ep_soc),
            "bls_detailed_soc6_not_in_onet": sorted(ep_soc - onet_soc),
        },
        "onet_to_oews_by_area_type": oews_coverage,
        "join_rules": [
            "O*NET extension occupations join through explicit base SOC6 normalization.",
            "BLS projection summary rows and OEWS aggregate occupation rows are excluded from detailed joins.",
            "OEWS geography is preserved; coverage is reported separately by source AREA_TYPE.",
        ],
    }
    baseline = evaluate_coverage_baseline("career", report)
    report["baseline_validation"] = baseline
    out_dir = output_dir / "_joins" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "career_source_coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if enforce_baseline and baseline["status"] != "pass":
        raise IngestionError("Career coverage regression gate failed: " + "; ".join(baseline["failures"]))
    return {"report": report, "output": str(out_dir / "career_source_coverage.json")}


def build_institution_coverage_report(output_dir: Path, *, enforce_baseline: bool = False) -> dict:
    ipeds_dir = latest_snapshot_dir(output_dir, "ipeds_directory_2025")
    dapip_dir = latest_snapshot_dir(output_dir, "dapip_accreditation")
    institutions = read_csv_path(ipeds_dir / "normalized" / "institution.csv")
    bridge = read_csv_path(dapip_dir / "normalized" / "dapip_ipeds_bridge.csv")
    accreditation = read_csv_path(dapip_dir / "normalized" / "accreditation_records.csv")

    dapip_by_unitid: dict[str, set[str]] = {}
    for row in bridge:
        unitid = str(row.get("UNITID") or "")
        dapip_id = str(row.get("DAPIP_ID") or "")
        if unitid and dapip_id:
            dapip_by_unitid.setdefault(unitid, set()).add(dapip_id)

    current_institutional = {
        str(row.get("DAPIP_ID") or "")
        for row in accreditation
        if str(row.get("IS_INSTITUTIONAL") or "") == "1"
        and str(row.get("IS_CURRENT_BY_EXPORT_RULE") or "") == "1"
        and row.get("DAPIP_ID")
    }

    flags: list[dict[str, object]] = []
    for row in institutions:
        unitid = str(row.get("UNITID") or "")
        dapip_ids = dapip_by_unitid.get(unitid, set())
        candidate, reasons = community_college_pathway_flags(row)
        has_current = any(dapip_id in current_institutional for dapip_id in dapip_ids)
        flags.append({
            "UNITID": unitid,
            "INSTNM": row.get("INSTNM"),
            "STABBR": row.get("STABBR"),
            "CONTROL": row.get("CONTROL"),
            "SECTOR": row.get("SECTOR"),
            "INSTCAT": row.get("INSTCAT"),
            "DAPIP_MATCH": "1" if dapip_ids else "0",
            "DAPIP_IDS": "|".join(sorted(dapip_ids)),
            "CURRENT_INSTITUTIONAL_ACCREDITATION_BY_EXPORT_RULE": "1" if has_current else "0",
            "COMMUNITY_COLLEGE_PATHWAY_PROXY": "1" if candidate else "0",
            "COMMUNITY_COLLEGE_PROXY_REASONS": "|".join(reasons),
        })

    community = [row for row in flags if row["COMMUNITY_COLLEGE_PATHWAY_PROXY"] == "1"]
    report = {
        "generated_at": utc_now(),
        "sources": {
            "ipeds_snapshot": str(ipeds_dir),
            "dapip_snapshot": str(dapip_dir),
        },
        "institution_universe": len(flags),
        "institutions_with_dapip_id_match": sum(1 for row in flags if row["DAPIP_MATCH"] == "1"),
        "institutions_with_current_institutional_accreditation_by_export_rule": sum(
            1 for row in flags if row["CURRENT_INSTITUTIONAL_ACCREDITATION_BY_EXPORT_RULE"] == "1"
        ),
        "community_college_pathway_proxy": {
            "count": len(community),
            "with_dapip_id_match": sum(1 for row in community if row["DAPIP_MATCH"] == "1"),
            "with_current_institutional_accreditation_by_export_rule": sum(
                1 for row in community if row["CURRENT_INSTITUTIONAL_ACCREDITATION_BY_EXPORT_RULE"] == "1"
            ),
            "public_two_year_sector": sum(
                1 for row in community if "public_two_year_sector" in str(row["COMMUNITY_COLLEGE_PROXY_REASONS"])
            ),
            "public_associates_certificates_instcat": sum(
                1 for row in community if "public_associates_certificates_instcat" in str(row["COMMUNITY_COLLEGE_PROXY_REASONS"])
            ),
            "public_associate_or_bacc_assoc_carnegie": sum(
                1 for row in community if "public_associate_or_bacc_assoc_carnegie" in str(row["COMMUNITY_COLLEGE_PROXY_REASONS"])
            ),
            "four_year_sector_recovered_by_proxy": sum(
                1 for row in community
                if str(row.get("SECTOR")) == "1"
                and (
                    "public_associates_certificates_instcat" in str(row["COMMUNITY_COLLEGE_PROXY_REASONS"])
                    or "public_associate_or_bacc_assoc_carnegie" in str(row["COMMUNITY_COLLEGE_PROXY_REASONS"])
                )
            ),
        },
        "interpretation_notes": [
            "The community-college pathway proxy is deliberately broader than SECTOR=4 and deliberately narrower than a name-based search.",
            "It is a discovery/coverage flag, not a claim that an institution is legally designated a community college.",
            "Accreditation status is kept as a separate layer and should be verified for high-stakes enrollment decisions.",
        ],
    }
    out_dir = output_dir / "_institution_coverage" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_csv(
        out_dir / "institution_coverage_flags.csv",
        ["UNITID", "INSTNM", "STABBR", "CONTROL", "SECTOR", "INSTCAT", "DAPIP_MATCH", "DAPIP_IDS",
         "CURRENT_INSTITUTIONAL_ACCREDITATION_BY_EXPORT_RULE", "COMMUNITY_COLLEGE_PATHWAY_PROXY",
         "COMMUNITY_COLLEGE_PROXY_REASONS"],
        flags,
    )
    baseline = evaluate_coverage_baseline("institution", report)
    report["baseline_validation"] = baseline
    (out_dir / "institution_coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if enforce_baseline and baseline["status"] != "pass":
        raise IngestionError("Institution coverage regression gate failed: " + "; ".join(baseline["failures"]))
    return {"report": report, "output": str(out_dir / "institution_coverage.json")}


def build_program_coverage_report(output_dir: Path, *, enforce_baseline: bool = False) -> dict:
    """Report program/completion coverage without treating missing mappings as quality failures."""
    institution_dir = latest_snapshot_dir(output_dir, "ipeds_directory_2025")
    completion_dir = latest_snapshot_dir(output_dir, "ipeds_completions_2025")
    crosswalk_dir = latest_snapshot_dir(output_dir, "cip_soc_crosswalk_2020_2018")

    institutions = read_csv_path(institution_dir / "normalized" / "institution.csv")
    completions = read_csv_path(completion_dir / "normalized" / "program_completion.csv")
    bridge = read_csv_path(crosswalk_dir / "normalized" / "cip_soc_bridge.csv")

    institution_ids = {
        str(row.get("UNITID") or "")
        for row in institutions
        if row.get("UNITID")
    }

    bridge_by_cip: dict[str, set[str]] = {}
    for row in bridge:
        cip = str(row.get("CIP6") or "")
        soc = str(row.get("SOC6") or "")
        if cip and soc:
            bridge_by_cip.setdefault(cip, set()).add(soc)

    program_rows: dict[tuple[str, str, str], int] = {}
    summary_cip_rows_excluded = 0
    second_major_rows_excluded = 0
    incomplete_key_rows_excluded = 0
    for row in completions:
        unitid = str(row.get("UNITID") or "")
        major_num = str(row.get("MAJORNUM") or "").strip()
        cip = str(row.get("CIP6") or "")
        award = str(row.get("AWLEVEL") or "")
        # 99.0000 is an IPEDS summary/total code, not a specific field of study.
        if cip in {"990000", "000099"}:
            summary_cip_rows_excluded += 1
            continue
        # Program availability uses first-major records. Second-major rows are
        # retained in the normalized source but kept out of the default
        # institution-program grain so they cannot double-count a program.
        if major_num == "2":
            second_major_rows_excluded += 1
            continue
        if major_num not in {"", "1"}:
            incomplete_key_rows_excluded += 1
            continue
        if not unitid or not cip or not award:
            incomplete_key_rows_excluded += 1
            continue
        key = (unitid, cip, award)
        program_rows[key] = program_rows.get(key, 0) + 1

    program_keys = sorted(program_rows)
    program_unitids = {unitid for unitid, _, _ in program_keys}
    observed_cips = {cip for _, cip, _ in program_keys}
    mapped_observed_cips = observed_cips & set(bridge_by_cip)
    unmapped_observed_cips = observed_cips - set(bridge_by_cip)

    mapped_programs = [
        key for key in program_keys
        if key[1] in bridge_by_cip
    ]
    unmapped_programs = [
        key for key in program_keys
        if key[1] not in bridge_by_cip
    ]

    institutions_with_mapped_programs = {unitid for unitid, _, _ in mapped_programs}
    institutions_with_only_unmapped_programs = program_unitids - institutions_with_mapped_programs

    def rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 6) if denominator else None

    award_level_coverage: dict[str, dict[str, object]] = {}
    for award in sorted({award for _, _, award in program_keys}):
        award_keys = [key for key in program_keys if key[2] == award]
        mapped = sum(1 for _, cip, _ in award_keys if cip in bridge_by_cip)
        award_level_coverage[award] = {
            "program_combinations": len(award_keys),
            "with_direct_cip_soc_mapping": mapped,
            "without_direct_cip_soc_mapping": len(award_keys) - mapped,
            "direct_mapping_rate": rate(mapped, len(award_keys)),
        }

    flags = [
        {
            "UNITID": unitid,
            "CIP6": cip,
            "AWLEVEL": award,
            "DIRECT_CIP_SOC_MAPPING": "1" if cip in bridge_by_cip else "0",
            "SOC6_COUNT": len(bridge_by_cip.get(cip, set())),
            "SOURCE_ROW_COUNT": program_rows[(unitid, cip, award)],
        }
        for unitid, cip, award in program_keys
    ]

    observed_bridge_pairs = sum(
        len(bridge_by_cip[cip])
        for cip in observed_cips
        if cip in bridge_by_cip
    )

    report = {
        "generated_at": utc_now(),
        "sources": {
            "institution_snapshot": str(institution_dir),
            "completion_snapshot": str(completion_dir),
            "cip_soc_crosswalk_snapshot": str(crosswalk_dir),
        },
        "institution_universe": len(institution_ids),
        "completion_source_rows": len(completions),
        "summary_cip_rows_excluded": summary_cip_rows_excluded,
        "second_major_rows_excluded": second_major_rows_excluded,
        "incomplete_key_rows_excluded": incomplete_key_rows_excluded,
        "unique_institution_program_award_combinations": len(program_keys),
        "institutions_with_specific_program_completions": len(program_unitids),
        "institution_completion_coverage_rate": rate(len(program_unitids & institution_ids), len(institution_ids)),
        "completion_unitids_not_in_current_directory": len(program_unitids - institution_ids),
        "distinct_cip6_observed": len(observed_cips),
        "award_level_coverage": award_level_coverage,
        "cip_soc_coverage": {
            "crosswalk_pairs_total": len(bridge),
            "distinct_cip6_in_crosswalk": len(bridge_by_cip),
            "observed_cip6_with_direct_mapping": len(mapped_observed_cips),
            "observed_cip6_without_direct_mapping": len(unmapped_observed_cips),
            "observed_cip6_direct_mapping_rate": rate(len(mapped_observed_cips), len(observed_cips)),
            "program_combinations_with_direct_mapping": len(mapped_programs),
            "program_combinations_without_direct_mapping": len(unmapped_programs),
            "program_combination_direct_mapping_rate": rate(len(mapped_programs), len(program_keys)),
            "institutions_with_at_least_one_direct_mapped_program": len(institutions_with_mapped_programs),
            "institutions_with_only_unmapped_specific_programs": len(institutions_with_only_unmapped_programs),
            "cip_soc_pairs_relevant_to_observed_cips": observed_bridge_pairs,
            "unmapped_observed_cip6": sorted(unmapped_observed_cips),
        },
        "interpretation_notes": [
            "C2025_A records observed 2024-25 completions by CIP and award level; it is not a complete institutional course catalog or proof that every historically offered program is currently admitting students.",
            "IPEDS CIP 99.0000 summary rows are excluded from specific-program coverage.",
            "C2025_A MAJORNUM=2 second-major rows remain available in the normalized source but are excluded from the default institution-program grain to prevent double counting.",
            "A missing CIP-SOC relationship means the official crosswalk has no direct mapping for that CIP; it is not a negative quality signal and does not remove the program.",
            "Program-to-occupation relationships remain many-to-many. SOC6_COUNT is descriptive coverage, not a career-fit score.",
        ],
    }

    out_dir = output_dir / "_program_coverage" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_csv(
        out_dir / "program_coverage_flags.csv",
        ["UNITID", "CIP6", "AWLEVEL", "DIRECT_CIP_SOC_MAPPING", "SOC6_COUNT", "SOURCE_ROW_COUNT"],
        flags,
    )
    baseline = evaluate_coverage_baseline("program", report)
    report["baseline_validation"] = baseline
    (out_dir / "program_coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if enforce_baseline and baseline["status"] != "pass":
        raise IngestionError("Program coverage regression gate failed: " + "; ".join(baseline["failures"]))
    return {"report": report, "output": str(out_dir / "program_coverage.json")}



def build_institution_identity_resolution(
    institutions: list[dict[str, str]],
    dapip_bridge: list[dict[str, str]],
    dapip_campus: list[dict[str, str]],
) -> list[dict[str, object]]:
    """Create review clusters from exact identifiers without auto-merging UNITIDs."""
    unitids = {
        str(row.get("UNITID") or "")
        for row in institutions
        if row.get("UNITID")
    }

    parent: dict[str, str] = {unitid: unitid for unitid in unitids}

    def find(unitid: str) -> str:
        root = parent[unitid]
        while root != parent[root]:
            root = parent[root]
        while unitid != root:
            nxt = parent[unitid]
            parent[unitid] = root
            unitid = nxt
        return root

    def union(a: str, b: str) -> None:
        if a not in parent or b not in parent:
            return
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        keep, merge = sorted((ra, rb))
        parent[merge] = keep

    dapip_by_unitid: dict[str, set[str]] = {}
    unitids_by_dapip: dict[str, set[str]] = {}
    for row in dapip_bridge:
        unitid = str(row.get("UNITID") or "")
        dapip_id = str(row.get("DAPIP_ID") or "")
        if unitid in unitids and dapip_id:
            dapip_by_unitid.setdefault(unitid, set()).add(dapip_id)
            unitids_by_dapip.setdefault(dapip_id, set()).add(unitid)

    for shared_unitids in unitids_by_dapip.values():
        ordered = sorted(shared_unitids)
        for other in ordered[1:]:
            union(ordered[0], other)

    components: dict[str, set[str]] = {}
    for unitid in sorted(unitids):
        components.setdefault(find(unitid), set()).add(unitid)

    campus_by_dapip: dict[str, list[dict[str, str]]] = {}
    for row in dapip_campus:
        dapip_id = str(row.get("DAPIP_ID") or "")
        if dapip_id:
            campus_by_dapip.setdefault(dapip_id, []).append(row)

    opeid_by_unitid: dict[str, str] = {}
    unitids_by_opeid: dict[str, set[str]] = {}
    institution_by_unitid = {
        str(row.get("UNITID") or ""): row
        for row in institutions
        if row.get("UNITID")
    }
    for unitid, row in institution_by_unitid.items():
        opeid = normalize_opeid(row.get("OPEID"))
        if opeid:
            opeid_by_unitid[unitid] = opeid
            unitids_by_opeid.setdefault(opeid, set()).add(unitid)

    output: list[dict[str, object]] = []
    for unitid in sorted(unitids):
        dapip_ids = dapip_by_unitid.get(unitid, set())
        component = components[find(unitid)]
        campus_rows = [
            campus
            for dapip_id in dapip_ids
            for campus in campus_by_dapip.get(dapip_id, [])
        ]
        parent_dapip_ids = {
            str(row.get("PARENT_DAPIP_ID") or "")
            for row in campus_rows
            if row.get("PARENT_DAPIP_ID")
        }
        location_types = {
            str(row.get("LOCATION_TYPE") or "")
            for row in campus_rows
            if row.get("LOCATION_TYPE")
        }
        dapip_opeids = {
            normalize_opeid(row.get("OPEID"))
            for row in campus_rows
            if normalize_opeid(row.get("OPEID"))
        }
        opeid = opeid_by_unitid.get(unitid)
        shared_opeid_count = len(unitids_by_opeid.get(opeid, set())) if opeid else 0

        reasons: list[str] = []
        if len(component) > 1:
            reasons.append("shared_dapip_component")
        if len(dapip_ids) > 1:
            reasons.append("multiple_dapip_ids")
        if shared_opeid_count > 1:
            reasons.append("shared_exact_opeid")
        if not dapip_ids:
            reasons.append("no_dapip_unitid_match")

        if len(component) > 1:
            status = "review_shared_exact_identifier_component"
        elif len(dapip_ids) > 1:
            status = "review_multiple_dapip_ids"
        elif shared_opeid_count > 1:
            status = "review_shared_exact_opeid"
        elif not dapip_ids:
            status = "distinct_unitid_unmatched_dapip"
        else:
            status = "distinct_unitid"

        cluster_id = (
            f"DAPIP-COMPONENT:{min(component)}"
            if len(component) > 1
            else f"UNITID:{unitid}"
        )
        output.append({
            "UNITID": unitid,
            "RECOMMENDATION_ENTITY_ID": f"UNITID:{unitid}",
            "IDENTITY_CLUSTER_ID": cluster_id,
            "IDENTITY_CLUSTER_SIZE": len(component),
            "IDENTITY_REVIEW_STATUS": status,
            "IDENTITY_REVIEW_REASONS": "|".join(reasons),
            "AUTO_COLLAPSE": "0",
            "KEEP_DISTINCT_BY_DEFAULT": "1",
            "DAPIP_IDS": "|".join(sorted(dapip_ids)),
            "DAPIP_ID_COUNT": len(dapip_ids),
            "PARENT_DAPIP_IDS": "|".join(sorted(parent_dapip_ids)),
            "DAPIP_LOCATION_TYPES": "|".join(sorted(location_types)),
            "IPEDS_OPEID": opeid or "",
            "DAPIP_OPEIDS": "|".join(sorted(str(v) for v in dapip_opeids if v)),
            "SHARED_EXACT_OPEID_UNIT_COUNT": shared_opeid_count,
            "IDENTITY_PROVENANCE": "IPEDS_UNITID|DAPIP_EXACT_UNITID_BRIDGE|OPEID_EXACT_REVIEW_ONLY",
        })

    return output


def build_model_ready_layer(output_dir: Path) -> dict:
    """Assemble explanation-ready institution → program → occupation tables without scoring."""
    ipeds_dir = latest_snapshot_dir(output_dir, "ipeds_directory_2025")
    completion_dir = latest_snapshot_dir(output_dir, "ipeds_completions_2025")
    crosswalk_dir = latest_snapshot_dir(output_dir, "cip_soc_crosswalk_2020_2018")
    onet_dir = latest_snapshot_dir(output_dir, "onet_31_0")
    projection_dir = latest_snapshot_dir(output_dir, "bls_employment_projections_2025_2035")
    oews_dir = latest_snapshot_dir(output_dir, "bls_oews_may_2025")
    dapip_dir = latest_snapshot_dir(output_dir, "dapip_accreditation")

    institutions = read_csv_path(ipeds_dir / "normalized" / "institution.csv")
    completions = read_csv_path(completion_dir / "normalized" / "program_completion.csv")
    crosswalk = read_csv_path(crosswalk_dir / "normalized" / "cip_soc_bridge.csv")
    occupations = read_csv_path(onet_dir / "normalized" / "occupation_data.csv")
    projections = read_csv_path(projection_dir / "normalized" / "occupation_outlook.csv")
    wages = read_csv_path(oews_dir / "normalized" / "occupation_wage.csv")
    dapip_bridge = read_csv_path(dapip_dir / "normalized" / "dapip_ipeds_bridge.csv")
    dapip_campus = read_csv_path(dapip_dir / "normalized" / "institution_campus.csv")
    accreditation = read_csv_path(dapip_dir / "normalized" / "accreditation_records.csv")

    identity_rows = build_institution_identity_resolution(
        institutions, dapip_bridge, dapip_campus
    )
    identity_by_unitid = {
        str(row["UNITID"]): row for row in identity_rows
    }

    current_accreditation_by_dapip = {
        str(row.get("DAPIP_ID") or "")
        for row in accreditation
        if str(row.get("IS_INSTITUTIONAL") or "") == "1"
        and str(row.get("IS_CURRENT_BY_EXPORT_RULE") or "") == "1"
        and row.get("DAPIP_ID")
    }

    scorecard_rows: list[dict[str, str]] = []
    scorecard_dir: Path | None = None
    scorecard_root = output_dir / "college_scorecard"
    if scorecard_root.exists() and any(p.is_dir() for p in scorecard_root.iterdir()):
        scorecard_dir = latest_snapshot_dir(output_dir, "college_scorecard")
        scorecard_file = scorecard_dir / "normalized" / "institution_scorecard.csv"
        if scorecard_file.exists():
            scorecard_rows = read_csv_path(scorecard_file)
    scorecard_by_unitid = {
        str(row.get("UNITID") or ""): row
        for row in scorecard_rows
        if row.get("UNITID")
    }

    institution_model: list[dict[str, object]] = []
    institution_by_unitid: dict[str, dict[str, object]] = {}
    for source_row in institutions:
        unitid = str(source_row.get("UNITID") or "")
        if not unitid:
            continue
        identity = identity_by_unitid[unitid]
        dapip_ids = {
            value for value in str(identity.get("DAPIP_IDS") or "").split("|") if value
        }
        community, community_reasons = community_college_pathway_flags(source_row)
        scorecard = scorecard_by_unitid.get(unitid)
        row: dict[str, object] = {
            "UNITID": unitid,
            "INSTNM": source_row.get("INSTNM"),
            "CITY": source_row.get("CITY"),
            "STABBR": source_row.get("STABBR"),
            "ZIP": source_row.get("ZIP"),
            "CONTROL": source_row.get("CONTROL"),
            "LOCALE": source_row.get("LOCALE"),
            "SECTOR": source_row.get("SECTOR"),
            "ICLEVEL": source_row.get("ICLEVEL"),
            "DEGGRANT": source_row.get("DEGGRANT"),
            "INSTCAT": source_row.get("INSTCAT"),
            "C21BASIC": source_row.get("C21BASIC"),
            "IPEDS_OPEID": identity.get("IPEDS_OPEID"),
            "RECOMMENDATION_ENTITY_ID": identity.get("RECOMMENDATION_ENTITY_ID"),
            "IDENTITY_CLUSTER_ID": identity.get("IDENTITY_CLUSTER_ID"),
            "IDENTITY_CLUSTER_SIZE": identity.get("IDENTITY_CLUSTER_SIZE"),
            "IDENTITY_REVIEW_STATUS": identity.get("IDENTITY_REVIEW_STATUS"),
            "IDENTITY_REVIEW_REASONS": identity.get("IDENTITY_REVIEW_REASONS"),
            "AUTO_COLLAPSE": identity.get("AUTO_COLLAPSE"),
            "KEEP_DISTINCT_BY_DEFAULT": identity.get("KEEP_DISTINCT_BY_DEFAULT"),
            "DAPIP_IDS": identity.get("DAPIP_IDS"),
            "DAPIP_ID_COUNT": identity.get("DAPIP_ID_COUNT"),
            "PARENT_DAPIP_IDS": identity.get("PARENT_DAPIP_IDS"),
            "DAPIP_LOCATION_TYPES": identity.get("DAPIP_LOCATION_TYPES"),
            "SHARED_EXACT_OPEID_UNIT_COUNT": identity.get("SHARED_EXACT_OPEID_UNIT_COUNT"),
            "CURRENT_INSTITUTIONAL_ACCREDITATION_BY_EXPORT_RULE": (
                "1" if any(dapip_id in current_accreditation_by_dapip for dapip_id in dapip_ids) else "0"
            ),
            "COMMUNITY_COLLEGE_PATHWAY_PROXY": "1" if community else "0",
            "COMMUNITY_COLLEGE_PROXY_REASONS": "|".join(community_reasons),
            "SCORECARD_MATCH": "1" if scorecard else "0",
            "SCORECARD_SOURCE_RELEASE": scorecard.get("source_release") if scorecard else "",
            "IPEDS_SOURCE_RELEASE": source_row.get("source_release"),
            "DAPIP_SOURCE_RELEASE": get_source("dapip_accreditation")["release"]["label"],
            "IDENTITY_PROVENANCE": identity.get("IDENTITY_PROVENANCE"),
        }
        if scorecard:
            for field in SCORECARD_FIELDS:
                if field == "id":
                    continue
                row[f"SCORECARD__{field}"] = scorecard.get(field)
        institution_model.append(row)
        institution_by_unitid[unitid] = row

    first_major: dict[tuple[str, str, str], dict[str, str]] = {}
    second_major_keys: set[tuple[str, str, str]] = set()
    for row in completions:
        unitid = str(row.get("UNITID") or "")
        major_num = str(row.get("MAJORNUM") or "").strip()
        cip = str(row.get("CIP6") or "")
        award = str(row.get("AWLEVEL") or "")
        if not unitid or not cip or not award or cip in {"990000", "000099"}:
            continue
        key = (unitid, cip, award)
        if major_num == "2":
            second_major_keys.add(key)
        elif major_num in {"", "1"}:
            first_major[key] = row

    socs_by_cip: dict[str, set[str]] = {}
    crosswalk_version_by_pair: dict[tuple[str, str], str] = {}
    for row in crosswalk:
        cip = str(row.get("CIP6") or "")
        soc = str(row.get("SOC6") or "")
        if not cip or not soc:
            continue
        socs_by_cip.setdefault(cip, set()).add(soc)
        crosswalk_version_by_pair[(cip, soc)] = str(row.get("crosswalk_version") or "")

    program_model: list[dict[str, object]] = []
    for key in sorted(first_major):
        unitid, cip, award = key
        source_row = first_major[key]
        institution = institution_by_unitid.get(unitid)
        if not institution:
            continue
        total = parse_number(source_row.get("CTOTALT"))
        program_model.append({
            "UNITID": unitid,
            "RECOMMENDATION_ENTITY_ID": institution.get("RECOMMENDATION_ENTITY_ID"),
            "CIP6": cip,
            "AWLEVEL": award,
            "MAJORNUM": "1",
            "COMPLETIONS_TOTAL": total,
            "COMPLETIONS_TOTAL_STATUS": "reported" if total is not None else "null",
            "SECOND_MAJOR_RECORD_PRESENT": "1" if key in second_major_keys else "0",
            "DIRECT_CIP_SOC_MAPPING": "1" if cip in socs_by_cip else "0",
            "DIRECT_SOC6_COUNT": len(socs_by_cip.get(cip, set())),
            "PROGRAM_SOURCE_ID": source_row.get("source_id"),
            "PROGRAM_SOURCE_RELEASE": source_row.get("source_release"),
            "PROGRAM_EVIDENCE_TYPE": "IPEDS_C2025_A_FIRST_MAJOR_RECORD",
        })

    onet_by_soc: dict[str, list[dict[str, str]]] = {}
    for row in occupations:
        soc = str(row.get("SOC6") or "")
        if soc:
            onet_by_soc.setdefault(soc, []).append(row)
    projection_by_soc = {
        str(row.get("SOC6") or ""): row
        for row in projections
        if row.get("SOC6")
    }
    national_wage_by_soc = {
        str(row.get("OCC_CODE") or ""): row
        for row in wages
        if str(row.get("AREA_TYPE") or "") == "National"
        and str(row.get("IS_DETAILED") or "") == "1"
        and row.get("OCC_CODE")
    }

    out_dir = output_dir / "_model_ready" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    identity_fields = list(identity_rows[0].keys()) if identity_rows else []
    institution_fields: list[str] = []
    for row in institution_model:
        for field in row:
            if field not in institution_fields:
                institution_fields.append(field)
    program_fields = list(program_model[0].keys()) if program_model else []
    pathway_fields = [
        "UNITID", "RECOMMENDATION_ENTITY_ID", "CIP6", "AWLEVEL", "SOC6",
        "ONET_SOC_CODE", "OCCUPATION_TITLE", "OCCUPATION_DESCRIPTION",
        "PATHWAY_RELATIONSHIP_TYPE", "PATHWAY_INTERPRETATION",
        "HAS_ONET_DETAIL", "HAS_BLS_PROJECTION", "HAS_OEWS_NATIONAL",
        "BLS_EMPLOYMENT_2025_THOUSANDS", "BLS_EMPLOYMENT_2035_THOUSANDS",
        "BLS_EMPLOYMENT_CHANGE_PERCENT_2025_2035",
        "BLS_ANNUAL_OPENINGS_2025_2035_THOUSANDS", "BLS_TYPICAL_EDUCATION",
        "OEWS_NATIONAL_EMPLOYMENT", "OEWS_NATIONAL_EMPLOYMENT_STATUS",
        "OEWS_NATIONAL_P25", "OEWS_NATIONAL_MEDIAN", "OEWS_NATIONAL_P75",
        "OEWS_NATIONAL_MEDIAN_STATUS", "CIP_SOC_CROSSWALK_VERSION",
        "ONET_VERSION", "BLS_PROJECTION_CYCLE", "OEWS_REFERENCE_PERIOD",
    ]

    write_csv(out_dir / "institution_identity_resolution.csv", identity_fields, identity_rows)
    write_csv(out_dir / "institution_model.csv", institution_fields, institution_model)
    write_csv(out_dir / "program_model.csv", program_fields, program_model)

    pathway_rows = 0
    mapped_pathway_rows = 0
    mapped_pathways_with_onet_detail = 0
    mapped_pathways_with_bls_projection = 0
    mapped_pathways_with_oews_national = 0
    pathway_path = out_dir / "program_occupation_pathway.csv"
    pathway_path.parent.mkdir(parents=True, exist_ok=True)
    with pathway_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=pathway_fields, extrasaction="ignore")
        writer.writeheader()
        for program in program_model:
            unitid = str(program["UNITID"])
            cip = str(program["CIP6"])
            award = str(program["AWLEVEL"])
            mapped_socs = sorted(socs_by_cip.get(cip, set()))
            if not mapped_socs:
                writer.writerow({
                    "UNITID": unitid,
                    "RECOMMENDATION_ENTITY_ID": program.get("RECOMMENDATION_ENTITY_ID"),
                    "CIP6": cip,
                    "AWLEVEL": award,
                    "SOC6": "",
                    "ONET_SOC_CODE": "",
                    "OCCUPATION_TITLE": "",
                    "OCCUPATION_DESCRIPTION": "",
                    "PATHWAY_RELATIONSHIP_TYPE": "no_direct_cip_soc_mapping",
                    "PATHWAY_INTERPRETATION": "coverage_gap_not_negative_signal",
                    "HAS_ONET_DETAIL": "0",
                    "HAS_BLS_PROJECTION": "0",
                    "HAS_OEWS_NATIONAL": "0",
                    "CIP_SOC_CROSSWALK_VERSION": "",
                    "ONET_VERSION": "",
                    "BLS_PROJECTION_CYCLE": "",
                    "OEWS_REFERENCE_PERIOD": "",
                })
                pathway_rows += 1
                continue

            for soc in mapped_socs:
                onet_rows = onet_by_soc.get(soc) or [None]
                projection = projection_by_soc.get(soc)
                wage = national_wage_by_soc.get(soc)
                for occupation in onet_rows:
                    row = {
                        "UNITID": unitid,
                        "RECOMMENDATION_ENTITY_ID": program.get("RECOMMENDATION_ENTITY_ID"),
                        "CIP6": cip,
                        "AWLEVEL": award,
                        "SOC6": soc,
                        "ONET_SOC_CODE": occupation.get("ONET_SOC_CODE") if occupation else "",
                        "OCCUPATION_TITLE": (
                            occupation.get("Title")
                            or occupation.get("TITLE")
                            or occupation.get("Occupation")
                            or ""
                        ) if occupation else "",
                        "OCCUPATION_DESCRIPTION": (
                            occupation.get("Description")
                            or occupation.get("DESCRIPTION")
                            or ""
                        ) if occupation else "",
                        "PATHWAY_RELATIONSHIP_TYPE": "official_cip_soc_direct",
                        "PATHWAY_INTERPRETATION": "taxonomy_relationship_not_observed_graduate_outcome",
                        "HAS_ONET_DETAIL": "1" if occupation else "0",
                        "HAS_BLS_PROJECTION": "1" if projection else "0",
                        "HAS_OEWS_NATIONAL": "1" if wage else "0",
                        "BLS_EMPLOYMENT_2025_THOUSANDS": projection.get("EMPLOYMENT_2025_THOUSANDS") if projection else "",
                        "BLS_EMPLOYMENT_2035_THOUSANDS": projection.get("EMPLOYMENT_2035_THOUSANDS") if projection else "",
                        "BLS_EMPLOYMENT_CHANGE_PERCENT_2025_2035": projection.get("EMPLOYMENT_CHANGE_PERCENT_2025_2035") if projection else "",
                        "BLS_ANNUAL_OPENINGS_2025_2035_THOUSANDS": projection.get("ANNUAL_OPENINGS_2025_2035_THOUSANDS") if projection else "",
                        "BLS_TYPICAL_EDUCATION": projection.get("TYPICAL_EDUCATION") if projection else "",
                        "OEWS_NATIONAL_EMPLOYMENT": wage.get("TOT_EMP") if wage else "",
                        "OEWS_NATIONAL_EMPLOYMENT_STATUS": wage.get("TOT_EMP_STATUS") if wage else "",
                        "OEWS_NATIONAL_P25": wage.get("A_PCT25") if wage else "",
                        "OEWS_NATIONAL_MEDIAN": wage.get("A_MEDIAN") if wage else "",
                        "OEWS_NATIONAL_P75": wage.get("A_PCT75") if wage else "",
                        "OEWS_NATIONAL_MEDIAN_STATUS": wage.get("A_MEDIAN_STATUS") if wage else "",
                        "CIP_SOC_CROSSWALK_VERSION": crosswalk_version_by_pair.get((cip, soc), ""),
                        "ONET_VERSION": occupation.get("onet_version") if occupation else "",
                        "BLS_PROJECTION_CYCLE": projection.get("projection_cycle") if projection else "",
                        "OEWS_REFERENCE_PERIOD": wage.get("reference_period") if wage else "",
                    }
                    writer.writerow(row)
                    pathway_rows += 1
                    mapped_pathway_rows += 1
                    if occupation:
                        mapped_pathways_with_onet_detail += 1
                    if projection:
                        mapped_pathways_with_bls_projection += 1
                    if wage:
                        mapped_pathways_with_oews_national += 1

    review_rows = [
        row for row in identity_rows
        if str(row.get("IDENTITY_REVIEW_STATUS") or "").startswith("review_")
    ]
    shared_clusters = {
        str(row.get("IDENTITY_CLUSTER_ID") or "")
        for row in identity_rows
        if int(row.get("IDENTITY_CLUSTER_SIZE") or 0) > 1
    }
    direct_programs = sum(
        1 for row in program_model if row.get("DIRECT_CIP_SOC_MAPPING") == "1"
    )
    qa = {
        "generated_at": utc_now(),
        "sources": {
            "ipeds_directory": str(ipeds_dir),
            "ipeds_completions": str(completion_dir),
            "cip_soc_crosswalk": str(crosswalk_dir),
            "onet": str(onet_dir),
            "bls_projections": str(projection_dir),
            "oews": str(oews_dir),
            "dapip": str(dapip_dir),
            "scorecard": str(scorecard_dir) if scorecard_dir else None,
        },
        "institution_rows": len(institution_model),
        "distinct_recommendation_entities": len({
            str(row.get("RECOMMENDATION_ENTITY_ID") or "")
            for row in institution_model
        }),
        "identity_review_rows": len(review_rows),
        "shared_exact_identifier_clusters": len(shared_clusters),
        "auto_collapsed_institutions": sum(
            1 for row in identity_rows if row.get("AUTO_COLLAPSE") == "1"
        ),
        "program_rows_first_major": len(program_model),
        "programs_with_direct_cip_soc_mapping": direct_programs,
        "programs_without_direct_cip_soc_mapping": len(program_model) - direct_programs,
        "pathway_rows": pathway_rows,
        "mapped_pathway_rows": mapped_pathway_rows,
        "mapped_pathways_with_onet_detail": mapped_pathways_with_onet_detail,
        "mapped_pathways_with_bls_projection": mapped_pathways_with_bls_projection,
        "mapped_pathways_with_oews_national": mapped_pathways_with_oews_national,
        "scorecard_rows_available": len(scorecard_rows),
        "scorecard_institution_matches": sum(
            1 for row in institution_model if row.get("SCORECARD_MATCH") == "1"
        ),
        "recommendation_scoring_enabled": False,
        "scoring_gate_reasons": [
            "Identity review clusters are preserved as distinct UNITIDs until authoritative resolution.",
            "CIP-SOC relationships describe taxonomy pathways, not observed graduate outcomes.",
            "College Scorecard enrichment is optional in this build and must be live-validated before affordability/admissions scoring.",
            "Recommendation calibration remains a later layer after integrated QA.",
        ],
    }
    if qa["auto_collapsed_institutions"] != 0:
        raise IngestionError("Model-ready identity layer auto-collapsed institutions unexpectedly")
    if qa["institution_rows"] != qa["distinct_recommendation_entities"]:
        raise IngestionError("Model-ready institution entity IDs are not one-to-one with UNITID")
    if not program_model or pathway_rows == 0:
        raise IngestionError("Model-ready layer produced no program/pathway rows")

    (out_dir / "model_ready_qa.json").write_text(
        json.dumps(qa, indent=2) + "\n", encoding="utf-8"
    )

    source_snapshot_dirs = {
        "ipeds_directory_2025": ipeds_dir,
        "ipeds_completions_2025": completion_dir,
        "cip_soc_crosswalk_2020_2018": crosswalk_dir,
        "onet_31_0": onet_dir,
        "bls_employment_projections_2025_2035": projection_dir,
        "bls_oews_may_2025": oews_dir,
        "dapip_accreditation": dapip_dir,
    }
    if scorecard_dir:
        source_snapshot_dirs["college_scorecard"] = scorecard_dir
    source_lineage = {}
    for source_id, snapshot_dir in source_snapshot_dirs.items():
        metadata = read_snapshot_metadata(snapshot_dir)
        source_lineage[source_id] = {
            "snapshot_dir": str(snapshot_dir),
            "retrieved_at": metadata.get("retrieved_at"),
            "source_release": metadata.get("source_release"),
            "sha256": metadata.get("sha256"),
            "reference_period": metadata.get("reference_period"),
        }

    build_manifest = {
        "generated_at": utc_now(),
        "source_lineage": source_lineage,
        "table_grains": {
            "institution_identity_resolution": "UNITID",
            "institution_model": "UNITID",
            "program_model": "UNITID + CIP6 + AWLEVEL (MAJORNUM=1 default)",
            "program_occupation_pathway": "UNITID + CIP6 + AWLEVEL + SOC6 + ONET_SOC_CODE",
        },
        "identity_policy": {
            "recommendation_entity_key": "UNITID",
            "automatic_collapse": False,
            "shared_dapip_behavior": "review_cluster_only",
            "shared_opeid_behavior": "review_signal_only",
            "fuzzy_name_merge": False,
        },
        "pathway_policy": {
            "cip_soc_relationship": "many_to_many_taxonomy_not_observed_outcomes",
            "retain_unmapped_programs": True,
            "retain_unmatched_occupations": True,
        },
        "recommendation_scoring_enabled": False,
    }
    (out_dir / "model_ready_manifest.json").write_text(
        json.dumps(build_manifest, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "qa": qa,
        "manifest": build_manifest,
        "output_dir": str(out_dir),
        "files": {
            "identity": str(out_dir / "institution_identity_resolution.csv"),
            "institution": str(out_dir / "institution_model.csv"),
            "program": str(out_dir / "program_model.csv"),
            "pathway": str(pathway_path),
            "qa": str(out_dir / "model_ready_qa.json"),
            "manifest": str(out_dir / "model_ready_manifest.json"),
        },
    }


def scorecard_url(page: int, api_key: str) -> str:
    params = {
        "api_key": api_key,
        "fields": ",".join(SCORECARD_FIELDS),
        "per_page": "100",
        "page": str(page),
    }
    return "https://api.data.gov/ed/collegescorecard/v1/schools.json?" + urllib.parse.urlencode(params)


def ingest_scorecard(source: dict, snapshot_dir: Path) -> dict:
    api_key = os.getenv("COLLEGE_SCORECARD_API_KEY")
    if not api_key:
        raise IngestionError("COLLEGE_SCORECARD_API_KEY is required for College Scorecard ingestion")

    all_results: list[dict] = []
    page = 0
    metadata_last: dict = {}
    raw_pages: list[bytes] = []
    while True:
        payload = http_get(scorecard_url(page, api_key))
        raw_pages.append(payload)
        parsed = json.loads(payload)
        results = parsed.get("results", [])
        metadata_last = parsed.get("metadata", {}) or {}
        all_results.extend(results)
        per_page = int(metadata_last.get("per_page") or 100)
        total = int(metadata_last.get("total") or len(all_results))
        if not results or len(all_results) >= total:
            break
        page += 1
        if page > math.ceil(total / max(per_page, 1)) + 2:
            raise IngestionError("Scorecard pagination exceeded expected page count")

    normalized: list[dict[str, object]] = []
    for record in all_results:
        flat = flatten_dict(record)
        row: dict[str, object] = {"UNITID": normalize_unitid(flat.get("id"))}
        for field in SCORECARD_FIELDS:
            if field == "id":
                continue
            row[field] = flat.get(field)
        row["source_id"] = source["source_id"]
        row["source_release"] = source["release"]["label"]
        normalized.append(row)

    fieldnames = ["UNITID"] + [f for f in SCORECARD_FIELDS if f != "id"] + ["source_id", "source_release"]
    write_csv(snapshot_dir / "normalized" / "institution_scorecard.csv", fieldnames, normalized)

    raw_ndjson = b"\n".join(json.dumps(r, separators=(",", ":")).encode("utf-8") for r in all_results) + b"\n"
    raw_dir = snapshot_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "scorecard.ndjson").write_bytes(raw_ndjson)

    report = qa_report(source["source_id"], normalized, ["UNITID"])
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source["access_url"],
        raw_filename="scorecard.ndjson",
        raw_bytes=raw_ndjson,
        row_count_raw=len(all_results),
        extra={"response_metadata": metadata_last, "query_fields": SCORECARD_FIELDS},
    )
    return {"metadata": metadata, "qa": report, "normalized_rows": len(normalized)}


def ingest_source(source_id: str, output_dir: Path, *, dry_run: bool = False) -> dict:
    source = get_source(source_id)

    if source_id == "dapip_accreditation":
        source_url = resolve_access_url(source)
        if dry_run:
            return {
                "source_id": source_id,
                "mode": "dry-run",
                "access_url": source_url,
                "method": "POST",
                "payload": {"CSVChecked": True, "ExcelChecked": False},
            }
        raw = http_post_json(source_url, {"CSVChecked": True, "ExcelChecked": False})
        snapshot_dir = output_dir / source_id / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        raw_dir = snapshot_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "DAPIPData.zip").write_bytes(raw)
        result = ingest_dapip(source, raw, snapshot_dir, source_url)

    elif source_id == "college_scorecard":
        if dry_run:
            return {
                "source_id": source_id,
                "mode": "dry-run",
                "access_url": source["access_url"],
                "requires_api_key": True,
            }
        snapshot_dir = output_dir / source_id / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result = ingest_scorecard(source, snapshot_dir)

    elif source_id == "onet_31_0":
        if dry_run:
            return {
                "source_id": source_id,
                "mode": "dry-run",
                "access_urls": source.get("files", {}),
            }
        snapshot_dir = output_dir / source_id / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result = ingest_onet(source, snapshot_dir)

    elif source_id == "bls_oews_may_2025":
        if dry_run:
            return {
                "source_id": source_id,
                "mode": "dry-run",
                "access_url": source.get("access_url"),
                "service_base_url": source.get("service_base_url"),
                "release_query_key": source.get("release_query_key"),
                "geography": "National",
            }
        snapshot_dir = output_dir / source_id / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result = ingest_oews_query(source, snapshot_dir)

    else:
        source_url = resolve_access_url(source)
        if dry_run:
            return {"source_id": source_id, "mode": "dry-run", "access_url": source_url}
        raw = http_get(source_url)
        snapshot_dir = output_dir / source_id / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        raw_dir = snapshot_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_name = safe_filename_from_url(source_url, f"{source_id}.bin")
        (raw_dir / raw_name).write_bytes(raw)

        if source_id.startswith("ipeds_"):
            result = ingest_ipeds(source, raw, snapshot_dir, source_url)
        elif source_id == "cip_soc_crosswalk_2020_2018":
            result = ingest_cip_soc(source, raw, snapshot_dir, source_url)
        elif source_id == "bls_employment_projections_2025_2035":
            result = ingest_bls_projection(source, raw, snapshot_dir, source_url)
        else:
            raise IngestionError(f"No adapter implemented for {source_id}")

    reports = snapshot_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "qa.json").write_text(json.dumps(result["qa"], indent=2) + "\n", encoding="utf-8")
    if "coverage" in result:
        coverage_name = (
            "institution_coverage.json"
            if source_id == "ipeds_directory_2025"
            else "career_coverage.json"
            if source_id == "onet_31_0"
            else "coverage.json"
        )
        (reports / coverage_name).write_text(
            json.dumps(result["coverage"], indent=2) + "\n", encoding="utf-8"
        )
    if result["qa"].get("status") == "fail":
        raise IngestionError(
            f"{source_id} normalization failed QA: {json.dumps(result['qa'], sort_keys=True)}"
        )
    result["snapshot_dir"] = str(snapshot_dir)
    return result


def cli() -> int:
    parser = argparse.ArgumentParser(description="College + Career Matching Tool public-source ingestion prototype")
    parser.add_argument("--source", help="source_id from source_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATA_DIR / "snapshots")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-sources", action="store_true")
    parser.add_argument("--build-career-joins", action="store_true")
    parser.add_argument("--build-institution-coverage", action="store_true")
    parser.add_argument("--build-program-coverage", action="store_true")
    parser.add_argument("--build-model-ready", action="store_true")
    parser.add_argument("--enforce-coverage-baseline", action="store_true")
    args = parser.parse_args()

    if args.build_career_joins:
        print(json.dumps(build_career_join_report(args.output_dir, enforce_baseline=args.enforce_coverage_baseline), indent=2, default=str))
        return 0

    if args.build_institution_coverage:
        print(json.dumps(build_institution_coverage_report(args.output_dir, enforce_baseline=args.enforce_coverage_baseline), indent=2, default=str))
        return 0

    if args.build_program_coverage:
        print(json.dumps(build_program_coverage_report(args.output_dir, enforce_baseline=args.enforce_coverage_baseline), indent=2, default=str))
        return 0

    if args.build_model_ready:
        print(json.dumps(build_model_ready_layer(args.output_dir), indent=2, default=str))
        return 0

    if args.list_sources:
        for source in load_manifest()["sources"]:
            print(source["source_id"])
        return 0

    if not args.source:
        parser.error("--source is required unless --list-sources or a build-report option is used")

    try:
        result = ingest_source(args.source, args.output_dir, dry_run=args.dry_run)
    except (IngestionError, urllib.error.URLError, zipfile.BadZipFile, ET.ParseError, json.JSONDecodeError) as exc:
        print(f"Ingestion failed: {exc}")
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
