from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "college_career_ingest.py"

spec = importlib.util.spec_from_file_location("college_career_ingest", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def make_zip_csv(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def main() -> None:
    assert_equal(module.normalize_unitid("190150.0"), "190150", "UNITID decimal cleanup")
    assert_equal(module.normalize_unitid(" 190150 "), "190150", "UNITID whitespace")
    assert_equal(module.normalize_cip6("16.0104"), "160104", "CIP punctuation")
    assert_equal(module.normalize_cip6("1.0101"), "010101", "CIP leading zero")
    assert_equal(module.normalize_soc6("19-3051.00"), "19-3051", "O*NET to SOC")
    assert_equal(module.normalize_soc6("193051"), "19-3051", "SOC digits")
    assert_equal(module.value_status("PrivacySuppressed"), "suppressed", "Scorecard suppression")
    assert_equal(module.value_status("**"), "suppressed", "generic suppression")
    assert_equal(module.value_status("0"), "reported", "zero is reported")
    assert_equal(module.bls_value_status("**"), "topcoded", "BLS top-coded wage")
    assert_equal(module.bls_value_status("*"), "suppressed", "BLS unavailable estimate")
    assert_equal(module.parse_number("$52,000"), 52000.0, "BLS numeric parsing")

    candidate, reasons = module.community_college_pathway_flags(
        {"CONTROL": "1", "SECTOR": "1", "INSTCAT": "4"}
    )
    assert_equal(candidate, True, "INSTCAT recovers public associate-focused pathway")
    if "public_associates_certificates_instcat" not in reasons:
        raise AssertionError("INSTCAT community-college proxy reason missing")
    candidate, _ = module.community_college_pathway_flags(
        {"CONTROL": "2", "SECTOR": "4", "INSTCAT": "4"}
    )
    assert_equal(candidate, False, "community-college proxy is public-sector scoped")

    empty_qa = module.qa_report("fixture", [], ["ID"])
    assert_equal(empty_qa["status"], "fail", "zero-row QA must fail")

    sample = make_zip_csv(
        "HD2025.csv",
        "UNITID,INSTNM,CITY,STABBR,ZIP,CONTROL,LOCALE\n"
        "190150,Example College,New York,NY,10027,2,11\n",
    )
    member, rows = module.read_zip_table(sample)
    assert_equal(member, "HD2025.csv", "ZIP member")
    assert_equal(rows[0]["UNITID"], "190150", "ZIP CSV read")

    manifest = module.load_manifest()
    source_ids = {s["source_id"] for s in manifest["sources"]}
    required = {
        "college_scorecard",
        "ipeds_directory_2025",
        "ipeds_completions_2025",
        "cip_soc_crosswalk_2020_2018",
        "onet_31_0",
        "dapip_accreditation",
        "bls_employment_projections_2025_2035",
        "bls_oews_may_2025",
    }
    missing = required - source_ids
    if missing:
        raise AssertionError(f"manifest missing sources: {sorted(missing)}")

    expected_urls = {
        "ipeds_directory_2025": "https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip",
        "ipeds_completions_2025": "https://nces.ed.gov/ipeds/complete-data-files/C2025_A.zip",
        "cip_soc_crosswalk_2020_2018": "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx",
        "dapip_accreditation": "https://ope.ed.gov/dapip/api/downloadFiles/accreditationDataFiles",
        "bls_employment_projections_2025_2035": "https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx",
        "bls_oews_may_2025": "https://www.bls.gov/oes/special-requests/oesm25all.zip",
    }
    for source_id, expected_url in expected_urls.items():
        actual = module.resolve_access_url(module.get_source(source_id))
        assert_equal(actual, expected_url, f"{source_id} URL")

    onet = module.get_source("onet_31_0")
    required_onet_files = {
        "occupation_data",
        "essential_skills",
        "transferable_skills",
        "software_skills",
        "knowledge",
        "abilities",
        "education",
        "training_and_experience",
        "career_interest_types",
        "work_activities",
        "work_context",
        "related_occupations",
        "job_zones",
    }
    missing_onet = required_onet_files - set(onet.get("files", {}))
    if missing_onet:
        raise AssertionError(f"O*NET manifest missing files: {sorted(missing_onet)}")
    for name, url in onet["files"].items():
        if not str(url).startswith("https://www.onetcenter.org/dl_files/database/db_31_0_csv/"):
            raise AssertionError(f"O*NET {name}: unexpected URL {url}")

    for source_id in required:
        result = module.ingest_source(source_id, ROOT / "tmp" / "college-career-test", dry_run=True)
        assert_equal(result["mode"], "dry-run", f"{source_id} dry run")
        if source_id == "onet_31_0":
            if len(result.get("access_urls", {})) < len(required_onet_files):
                raise AssertionError("O*NET dry run did not expose configured source files")
        elif not str(result["access_url"]).startswith("https://"):
            raise AssertionError(f"{source_id}: dry-run URL must be HTTPS")
        if source_id == "dapip_accreditation":
            assert_equal(result.get("method"), "POST", "DAPIP dry-run method")
            assert_equal(result.get("payload"), {"CSVChecked": True, "ExcelChecked": False}, "DAPIP dry-run payload")

    print(
        "College + Career ingestion prototype tests passed: "
        f"{len(required)} sources, key normalization, coverage classification, ZIP parsing, and dry-run resolution."
    )


if __name__ == "__main__":
    main()
