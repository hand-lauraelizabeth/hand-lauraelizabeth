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
    assert_equal(module.normalize_cip6("99"), "990000", "CIP summary serialization")
    assert_equal(module.normalize_cip6("99.0000"), "990000", "CIP summary decimal")
    assert_equal(module.normalize_soc6("19-3051.00"), "19-3051", "O*NET to SOC")
    assert_equal(module.normalize_soc6("193051"), "19-3051", "SOC digits")
    assert_equal(module.value_status("PrivacySuppressed"), "suppressed", "Scorecard suppression")
    assert_equal(module.value_status("**"), "suppressed", "generic suppression")
    assert_equal(module.value_status("0"), "reported", "zero is reported")
    assert_equal(module.bls_value_status("**"), "topcoded", "BLS topcode")
    assert_equal(module.bls_value_status("*"), "suppressed", "BLS suppression marker")
    assert_equal(module.parse_number("$12,345"), 12345.0, "BLS numeric parsing")

    # O*NET ingestion emits the reviewed work-activity preference artifact from the same pinned source snapshot.
    onet_fixture_root = ROOT / "tmp" / "onet-career-ingest-fixture"
    shutil.rmtree(onet_fixture_root, ignore_errors=True)
    onet_source = {
        "source_id": "onet_31_0", "official_url": "https://www.onetcenter.org/database.html",
        "release": {"label": "31.0"},
        "files": {"occupation_data": "https://fixture/occupation_data.csv", "work_activities": "https://fixture/work_activities.csv"},
    }
    onet_payloads = {
        "https://fixture/occupation_data.csv": b"O*NET-SOC Code,Title\\n15-2051.00,Data Scientists\\n15-2051.01,Bioinformatics Scientists\\n",
        "https://fixture/work_activities.csv": (
            "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Scale Name,Data Value,N,Standard Error,Lower CI Bound,Upper CI Bound,Recommend Suppress,Not Relevant,Date,Domain Source\\n"
            "15-2051.00,Data Scientists,4.A.2.a.4,Analyzing Data or Information,IM,Importance,4.50,10,0.1,4.3,4.7,N,N,2026-08,Analyst\\n"
            "15-2051.00,Data Scientists,4.A.2.b.1,Making Decisions and Solving Problems,IM,Importance,4.25,10,0.1,4.0,4.5,N,N,2026-08,Analyst\\n"
            "15-2051.00,Data Scientists,4.A.2.b.2,Thinking Creatively,IM,Importance,3.75,10,0.1,3.5,4.0,N,N,2026-08,Analyst\\n"
            "15-2051.01,Bioinformatics Scientists,4.A.2.a.4,Analyzing Data or Information,IM,Importance,5.00,10,0.1,4.8,5.0,N,N,2026-08,Analyst\\n"
        ).encode("utf-8"),
    }
    parsed_work_activities = module.read_delimited_bytes(onet_payloads["https://fixture/work_activities.csv"])
    assert_equal(parsed_work_activities[0].get("O*NET-SOC Code"), "15-2051.00", "O*NET fixture SOC parse")
    assert_equal(parsed_work_activities[0].get("Element ID"), "4.A.2.a.4", "O*NET fixture element parse")
    direct_career_attrs = module.normalize_onet_career_attributes(parsed_work_activities)
    assert_equal(len(direct_career_attrs), 3, "direct reviewed O*NET normalization")
    original_http_get = module.http_get
    module.http_get = lambda url, **kwargs: onet_payloads[url]
    try:
        onet_result = module.ingest_onet(onet_source, onet_fixture_root)
    finally:
        module.http_get = original_http_get
    career_attrs = module.read_csv_path(onet_fixture_root / "normalized" / "career_preference_attributes.csv")
    assert_equal(len(career_attrs), 3, "O*NET ingestion reviewed career preference rows")
    assert_equal({row["occ_code"] for row in career_attrs}, {"15-2051"}, "O*NET specialty rows not averaged")
    assert_equal(onet_result["coverage"]["career_preference_attributes"]["unique_base_soc6"], 1, "O*NET reviewed preference base-SOC coverage")

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

    scorecard_fixture = make_zip_csv(
        "Most-Recent-Cohorts-Institution.csv",
        "UNITID,INSTNM,CITY,STABBR,ZIP,CONTROL,LOCALE,PREDDEG,ICLEVEL,CURROPER,UGDS,STUFACR,ADM_RATE,SAT_AVG,SATVR25,SATVR75,SATMT25,SATMT75,ACTCM25,ACTCM75,TUITIONFEE_IN,TUITIONFEE_OUT,NPT4_PUB,NPT4_PRIV,OMAWDP8_ALL_POOLED_SUPP,C150_4_POOLED_SUPP,C150_L4_POOLED_SUPP,RET_FT4_POOLED_SUPP,RET_FTL4_POOLED_SUPP,DEBT_MDN,MD_EARN_WNE_P6,MD_EARN_WNE_P10\n"
        "100001,Public Community College,Alpha,NY,10001,1,21,2,2,1,5000,14,0.65,1100,500,650,520,670,21,28,5500,9500,12000,,0.61,,0.42,,0.72,9000,42000,PrivacySuppressed\n"
        "100002,Private University,Beta,NY,10002,2,12,3,1,1,8000,10,0.40,1250,600,700,610,710,26,31,45000,45000,,25000,PrivacySuppressed,0.55,,0.88,,18000,52000,65000\n",
    )
    scorecard_root = ROOT / "tmp" / "scorecard-bulk-fixture"
    shutil.rmtree(scorecard_root, ignore_errors=True)
    scorecard_source = module.get_source("college_scorecard")
    scorecard_result = module.ingest_scorecard(
        scorecard_source,
        scorecard_fixture,
        scorecard_root,
        "https://example.invalid/Most-Recent-Cohorts-Institution.zip",
    )
    assert_equal(scorecard_result["qa"]["status"], "pass", "Scorecard bulk fixture QA")
    assert_equal(scorecard_result["normalized_rows"], 2, "Scorecard bulk normalized rows")
    scorecard_rows = module.read_csv_path(scorecard_root / "normalized" / "institution_scorecard.csv")
    scorecard_by_id = {row["UNITID"]: row for row in scorecard_rows}
    assert_equal(scorecard_by_id["100001"]["latest.cost.avg_net_price.overall"], "12000", "public net price mapping")
    assert_equal(scorecard_by_id["100002"]["latest.cost.avg_net_price.overall"], "25000", "private net price mapping")
    assert_equal(scorecard_by_id["100001"]["latest.completion.consumer_rate"], "0.61", "degree-granting completion mapping")
    assert_equal(scorecard_by_id["100002"]["latest.completion.consumer_rate"], "0.55", "completion fallback mapping")
    assert_equal(scorecard_by_id["100001"]["latest.student.retention_rate"], "0.72", "less-than-four-year retention mapping")
    assert_equal(scorecard_by_id["100002"]["latest.student.retention_rate"], "0.88", "four-year retention mapping")
    assert_equal(scorecard_by_id["100001"]["latest.earnings.10_yrs_after_entry.median"], "", "Scorecard suppression remains null")

    scorecard_local_zip = scorecard_root / "Most-Recent-Cohorts-Institution_06102026.zip"
    scorecard_local_zip.write_bytes(scorecard_fixture)
    scorecard_local_output = ROOT / "tmp" / "scorecard-local-source-fixture"
    shutil.rmtree(scorecard_local_output, ignore_errors=True)
    scorecard_local_result = module.ingest_source(
        "college_scorecard",
        scorecard_local_output,
        source_file=scorecard_local_zip,
    )
    assert_equal(
        scorecard_local_result["retrieval_mode"],
        "user_supplied_official_bulk_zip",
        "Scorecard local official ZIP retrieval mode",
    )
    assert_equal(scorecard_local_result["normalized_rows"], 2, "Scorecard local official ZIP rows")

    baseline_config = module.load_coverage_baselines()
    assert_equal(set(baseline_config["layers"]), {"institution", "program", "career", "model_ready"}, "coverage baseline layers")

    program_floor_report = {}
    for metric_path, minimum in baseline_config["layers"]["program"]["minimums"].items():
        target = program_floor_report
        parts = metric_path.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = minimum
    assert_equal(
        module.evaluate_coverage_baseline("program", program_floor_report)["status"],
        "pass",
        "program coverage baseline at configured floors",
    )
    program_floor_report["completion_source_rows"] = 0
    assert_equal(
        module.evaluate_coverage_baseline("program", program_floor_report)["status"],
        "fail",
        "program coverage baseline detects shrinkage",
    )

    model_floor_report = {}
    model_config = baseline_config["layers"]["model_ready"]
    for section_name in ("minimums", "maximums", "equals"):
        for metric_path, expected in model_config.get(section_name, {}).items():
            target = model_floor_report
            parts = metric_path.split(".")
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = expected
    assert_equal(
        module.evaluate_coverage_baseline("model_ready", model_floor_report)["status"],
        "pass",
        "model-ready baseline at configured thresholds",
    )
    model_floor_report["auto_collapsed_institutions"] = 1
    assert_equal(
        module.evaluate_coverage_baseline("model_ready", model_floor_report)["status"],
        "fail",
        "model-ready baseline rejects identity auto-collapse",
    )

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
        ["UNITID", "MAJORNUM", "CIP6", "AWLEVEL", "CTOTALT"],
        [
            {"UNITID": "100001", "MAJORNUM": "1", "CIP6": "010101", "AWLEVEL": "5", "CTOTALT": "10"},
            {"UNITID": "100001", "MAJORNUM": "1", "CIP6": "990000", "AWLEVEL": "5", "CTOTALT": "10"},
            {"UNITID": "100001", "MAJORNUM": "2", "CIP6": "010101", "AWLEVEL": "5", "CTOTALT": "2"},
            {"UNITID": "100002", "MAJORNUM": "1", "CIP6": "020202", "AWLEVEL": "3", "CTOTALT": "4"},
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
    assert_equal(program_coverage["second_major_rows_excluded"], 1, "second-major row exclusion")
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


    preference_coverage_root = ROOT / "tmp" / "onet-preference-coverage-fixture"
    shutil.rmtree(preference_coverage_root, ignore_errors=True)
    (preference_coverage_root / "onet_31_0" / "20261006T000000Z" / "normalized").mkdir(parents=True, exist_ok=True)
    (preference_coverage_root / "cip_soc_crosswalk_2020_2018" / "20261006T000000Z" / "normalized").mkdir(parents=True, exist_ok=True)
    module.write_csv(
        preference_coverage_root / "cip_soc_crosswalk_2020_2018" / "20261006T000000Z" / "normalized" / "cip_soc_bridge.csv",
        ["CIP6", "SOC6"],
        [{"CIP6": "010101", "SOC6": "15-2051"}, {"CIP6": "010102", "SOC6": "15-2051"}, {"CIP6": "020202", "SOC6": "15-1252"}],
    )
    module.write_csv(
        preference_coverage_root / "onet_31_0" / "20261006T000000Z" / "normalized" / "career_preference_attributes.csv",
        ["occ_code", "attribute_id", "attribute_value", "evidence_state"],
        [
            {"occ_code": "15-2051", "attribute_id": "onet31:work_activity:4.A.2.a.4:IM", "attribute_value": "5", "evidence_state": "observed"},
            {"occ_code": "15-2051", "attribute_id": "onet31:work_activity:4.A.2.b.1:IM", "attribute_value": "4", "evidence_state": "observed"},
            {"occ_code": "15-2051", "attribute_id": "onet31:work_activity:4.A.2.b.2:IM", "attribute_value": "3", "evidence_state": "observed"},
            {"occ_code": "15-1252", "attribute_id": "onet31:work_activity:4.A.2.a.4:IM", "attribute_value": "4", "evidence_state": "observed"},
            {"occ_code": "15-1252", "attribute_id": "onet31:work_activity:4.A.2.b.1:IM", "attribute_value": "", "evidence_state": "suppressed"},
            {"occ_code": "15-1252", "attribute_id": "onet31:work_activity:4.A.2.b.2:IM", "attribute_value": "5", "evidence_state": "observed"},
        ],
    )
    pref_cov = module.build_onet_preference_coverage_report(preference_coverage_root)["report"]
    assert_equal(pref_cov["cip_soc_relationship_rows"], 3, "career-preference CIP-SOC relationship rows")
    assert_equal(pref_cov["unique_soc6"], 2, "career-preference distinct SOC6")
    assert_equal(pref_cov["soc6_with_all_reviewed_attributes_observed"], 1, "career-preference all-reviewed SOC6")
    assert_equal(pref_cov["cip_soc_relationship_rows_with_all_reviewed_attributes_observed"], 2, "career-preference relationship coverage preserves repeated SOC mappings")
    assert_equal(pref_cov["cip_soc_relationship_all_reviewed_coverage_rate"], 0.666667, "career-preference relationship coverage rate")
    assert_equal(pref_cov["per_attribute"]["career_problem_solving"]["cip_soc_relationship_rows_covered"], 2, "suppressed problem-solving evidence is not counted observed")



    model_root = ROOT / "tmp" / "model-ready-fixture"
    shutil.rmtree(model_root, ignore_errors=True)
    model_sources = (
        "ipeds_directory_2025",
        "ipeds_completions_2025",
        "cip_soc_crosswalk_2020_2018",
        "onet_31_0",
        "bls_employment_projections_2025_2035",
        "bls_oews_may_2025",
        "dapip_accreditation",
    )
    for source_id in model_sources:
        (model_root / source_id / "20261004T000000Z" / "normalized").mkdir(
            parents=True, exist_ok=True
        )

    module.write_csv(
        model_root / "ipeds_directory_2025" / "20261004T000000Z" / "normalized" / "institution.csv",
        ["UNITID", "INSTNM", "CITY", "STABBR", "ZIP", "CONTROL", "LOCALE", "SECTOR",
         "ICLEVEL", "DEGGRANT", "INSTCAT", "C21BASIC", "OPEID", "source_release"],
        [
            {"UNITID": "100001", "INSTNM": "Alpha College", "CITY": "A", "STABBR": "NY",
             "ZIP": "10001", "CONTROL": "1", "LOCALE": "11", "SECTOR": "1", "ICLEVEL": "1",
             "DEGGRANT": "1", "INSTCAT": "1", "C21BASIC": "15", "OPEID": "00111100",
             "source_release": "2025 provisional"},
            {"UNITID": "100002", "INSTNM": "Alpha Branch", "CITY": "B", "STABBR": "NY",
             "ZIP": "10002", "CONTROL": "1", "LOCALE": "12", "SECTOR": "4", "ICLEVEL": "2",
             "DEGGRANT": "1", "INSTCAT": "4", "C21BASIC": "2", "OPEID": "00111100",
             "source_release": "2025 provisional"},
            {"UNITID": "100003", "INSTNM": "Beta College", "CITY": "C", "STABBR": "NJ",
             "ZIP": "07001", "CONTROL": "2", "LOCALE": "21", "SECTOR": "2", "ICLEVEL": "1",
             "DEGGRANT": "1", "INSTCAT": "1", "C21BASIC": "15", "OPEID": "00222200",
             "source_release": "2025 provisional"},
        ],
    )
    module.write_csv(
        model_root / "ipeds_completions_2025" / "20261004T000000Z" / "normalized" / "program_completion.csv",
        ["UNITID", "MAJORNUM", "CIP6", "AWLEVEL", "CTOTALT", "source_id", "source_release"],
        [
            {"UNITID": "100001", "MAJORNUM": "1", "CIP6": "010101", "AWLEVEL": "5", "CTOTALT": "10",
             "source_id": "ipeds_completions_2025", "source_release": "2024-25"},
            {"UNITID": "100001", "MAJORNUM": "2", "CIP6": "010101", "AWLEVEL": "5", "CTOTALT": "2",
             "source_id": "ipeds_completions_2025", "source_release": "2024-25"},
            {"UNITID": "100003", "MAJORNUM": "1", "CIP6": "020202", "AWLEVEL": "3", "CTOTALT": "0",
             "source_id": "ipeds_completions_2025", "source_release": "2024-25"},
        ],
    )
    module.write_csv(
        model_root / "cip_soc_crosswalk_2020_2018" / "20261004T000000Z" / "normalized" / "cip_soc_bridge.csv",
        ["CIP6", "SOC6", "crosswalk_version"],
        [{"CIP6": "010101", "SOC6": "11-1011", "crosswalk_version": "CIP 2020 ↔ SOC 2018"}],
    )
    module.write_csv(
        model_root / "onet_31_0" / "20261004T000000Z" / "normalized" / "occupation_data.csv",
        ["ONET_SOC_CODE", "SOC6", "Title", "Description", "onet_version"],
        [{"ONET_SOC_CODE": "11-1011.00", "SOC6": "11-1011", "Title": "Chief Executives",
          "Description": "Determine and formulate policies.", "onet_version": "31.0"}],
    )
    module.write_csv(
        model_root / "bls_employment_projections_2025_2035" / "20261004T000000Z" / "normalized" / "occupation_outlook.csv",
        ["SOC6", "EMPLOYMENT_2025_THOUSANDS", "EMPLOYMENT_2035_THOUSANDS",
         "EMPLOYMENT_CHANGE_PERCENT_2025_2035", "ANNUAL_OPENINGS_2025_2035_THOUSANDS",
         "TYPICAL_EDUCATION", "projection_cycle"],
        [{"SOC6": "11-1011", "EMPLOYMENT_2025_THOUSANDS": "300", "EMPLOYMENT_2035_THOUSANDS": "310",
          "EMPLOYMENT_CHANGE_PERCENT_2025_2035": "3.3", "ANNUAL_OPENINGS_2025_2035_THOUSANDS": "20",
          "TYPICAL_EDUCATION": "Bachelor's degree", "projection_cycle": "2025-2035"}],
    )
    module.write_csv(
        model_root / "bls_oews_may_2025" / "20261004T000000Z" / "normalized" / "occupation_wage.csv",
        ["AREA", "AREA_TYPE", "IS_DETAILED", "OCC_CODE", "TOT_EMP", "TOT_EMP_STATUS",
         "A_PCT25", "A_MEDIAN", "A_PCT75", "A_MEDIAN_STATUS", "reference_period"],
        [{"AREA": "0000000", "AREA_TYPE": "National", "IS_DETAILED": "1", "OCC_CODE": "11-1011",
          "TOT_EMP": "200000", "TOT_EMP_STATUS": "reported", "A_PCT25": "90000",
          "A_MEDIAN": "150000", "A_PCT75": "220000", "A_MEDIAN_STATUS": "reported",
          "reference_period": "May 2025"}],
    )
    module.write_csv(
        model_root / "dapip_accreditation" / "20261004T000000Z" / "normalized" / "dapip_ipeds_bridge.csv",
        ["DAPIP_ID", "UNITID"],
        [
            {"DAPIP_ID": "500", "UNITID": "100001"},
            {"DAPIP_ID": "500", "UNITID": "100002"},
            {"DAPIP_ID": "600", "UNITID": "100003"},
        ],
    )
    module.write_csv(
        model_root / "dapip_accreditation" / "20261004T000000Z" / "normalized" / "institution_campus.csv",
        ["DAPIP_ID", "PARENT_DAPIP_ID", "LOCATION_TYPE", "OPEID"],
        [
            {"DAPIP_ID": "500", "PARENT_DAPIP_ID": "", "LOCATION_TYPE": "Institution", "OPEID": "00111100"},
            {"DAPIP_ID": "600", "PARENT_DAPIP_ID": "", "LOCATION_TYPE": "Institution", "OPEID": "00222200"},
        ],
    )
    module.write_csv(
        model_root / "dapip_accreditation" / "20261004T000000Z" / "normalized" / "accreditation_records.csv",
        ["DAPIP_ID", "IS_INSTITUTIONAL", "IS_CURRENT_BY_EXPORT_RULE"],
        [
            {"DAPIP_ID": "500", "IS_INSTITUTIONAL": "1", "IS_CURRENT_BY_EXPORT_RULE": "1"},
            {"DAPIP_ID": "600", "IS_INSTITUTIONAL": "1", "IS_CURRENT_BY_EXPORT_RULE": "1"},
        ],
    )

    model_ready = module.build_model_ready_layer(model_root)
    model_qa = model_ready["qa"]
    assert_equal(model_qa["institution_rows"], 3, "model-ready institution rows")
    assert_equal(model_qa["distinct_recommendation_entities"], 3, "UNITIDs remain distinct entities")
    assert_equal(model_qa["shared_exact_identifier_clusters"], 1, "shared DAPIP review cluster")
    assert_equal(model_qa["auto_collapsed_institutions"], 0, "no identity auto-collapse")
    assert_equal(model_qa["program_rows_first_major"], 2, "second-major excluded from model-ready programs")
    assert_equal(model_qa["programs_without_direct_cip_soc_mapping"], 1, "unmapped program retained")
    pathway_fixture_rows = module.read_csv_path(Path(model_ready["files"]["pathway"]))
    assert_equal(
        any(row["PATHWAY_RELATIONSHIP_TYPE"] == "no_direct_cip_soc_mapping" for row in pathway_fixture_rows),
        True,
        "unmapped program pathway row retained",
    )
    identity_fixture_rows = module.read_csv_path(Path(model_ready["files"]["identity"]))
    assert_equal(
        {row["RECOMMENDATION_ENTITY_ID"] for row in identity_fixture_rows},
        {"UNITID:100001", "UNITID:100002", "UNITID:100003"},
        "identity resolution preserves each UNITID",
    )

    assert_equal(
        model_ready["manifest"]["identity_policy"]["automatic_collapse"],
        False,
        "model-ready manifest records no automatic collapse",
    )
    assert_equal(
        model_qa["baseline_validation"]["status"],
        "fail",
        "small fixture remains below production model-ready baseline",
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
        "college_scorecard": "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_06102026.zip",
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
        elif source_id == "college_scorecard":
            assert_equal(result.get("requires_api_key"), False, "Scorecard bulk download is keyless")
            assert_equal(result.get("retrieval_mode"), "official_featured_bulk_zip", "Scorecard bulk retrieval mode")
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
