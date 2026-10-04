from __future__ import annotations

import importlib.util
import io
import json
import shutil
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


def make_zip_files(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in files.items():
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
    assert_equal(module.bls_value_status("**"), "topcoded", "BLS topcode")
    assert_equal(module.bls_value_status("*"), "suppressed", "BLS suppression marker")
    assert_equal(module.parse_number("$12,345"), 12345.0, "BLS numeric parsing")

    community, reasons = module.community_college_pathway_flags({"CONTROL": "1", "SECTOR": "1", "INSTCAT": "4"})
    assert_equal(community, True, "community-college proxy recovers associate-focused public four-year")
    if "public_associates_certificates_instcat" not in reasons:
        raise AssertionError("community-college proxy did not record INSTCAT reason")

    carnegie_community, carnegie_reasons = module.community_college_pathway_flags(
        {"CONTROL": "1", "SECTOR": "1", "INSTCAT": "1", "C21BASIC": "14"}
    )
    assert_equal(carnegie_community, True, "community-college proxy recovers public baccalaureate/associate institution")
    if "public_associate_or_bacc_assoc_carnegie" not in carnegie_reasons:
        raise AssertionError("community-college proxy did not record Carnegie reason")
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

    dapip_fixture = make_zip_files({
        "InstitutionCampus.csv": (
            "DapipId,ParentDapipId,IpedsUnitIds,ParentName,LocationName,LocationType,Address,OpeId\n"
            '100,,"190150, 190151",Example University,Main Campus,Institution,"New York, NY",00123400\n'
        ),
        "AccreditationRecords.csv": (
            "DapipId,AgencyId,AgencyName,ProgramId,ProgramName,AccreditationEndDate,AccreditationStatus\n"
            "100,10,Example Accreditor,1,Institutional,,Accredited\n"
        ),
        "AccreditationActions.csv": (
            "DapipId,AgencyId,AgencyName,ProgramId,ProgramName,ActionDescription,ActionDate,EndDate,Justification\n"
            "100,10,Example Accreditor,1,Institutional,Renewal,01/01/2026,,\n"
        ),
    })
    dapip_fixture_dir = ROOT / "tmp" / "dapip-fixture"
    dapip_result = module.ingest_dapip(
        module.get_source("dapip_accreditation"),
        dapip_fixture,
        dapip_fixture_dir,
        module.get_source("dapip_accreditation")["access_url"],
    )
    assert_equal(dapip_result["qa"]["dapip_ipeds_bridge_rows"], 2, "DAPIP multi-UNITID bridge row count")
    bridge_rows = module.read_csv_path(dapip_fixture_dir / "normalized" / "dapip_ipeds_bridge.csv")
    assert_equal({row["UNITID"] for row in bridge_rows}, {"190150", "190151"}, "DAPIP multi-UNITID bridge")


    program_fixture_root = ROOT / "tmp" / "program-coverage-fixture"
    shutil.rmtree(program_fixture_root, ignore_errors=True)
    for source_id in ("ipeds_directory_2025", "ipeds_completions_2025", "cip_soc_crosswalk_2020_2018"):
        (program_fixture_root / source_id / "20261004T000000Z" / "normalized").mkdir(
            parents=True, exist_ok=True
        )

    module.write_csv(
        program_fixture_root / "ipeds_directory_2025" / "20261004T000000Z" / "normalized" / "institution.csv",
        ["UNITID", "INSTNM"],
        [
            {"UNITID": "100001", "INSTNM": "Mapped College"},
            {"UNITID": "100002", "INSTNM": "Unmapped College"},
            {"UNITID": "100003", "INSTNM": "No Completions College"},
        ],
    )
    module.write_csv(
        program_fixture_root / "ipeds_completions_2025" / "20261004T000000Z" / "normalized" / "program_completion.csv",
        ["UNITID", "CIP6", "AWLEVEL", "CTOTALT"],
        [
            {"UNITID": "100001", "CIP6": "010101", "AWLEVEL": "5", "CTOTALT": "10"},
            {"UNITID": "100001", "CIP6": "990000", "AWLEVEL": "5", "CTOTALT": "10"},
            {"UNITID": "100002", "CIP6": "020202", "AWLEVEL": "3", "CTOTALT": "4"},
        ],
    )
    module.write_csv(
        program_fixture_root / "cip_soc_crosswalk_2020_2018" / "20261004T000000Z" / "normalized" / "cip_soc_bridge.csv",
        ["CIP6", "SOC6"],
        [
            {"CIP6": "010101", "SOC6": "11-1011"},
            {"CIP6": "010101", "SOC6": "11-1021"},
        ],
    )
    program_coverage = module.build_program_coverage_report(program_fixture_root)["report"]
    assert_equal(
        program_coverage["unique_institution_program_award_combinations"],
        2,
        "program coverage excludes IPEDS summary CIP",
    )
    assert_equal(program_coverage["summary_cip_rows_excluded"], 1, "program summary row count")
    assert_equal(
        program_coverage["cip_soc_coverage"]["program_combinations_with_direct_mapping"],
        1,
        "mapped program combinations",
    )
    assert_equal(
        program_coverage["cip_soc_coverage"]["program_combinations_without_direct_mapping"],
        1,
        "unmapped program combinations",
    )
    assert_equal(
        program_coverage["institutions_with_specific_program_completions"],
        2,
        "institutions with specific program completions",
    )

    manifest = module.load_manifest()
    source_ids = {s["source_id"] for s in manifest["sources"]}
    required = {
        "college_scorecard",
        "dapip_accreditation",
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
        "dapip_accreditation": "https://ope.ed.gov/dapip/api/downloadFiles/accreditationDataFiles",
        "ipeds_directory_2025": "https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip",
        "ipeds_completions_2025": "https://nces.ed.gov/ipeds/complete-data-files/C2025_A.zip",
        "cip_soc_crosswalk_2020_2018": "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx",
        "bls_employment_projections_2025_2035": "https://data.bls.gov/projections/occupationProj",
        "bls_oews_may_2025": "https://data.bls.gov/oes/",
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
        elif source_id == "bls_oews_may_2025":
            assert_equal(result.get("access_url"), "https://data.bls.gov/oes/", "OEWS query app URL")
            assert_equal(result.get("service_base_url"), "https://data.bls.gov", "OEWS query service base")
            assert_equal(result.get("release_query_key"), "2025A01", "OEWS May 2025 query release")
            assert_equal(result.get("geography"), "National", "OEWS automation-safe baseline geography")
        elif source_id == "dapip_accreditation":
            assert_equal(result.get("method"), "POST", "DAPIP dry-run method")
            assert_equal(result.get("payload"), {"CSVChecked": True, "ExcelChecked": False}, "DAPIP dry-run payload")
        elif not str(result["access_url"]).startswith("https://"):
            raise AssertionError(f"{source_id}: dry-run URL must be HTTPS")

    print(
        "College + Career ingestion prototype tests passed: "
        f"{len(required)} sources, key normalization, coverage classification, ZIP parsing, and dry-run resolution."
    )


if __name__ == "__main__":
    main()
