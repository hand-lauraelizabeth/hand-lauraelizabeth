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
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "college-career-matching"
MANIFEST_PATH = PROJECT / "source_manifest.json"
DEFAULT_DATA_DIR = PROJECT / "data"

USER_AGENT = "LauraElizabethHand-CollegeCareerMatcher/0.1 (+public portfolio prototype)"
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
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/zip,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.bls.gov/emp/tables.htm",
        })
    request_headers.update(headers or {})
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def http_post_json(url: str, payload: dict[str, object], *, timeout: int = 90) -> bytes:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/zip, application/octet-stream, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


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


def normalize_cip6(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
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
        fields = ["UNITID", "CIP6", "CIPCODE_RAW", "AWLEVEL", "CTOTALT"]
        for row in records:
            cip_raw = row.get("CIPCODE")
            normalized.append({
                "UNITID": normalize_unitid(row.get("UNITID")),
                "CIP6": normalize_cip6(cip_raw),
                "CIPCODE_RAW": cip_raw,
                "AWLEVEL": row.get("AWLEVEL"),
                "CTOTALT": row.get("CTOTALT"),
                "source_id": source["source_id"],
                "source_release": source["release"]["label"],
            })
        out = snapshot_dir / "normalized" / "program_completion.csv"
        write_csv(out, fields + ["source_id", "source_release"], normalized)
        report = qa_report(source["source_id"], normalized, ["UNITID", "CIP6", "AWLEVEL"])

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

def ingest_bls_projection(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
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

    all_rows: list[dict[str, object]] = []
    detailed_rows: list[dict[str, object]] = []
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
            "Only BLS rows explicitly labeled Line item enter detailed occupation joins by default.",
            "Employment and annual-opening values retain the BLS thousands unit in field names.",
        ],
    }
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=safe_filename_from_url(source_url, "occupation.xlsx"),
        raw_bytes=raw,
        row_count_raw=len(all_rows),
        extra={"projection_base_year": 2025, "projection_end_year": 2035},
    )
    return {"metadata": metadata, "qa": report, "coverage": coverage, "normalized_rows": len(detailed_rows)}


