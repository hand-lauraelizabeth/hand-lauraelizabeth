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
    assert_equal(module.value_status("**"), "suppressed", "BLS suppression")
    assert_equal(module.value_status("0"), "reported", "zero is reported")

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
        "bls_employment_projections_2025_2035",
        "bls_oews_may_2025",
    }
    missing = required - source_ids
    if missing:
        raise AssertionError(f"manifest missing sources: {sorted(missing)}")

    expected_urls = {
        "ipeds_directory_2025": "https://nces.ed.gov/ipeds/datacenter/data/HD2025.zip",
        "ipeds_completions_2025": "https://nces.ed.gov/ipeds/datacenter/data/C2025_A.zip",
        "cip_soc_crosswalk_2020_2018": "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx",
        "onet_31_0": "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip",
        "bls_employment_projections_2025_2035": "https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx",
        "bls_oews_may_2025": "https://www.bls.gov/oes/special-requests/oesm25all.zip",
    }
    for source_id, expected_url in expected_urls.items():
        actual = module.resolve_access_url(module.get_source(source_id))
        assert_equal(actual, expected_url, f"{source_id} URL")

    for source_id in required:
        result = module.ingest_source(source_id, ROOT / "tmp" / "college-career-test", dry_run=True)
        assert_equal(result["mode"], "dry-run", f"{source_id} dry run")
        if not str(result["access_url"]).startswith("https://"):
            raise AssertionError(f"{source_id}: dry-run URL must be HTTPS")

    print(
        "College + Career ingestion prototype tests passed: "
        f"{len(required)} sources, key normalization, ZIP parsing, and dry-run resolution."
    )


if __name__ == "__main__":
    main()
