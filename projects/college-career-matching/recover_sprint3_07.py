"""S3-07: recover HD2025 from the NCES official complete-data-files link.

Rerun prior S3-06 comparison with an official publisher-linked download URL.
Keep earlier S3-06 report as a historical audit; commit new S3-07 aggregates only.
Research; neither Census GEOIDs nor campus coordinates are newly approved.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import reconcile_sprint3_06 as prior
from audit_sprint3_geography import ROOT

OFFICIAL_ZIP = "https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip"
OFFICIAL_DICTIONARY = "https://nces.ed.gov/ipeds/complete-data-files/HD2025_Dict.zip"
OFFICIAL_CATALOG = "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7"
FINAL_JSON = ROOT / "research_aggregate/s3_07_hd2025_source_recovery.json"
FINAL_MD = ROOT / "S3_07_IPEDS_RECOVERY.md"
CASES = ROOT / "research_work/s3_07_49_case_comparison.json"

def main():
    prior.OFFICIAL_2025_URLS = [
        OFFICIAL_ZIP, *[x for x in prior.OFFICIAL_2025_URLS if x != OFFICIAL_ZIP]
    ]
    original_probe = prior.url_probe
    # Official distribution can take time; avoid mistaking a slow response for 404.
    def probe(url, limit=25_000_000, timeout=55):
        return original_probe(url, limit=limit, timeout=timeout)
    prior.url_probe = probe
    existing_registry = (ROOT / "research_aggregate/s3_05_approved_city_place_registry.json").read_bytes()
    prior.main()
    assert existing_registry == (ROOT / "research_aggregate/s3_05_approved_city_place_registry.json").read_bytes()

    evidence = json.loads((ROOT / "research_aggregate/s3_06_reconciliation_summary.json").read_text())
    cases = json.loads((ROOT / "research_work/s3_06_49_case_ledger.json").read_text())["rows"]
    assert len(cases) == evidence["records_reviewed"] == 49
    meta25 = evidence["2025_directory_metadata"]
    recovered = evidence["2025_directory_obtained"]
    candidates = Counter()
    by_old = defaultdict(Counter)
    changes = []
    for row in cases:
        prior24 = row["official_nces_2024_present"]
        current25 = row["official_nces_2025_present"]
        if recovered:
            status = ("both_years" if prior24 and current25 else
                      "new_in_2025" if (not prior24) and current25 else
                      "missing_in_2025" if prior24 and not current25 else
                      "missing_in_both")
            assert current25 is not None
        else:
            status = "2025_unavailable"
            assert current25 is None
        candidates[status] += 1
        by_old[row["s3_05_decision"]][status] += 1
        changes.append({
            "unitid": row["unitid"], "scorecard_city":row["scorecard_city"],
            "state": row["state"], "2024_directory_present": prior24,
            "2025_directory_present": current25,
            "crossyear_class":status,
            "2025_or_fallback_directory_name":row["directory_name"],
            "2025_or_fallback_directory_city":row["directory_city"],
            "2025_or_fallback_directory_state":row["directory_state"],
            "possible_6_digit_prefix":row["possible_branch_unitid_prefix"],
            "decision":row["s3_06_decision"],
            "approved_new_census_geoid":None,
            "exact_campus_location_verified":False,
        })
    if recovered:
        assert meta25 is not None
        assert meta25["url"] == OFFICIAL_ZIP
        assert len(meta25["zip_sha256"]) == 64
        assert len(meta25["csv_sha256"]) == 64
        assert meta25["record_count"] >= 5000
        assert sum(candidates.values())==49
        assert evidence["primary_directory_year"]==2025
    else:
        assert not meta25 and evidence["primary_directory_year"]==2024
    assert sum(candidates.values())==49
    assert all(x["approved_new_census_geoid"] is None for x in changes)
    assert evidence["new_approved_census_place_geoids"]==0
    now=datetime.now(timezone.utc).isoformat()
    data={
        "audit_utc":now,
        "official_nces_catalog":OFFICIAL_CATALOG,
        "recovered_direct_official_source":recovered,
        "official_archive_url_requested":OFFICIAL_ZIP,
        "official_dictionary_url":OFFICIAL_DICTIONARY,
        "official_archive_metadata":meta25,
        "all_attempts":evidence["2025_retrieval_probes"],
        "previous_fallback_vintage":"2024",
        "previous_fallback_sha256":evidence["2024_fallback_metadata"]["zip_sha256"],
        "reconciled_s3_05_pending_cases":len(cases),
        "crossyear_49_cases":dict(sorted(candidates.items())),
        "cases_grouped_by_prior_disposition":{
            k:dict(sorted(v.items())) for k,v in sorted(by_old.items())},
        "new_approved_place_geoids":0,
        "unchanged_public_city_label_coverage":5659,
        "unchanged_original_unresolved":584,
        "unchanged_s3_05_approved_city_place_proxy_count":3,
        "remaining_decisions":evidence["decisions"],
        "woodbury_and_pacifica_source_checks":evidence["institution_publisher_checks"],
        "institution_sites_tested":evidence["checks"].get("homepage_supplied"),
        "institution_sites_retrieved":evidence["checks"].get("homepage_retrieved"),
        "deployment_approved":False,
        "notes":[
            "HD2025 release is provisional according to 2026 NCES public release materials; validate release-specific metadata before aggregate uses.",
            "Presence or disappearance of a UNITID in a directory does not demonstrate physical campus opening, closure, legal parent, or moving.",
            "The source is an institution directory, not certified exact campus buildings or accessibility/routing data.",
            "Source ZIP and case-by-case input files exist only in CI runner; no source ZIP or address-coordinate fixture committed.",
            "S3-06 rerun report is local to CI as historical report remains unchanged in GitHub.",
        ],
    }
    FINAL_JSON.parent.mkdir(parents=True,exist_ok=True)
    FINAL_JSON.write_text(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    CASES.parent.mkdir(parents=True,exist_ok=True)
    CASES.write_text(json.dumps({"audited_at":now,"cases":changes},indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")

    body=[
        "# S3-07 — Recover official NCES IPEDS HD2025 and rerun identity lineage",
        "",
        "**Audit timestamp (UTC):** "+now,
        "",
        "**Scope:** Source recovery, validation and the 49-case 2024/2025 institution-identity comparison only. "
        "All new geographic/campus assignments remain unapproved and the live WordPress pages unchanged.",
        "",
        "## Source recovery",
        "",
        "NCES dataset catalog: "+OFFICIAL_CATALOG,
        "",
        "Official direct source URL obtained from a link labeled as the original NCES download: "
        +OFFICIAL_ZIP,
        "",
    ]
    if recovered:
        body += [
            "**HD2025 recovery: SUCCESS — authoritative publisher-hosted ZIP downloaded and parsed.**",
            "",
            "- Release year/vintage: **2025** (institutional directory). NCES materials identify 2025–26 as a provisional release; it is **not** a contemporaneous October 2026 location registry.",
            "- UNITIDs: **"+str(meta25["record_count"])+"** unique records.",
            "- ZIP SHA-256: \`"+meta25["zip_sha256"]+"\`.",
            "- Member CSV SHA-256: \`"+meta25["csv_sha256"]+"\`.",
            "- Official verified URL: "+meta25["final_url"],
            "- Bytes of official ZIP: "+str(meta25["bytes"])+".",
            "- Verified minimum fields: UNITID, INSTNM, ADDR, CITY, STABBR, ZIP; rejected duplicate UNITIDs.",
            "",
        ]
    else:
        body += [
            "**HD2025 recovery remains blocked:** attempted official ZIP URL not downloaded/parsed. "
            "Historical 2024 source remains correctly labeled as 2024, not substituted silently.",
            "",
        ]
    body += [
        "## 49 records compared to the 2024 directory",
        "",
        "| Cross-year status | S3-05 still-unapproved records |",
        "|---|---:|",
    ]
    for name,count in sorted(candidates.items()):
        body.append("| "+name.replace("_"," ")+" | "+str(count)+" |")
    body += [
        "",
        "This comparison never infers an institution's closure, merger, new branch, or exact campus location from inclusion/absence alone.",
        "",
        "## Historical identity holds",
        "",
        "- **Woodbury / University of Redlands Los Angeles:** merger officially announced completed July 6, 2026. Remains **held** until legal/survey UNITID lineage is corroborated, even if the historic UNITID still appears in an earlier directory.",
        "- **Pacifica:** its Lambert/Ladera instructional-campus transition continues through winter 2027. Remains **held** despite a 2025 directory address.",
        "- **All other pending cases:** keep their 2024/2025 source-specific statuses in the non-coordinate CI audit artifact; do not assign a Census place or school campus by fuzzy label or a numeric UNITID prefix.",
        "",
        "## Release gate and next steps",
        "",
        "No geographic filter, ZIP search, coordinates, 750 KiB browser payload, road distance, or public release was created. "
        "**Three** earlier approved *research-only* Census-place IDs remain unchanged; **5,659/6,243** "
        "baseline label matches remain unchanged; **584** still unresolved for production geographic functionality.",
        "",
        "Review the 49-case artifact to determine historical/campus identities with **current official institution pages and published NCES parent/child evidence**. "
        "Preserve the 2025 release provenance, audit any name/status changes rather than guessing.",
        "",
        "Sources: [NCES complete data files]("+OFFICIAL_CATALOG+"), "
        "[official 2025 directory ZIP]("+OFFICIAL_ZIP+"), "
        "[NCES IPEDS release information](https://nces.ed.gov/ipeds), "
        "[Woodbury merger publisher source](https://www.redlands.edu/about/office-of-the-president/presidents-messages/2026/university-of-redlands-and-woodbury-university-complete-historic-merger), "
        "[Pacifica campus transition](https://www.pacifica.edu/pacificas-campus-transition/).",
        "",
    ]
    FINAL_MD.write_text("\n".join(body),encoding="utf-8")
    print("S3_07_RECOVERY_AUDIT_PASS "+json.dumps({
        "hd2025_download_verified":recovered,
        "hd2025_count":meta25["record_count"] if recovered else None,
        "crossyear_49":dict(candidates),
        "source_sha256":meta25["zip_sha256"] if recovered else None,
        "approved_new_geoids":0,
    },sort_keys=True))

if __name__=="__main__":
    main()