def parse_oews_archive(raw: bytes) -> tuple[str, list[dict[str, str]]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [
            member for member in archive.namelist()
            if member.lower().endswith((".txt", ".csv", ".xlsx"))
        ]
        if not members:
            raise IngestionError("OEWS archive has no readable CSV/TXT/XLSX member")
        preferred = sorted(
            members,
            key=lambda name: (
                0 if ("all_data" in name.lower() or "oesm25all" in name.lower()) else 1,
                0 if name.lower().endswith((".txt", ".csv")) else 1,
                -archive.getinfo(name).file_size,
            ),
        )[0]
        payload = archive.read(preferred)
        if preferred.lower().endswith((".txt", ".csv")):
            delimiter = "\t" if preferred.lower().endswith(".txt") else None
            return preferred, read_delimited_bytes(payload, delimiter=delimiter)
        rows = read_xlsx_rows_bytes(payload)
        header_index, header = find_header_row(rows, ["area", "occ"])
        return preferred, row_dicts_from_matrix(rows, header_index, header)


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


def ingest_oews(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    member, records = parse_oews_archive(raw)
    normalized: list[dict[str, object]] = []
    for row in records:
        area = _row_value(row, "AREA")
        occ = _row_value(row, "OCC_CODE")
        if not area or not occ:
            continue
        o_group = _row_value(row, "O_GROUP") or ""
        is_detailed = str(o_group).strip().lower() == "detailed"
        wage_values = {
            name: _row_value(row, name)
            for name in ("A_PCT10", "A_PCT25", "A_MEDIAN", "A_PCT75", "A_PCT90")
        }
        item: dict[str, object] = {
            "AREA": area,
            "AREA_TITLE": _row_value(row, "AREA_TITLE"),
            "AREA_TYPE": _row_value(row, "AREA_TYPE"),
            "PRIM_STATE": _row_value(row, "PRIM_STATE"),
            "OCC_CODE": normalize_soc6(occ) or str(occ).strip(),
            "OCC_TITLE": _row_value(row, "OCC_TITLE"),
            "O_GROUP": o_group,
            "IS_DETAILED": "1" if is_detailed else "0",
            "TOT_EMP": parse_number(_row_value(row, "TOT_EMP")),
            "TOT_EMP_STATUS": bls_value_status(_row_value(row, "TOT_EMP")),
            "A_MEAN": parse_number(_row_value(row, "A_MEAN")),
            "A_MEAN_STATUS": bls_value_status(_row_value(row, "A_MEAN")),
            "reference_period": source["release"]["label"],
            "source_id": source["source_id"],
        }
        for name, raw_value in wage_values.items():
            item[name] = parse_number(raw_value)
            item[f"{name}_STATUS"] = bls_value_status(raw_value)
        normalized.append(item)

    fields = [
        "AREA", "AREA_TITLE", "AREA_TYPE", "PRIM_STATE", "OCC_CODE", "OCC_TITLE",
        "O_GROUP", "IS_DETAILED", "TOT_EMP", "TOT_EMP_STATUS", "A_MEAN", "A_MEAN_STATUS",
        "A_PCT10", "A_PCT10_STATUS", "A_PCT25", "A_PCT25_STATUS",
        "A_MEDIAN", "A_MEDIAN_STATUS", "A_PCT75", "A_PCT75_STATUS",
        "A_PCT90", "A_PCT90_STATUS", "reference_period", "source_id",
    ]
    write_csv(snapshot_dir / "normalized" / "occupation_wage.csv", fields, normalized)

    report = qa_report(source["source_id"], normalized, ["AREA", "OCC_CODE"])
    detailed = [row for row in normalized if row["IS_DETAILED"] == "1"]
    ordering_failures = 0
    for row in detailed:
        values = [row.get("A_PCT25"), row.get("A_MEDIAN"), row.get("A_PCT75")]
        if all(isinstance(value, (int, float)) for value in values):
            if not (float(values[0]) <= float(values[1]) <= float(values[2])):
                ordering_failures += 1
    area_titles: dict[str, set[str]] = {}
    for row in normalized:
        area_titles.setdefault(str(row["AREA"]), set()).add(str(row.get("AREA_TITLE") or ""))
    area_title_conflicts = sum(1 for titles in area_titles.values() if len(titles) > 1)
    report.update({
        "archive_member": member,
        "detailed_occupation_rows": len(detailed),
        "aggregate_occupation_rows": len(normalized) - len(detailed),
        "wage_percentile_ordering_failures": ordering_failures,
        "area_title_conflicts": area_title_conflicts,
    })
    if ordering_failures or area_title_conflicts:
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
        "all_rows": len(normalized),
        "detailed_occupation_rows": len(detailed),
        "coverage_by_area_type": coverage_by_area_type,
        "notes": [
            "AREA_TYPE is retained as the source geography classification rather than inferred from AREA_TITLE.",
            "Aggregate occupation rows remain in the normalized source table but are excluded from detailed O*NET joins.",
            "Suppressed or top-coded wage values remain null numerically with an explicit status field.",
        ],
    }
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=safe_filename_from_url(source_url, "oews.zip"),
        raw_bytes=raw,
        row_count_raw=len(records),
        extra={"archive_member": member},
    )
    return {"metadata": metadata, "qa": report, "coverage": coverage, "normalized_rows": len(normalized)}


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


def build_career_join_report(output_dir: Path) -> dict:
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
    out_dir = output_dir / "_joins" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "career_source_coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {"report": report, "output": str(out_dir / "career_source_coverage.json")}


def build_institution_coverage_report(output_dir: Path) -> dict:
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
    (out_dir / "institution_coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {"report": report, "output": str(out_dir / "institution_coverage.json")}

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
        elif source_id == "bls_oews_may_2025":
            result = ingest_oews(source, raw, snapshot_dir, source_url)
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
    args = parser.parse_args()

    if args.build_career_joins:
        print(json.dumps(build_career_join_report(args.output_dir), indent=2, default=str))
        return 0

    if args.build_institution_coverage:
        print(json.dumps(build_institution_coverage_report(args.output_dir), indent=2, default=str))
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
