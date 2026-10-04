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
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def resolve_access_url(source: dict) -> str:
    if source.get("access_url"):
        return str(source["access_url"])
    if source["source_id"].startswith("ipeds_") and source.get("file_stem"):
        return f"https://nces.ed.gov/ipeds/datacenter/data/{source['file_stem']}.zip"
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
    if text.lower() in {"privacysuppressed", "#", "**", "***", "n/a", "na"}:
        return "suppressed"
    return "reported"


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
    return {
        "source_id": source_id,
        "generated_at": utc_now(),
        "row_count": len(rows),
        "key_fields": key_fields,
        "null_key_rows": null_key_rows,
        "duplicate_key_rows": duplicate_keys,
        "status": "pass" if null_key_rows == 0 and duplicate_keys == 0 else "review",
    }


def ingest_ipeds(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    member, records = read_zip_table(raw)
    normalized: list[dict[str, object]] = []

    if source["source_id"] == "ipeds_directory_2025":
        fields = ["UNITID", "INSTNM", "CITY", "STABBR", "ZIP", "CONTROL", "LOCALE"]
        for row in records:
            normalized.append({
                "UNITID": normalize_unitid(row.get("UNITID")),
                "INSTNM": row.get("INSTNM"),
                "CITY": row.get("CITY"),
                "STABBR": row.get("STABBR"),
                "ZIP": row.get("ZIP"),
                "CONTROL": row.get("CONTROL"),
                "LOCALE": row.get("LOCALE"),
                "source_id": source["source_id"],
                "source_release": source["release"]["label"],
            })
        out = snapshot_dir / "normalized" / "institution.csv"
        write_csv(out, fields + ["source_id", "source_release"], normalized)
        report = qa_report(source["source_id"], normalized, ["UNITID"])
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
    return {"metadata": metadata, "qa": report, "normalized_rows": len(normalized)}


def ingest_cip_soc(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    rows = read_xlsx_rows_bytes(raw)
    header_index, header = find_header_row(rows, ["cip", "soc"])
    records = row_dicts_from_matrix(rows, header_index, header)

    def choose(record: dict[str, str], must_include: tuple[str, ...]) -> str | None:
        for key, value in record.items():
            low = key.lower()
            if all(token in low for token in must_include):
                return value
        return None

    normalized: list[dict[str, object]] = []
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
        normalized.append({
            "CIP6": cip,
            "SOC6": soc,
            "CIP_RAW": cip_raw,
            "SOC_RAW": soc_raw,
            "crosswalk_version": source["release"]["label"],
            "source_id": source["source_id"],
        })

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
        row_count_raw=len(records),
    )
    return {"metadata": metadata, "qa": report, "normalized_rows": len(normalized)}


def ingest_onet(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    wanted = {
        "occupation data": "occupation.csv",
        "skills": "skills.csv",
        "knowledge": "knowledge.csv",
        "abilities": "abilities.csv",
        "interests": "interests.csv",
        "work activities": "work_activities.csv",
        "work context": "work_context.csv",
        "education, training, and experience": "education_training_experience.csv",
        "related occupations": "related_occupations.csv",
        "technology skills": "technology_skills.csv",
    }
    extracted: dict[str, int] = {}
    occupation_rows: list[dict[str, object]] = []

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.namelist()
        for label, out_name in wanted.items():
            matches = [m for m in members if Path(m).stem.lower() == label]
            if not matches:
                continue
            member = matches[0]
            rows = read_delimited_bytes(archive.read(member))
            normalized_rows: list[dict[str, object]] = []
            for row in rows:
                onet = row.get("O*NET-SOC Code") or row.get("ONET_SOC_CODE") or row.get("O*NET-SOC_Code")
                new_row: dict[str, object] = dict(row)
                new_row["ONET_SOC_CODE"] = onet
                new_row["SOC6"] = normalize_soc6(onet)
                new_row["onet_version"] = source["release"]["label"]
                normalized_rows.append(new_row)
            if normalized_rows:
                fieldnames = list(normalized_rows[0].keys())
                write_csv(snapshot_dir / "normalized" / out_name, fieldnames, normalized_rows)
            extracted[out_name] = len(normalized_rows)
            if out_name == "occupation.csv":
                occupation_rows = normalized_rows

    report = qa_report(source["source_id"], occupation_rows, ["ONET_SOC_CODE"])
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=safe_filename_from_url(source_url, "onet.zip"),
        raw_bytes=raw,
        row_count_raw=sum(extracted.values()),
        extra={"tables_extracted": extracted},
    )
    return {"metadata": metadata, "qa": report, "normalized_rows": extracted}


def ingest_bls_projection(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    rows = read_xlsx_rows_bytes(raw)
    header_index, header = find_header_row(rows, ["employment", "2025", "2035"])
    records = row_dicts_from_matrix(rows, header_index, header)

    def find_key(record: dict[str, str], fragments: tuple[str, ...]) -> str | None:
        for key in record:
            low = key.lower()
            if all(fragment in low for fragment in fragments):
                return key
        return None

    normalized: list[dict[str, object]] = []
    for record in records:
        code_key = find_key(record, ("matrix", "code")) or find_key(record, ("code",))
        title_key = find_key(record, ("matrix", "title")) or find_key(record, ("title",))
        type_key = find_key(record, ("occupation", "type"))
        soc = normalize_soc6(record.get(code_key) if code_key else None)
        if not soc:
            continue
        normalized.append({
            "SOC6": soc,
            "TITLE": record.get(title_key, "") if title_key else "",
            "OCCUPATION_TYPE": record.get(type_key, "") if type_key else "",
            "projection_cycle": source["release"]["label"],
            "source_id": source["source_id"],
        })

    write_csv(
        snapshot_dir / "normalized" / "occupation_outlook.csv",
        ["SOC6", "TITLE", "OCCUPATION_TYPE", "projection_cycle", "source_id"],
        normalized,
    )
    report = qa_report(source["source_id"], normalized, ["SOC6"])
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=safe_filename_from_url(source_url, "occupation.xlsx"),
        raw_bytes=raw,
        row_count_raw=len(records),
    )
    return {"metadata": metadata, "qa": report, "normalized_rows": len(normalized)}


def parse_oews_archive(raw: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.namelist()
        for member in members:
            low = member.lower()
            if low.endswith(".txt") or low.endswith(".csv"):
                delimiter = "\t" if low.endswith(".txt") else None
                return read_delimited_bytes(archive.read(member), delimiter=delimiter)
        xlsx_members = [m for m in members if m.lower().endswith(".xlsx")]
        if xlsx_members:
            rows = read_xlsx_rows_bytes(archive.read(xlsx_members[0]))
            header_index, header = find_header_row(rows, ["area", "occ"])
            return row_dicts_from_matrix(rows, header_index, header)
    raise IngestionError("OEWS archive has no readable CSV/TXT/XLSX member")


def ingest_oews(source: dict, raw: bytes, snapshot_dir: Path, source_url: str) -> dict:
    records = parse_oews_archive(raw)
    normalized: list[dict[str, object]] = []
    for row in records:
        area = row.get("AREA") or row.get("area")
        occ = row.get("OCC_CODE") or row.get("occ_code")
        if not area or not occ:
            continue
        normalized.append({
            "AREA": area,
            "AREA_TITLE": row.get("AREA_TITLE") or row.get("area_title"),
            "OCC_CODE": normalize_soc6(occ) or occ,
            "TOT_EMP": row.get("TOT_EMP") or row.get("tot_emp"),
            "A_PCT25": row.get("A_PCT25") or row.get("a_pct25"),
            "A_MEDIAN": row.get("A_MEDIAN") or row.get("a_median"),
            "A_PCT75": row.get("A_PCT75") or row.get("a_pct75"),
            "reference_period": source["release"]["label"],
            "source_id": source["source_id"],
        })

    write_csv(
        snapshot_dir / "normalized" / "occupation_wage.csv",
        ["AREA", "AREA_TITLE", "OCC_CODE", "TOT_EMP", "A_PCT25", "A_MEDIAN", "A_PCT75", "reference_period", "source_id"],
        normalized,
    )
    report = qa_report(source["source_id"], normalized, ["AREA", "OCC_CODE"])
    metadata = write_snapshot_metadata(
        snapshot_dir,
        source=source,
        source_url=source_url,
        raw_filename=safe_filename_from_url(source_url, "oews.zip"),
        raw_bytes=raw,
        row_count_raw=len(records),
    )
    return {"metadata": metadata, "qa": report, "normalized_rows": len(normalized)}


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

    if source_id == "college_scorecard":
        if dry_run:
            return {"source_id": source_id, "mode": "dry-run", "access_url": source["access_url"], "requires_api_key": True}
        snapshot_dir = output_dir / source_id / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result = ingest_scorecard(source, snapshot_dir)
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
        elif source_id == "onet_31_0":
            result = ingest_onet(source, raw, snapshot_dir, source_url)
        elif source_id == "bls_employment_projections_2025_2035":
            result = ingest_bls_projection(source, raw, snapshot_dir, source_url)
        elif source_id == "bls_oews_may_2025":
            result = ingest_oews(source, raw, snapshot_dir, source_url)
        else:
            raise IngestionError(f"No adapter implemented for {source_id}")

    reports = snapshot_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "qa.json").write_text(json.dumps(result["qa"], indent=2) + "\n", encoding="utf-8")
    result["snapshot_dir"] = str(snapshot_dir)
    return result


def cli() -> int:
    parser = argparse.ArgumentParser(description="College + Career Matching Tool public-source ingestion prototype")
    parser.add_argument("--source", help="source_id from source_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATA_DIR / "snapshots")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-sources", action="store_true")
    args = parser.parse_args()

    if args.list_sources:
        for source in load_manifest()["sources"]:
            print(source["source_id"])
        return 0

    if not args.source:
        parser.error("--source is required unless --list-sources is used")

    try:
        result = ingest_source(args.source, args.output_dir, dry_run=args.dry_run)
    except (IngestionError, urllib.error.URLError, zipfile.BadZipFile, ET.ParseError, json.JSONDecodeError) as exc:
        print(f"Ingestion failed: {exc}")
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
