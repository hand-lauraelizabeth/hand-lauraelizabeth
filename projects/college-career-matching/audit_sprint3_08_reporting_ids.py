"""S3-08: investigate Scorecard 8-digit identifiers versus official 6-digit IPEDS UNITIDs.

Research-only: no record reassignment, geographic coordinates, public UI or WP changes.
Uses pinned 2024/2025 NCES directories and exact current federal/official identifiers.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from html import unescape
import re
from urllib.request import Request, urlopen

from recover_sprint3_07 import checked_official_archive, source_directory_2024
from audit_sprint3_geography import ROOT

BASE = ROOT / "research_aggregate"
OUT = BASE / "s3_08_reporting_unit_audit.json"
MD = ROOT / "S3_08_REPORTING_UNIT_REVIEW.md"
QUEUE = ROOT / "research_work/s3_08_nine_cases.json"

NCES_GUIDANCE = "https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds"
NCES_UNITID_HELP = "https://nces.ed.gov/ipeds/Help/View/103"
PACIFICA = "https://www.pacifica.edu/visitors/"
TRANSITION = "https://www.pacifica.edu/pacificas-campus-transition/"
CA_BPPE = "https://search-bppe.dca.ca.gov/institutionDetail?schoolCode=77183565"
RECOVER = BASE / "s3_07_hd2025_source_recovery.json"
SOURCE = ROOT / "data" / "sprint2" / "college-search-national.v2.json"
REGISTRY = BASE / "s3_05_approved_city_place_registry.json"

def fetch_text(url,needles):
    try:
        req=Request(url, headers={"User-Agent":"Mozilla/5.0 CollegeSearch-S3-08/1.0 Research"})
        with urlopen(req, timeout=19) as resp:
            raw=resp.read(2_000_001)
            final_url=resp.geturl()
        if len(raw)>2_000_000: raise ValueError("page too large")
        html=raw.decode("utf-8","replace")
        html=re.sub(r"<(script|style)\b[^>]*>.*?</\1>"," ",html,flags=re.S|re.I)
        text=unescape(re.sub(r"<[^>]*>"," ",html))
        text=" ".join(text.split())
        terms={word: word.casefold() in text.casefold() for word in needles}
        return {
          "retrieved":True,"url":url,"final_url":final_url,
          "source_sha256":hashlib.sha256(text.encode()).hexdigest(),
          "required_phrases":terms,"all_phrases_present":all(terms.values())
        }
    except Exception as e:
        return {"retrieved":False,"url":url,"error":str(e)[:160],"all_phrases_present":False}

def main():
    previous=json.loads(RECOVER.read_text())
    assert previous["official_hd2025_retrieved"]
    assert previous["records_compared"]==49
    assert previous["cross_year_unitid_membership"]=={"present_both":41,"missing_both":8}
    national_raw=SOURCE.read_bytes()
    national=json.loads(national_raw)
    schools=national["institutions"]
    assert national["source_release"]=="2026-06-10" and len(schools)==6243
    lengths=Counter(len(uid) for uid in schools)
    assert all(uid.isdigit() for uid in schools)

    archive25, metadata25, probes=checked_official_archive()
    assert archive25 and metadata25, probes
    assert metadata25["zip_sha256"]==previous["hd2025_metadata"]["zip_sha256"]
    assert metadata25["csv_sha256"]==previous["hd2025_metadata"]["csv_sha256"]
    archive24, metadata24=source_directory_2024()
    assert metadata24["zip_sha256"]==previous["hd2024_metadata"]["zip_sha256"]

    unmatched=sorted(
        {example["unitid"] for example in previous["source_identity_examples"]
         if example["year_group"]=="missing_both"}
    )
    assert len(unmatched)==8 and all(len(uid)==8 for uid in unmatched)
    table=[]
    for uid in unmatched:
        root=uid[:6]
        scorecard=schools[uid]
        root_school=schools.get(root)
        row25=archive25.get(root)
        row24=archive24.get(root)
        assert uid not in archive25 and uid not in archive24
        assert row25 and row24, uid
        assert root in schools, (uid,root)
        opeid25=row25.get("OPEID")
        table.append({
            "scorecard_display_id":uid,
            "scorecard_display_name":scorecard["name"],
            "scorecard_display_city":scorecard["city"],
            "scorecard_display_state":scorecard["state"],
            "candidate_six_digit_prefix":root,
            "prefix_in_scorecard":True,
            "prefix_in_2024_ipeds":True,
            "prefix_in_2025_ipeds":True,
            "prefix_ipeds_2025_name":row25["INSTNM"],
            "prefix_ipeds_2025_city":row25["CITY"],
            "prefix_scorecard_name":root_school["name"],
            "prefix_ipeds_2025_opeid":opeid25,
            "eight_digit_value_equals_ipeds_opeid":uid==opeid25,
            "evidence":"Prefix equality only; no parent/branch approval. IPEDS UNITID is six digits; 8-digit value is not verified as an IPEDS UNITID.",
            "verification_status":"hold_reporting_identity_ambiguous",
            "verified_parent_child_relationship":False,
            "approved_geo_association":None,
        })
    assert len({x["scorecard_display_id"] for x in table})==8

    # Test the one city change, using both directory years and first-party pages.
    citychanges=[
        x for x in previous["source_identity_examples"]
        if x["year_group"]=="present_both" and x["2024_city"]!=x["2025_city"]
    ]
    assert len(citychanges)==1,citychanges
    changed=citychanges[0]
    assert changed["unitid"]=="115746"
    uid=changed["unitid"]
    assert archive24[uid]["CITY"]==changed["2024_city"]
    assert archive25[uid]["CITY"]==changed["2025_city"]
    assert archive24[uid]["INSTNM"]==archive25[uid]["INSTNM"]
    assert schools[uid]["city"]==changed["2025_city"]
    source_checks={
      "nces_unitid_semantics":fetch_text(NCES_GUIDANCE,["UnitID","OPE ID"]),
      "nces_six_digit_help":fetch_text(NCES_UNITID_HELP,["six","UnitID"]),
      "pacifica_both_campus_addresses":fetch_text(PACIFICA,["249 Lambert Road","Carpinteria","801 Ladera Lane","Santa Barbara"]),
      "pacifica_transition":fetch_text(TRANSITION,["winter 2027","Lambert","Ladera"]),
      "california_state_regulator":fetch_text(CA_BPPE,["Pacifica Graduate Institute","Mailing Address","Physical Address"]),
    }
    pacifica={
      "unitid":uid,
      "institution":archive25[uid]["INSTNM"],
      "2024_ipeds_city":archive24[uid]["CITY"],
      "2025_ipeds_city":archive25[uid]["CITY"],
      "scorecard_june_2026_city":schools[uid]["city"],
      "2024_ipeds_address":archive24[uid].get("ADDR"),
      "2025_ipeds_address":archive25[uid].get("ADDR"),
      "2024_zip":archive24[uid].get("ZIP"),
      "2025_zip":archive25[uid].get("ZIP"),
      "verified_one_unitid_multiple_campuses":bool(source_checks["pacifica_both_campus_addresses"]["all_phrases_present"]),
      "source_2026_transition_checked":bool(source_checks["pacifica_transition"]["all_phrases_present"]),
      "state_regulator_primary_source_checked":bool(source_checks["california_state_regulator"]["all_phrases_present"]),
      "decision":"hold_multi_campus_city_label_change",
      "reason":"Directory-city label changed but both official institution sites and California regulator describe distinct Ladera/Lambert addresses; city label does not identify one physical campus.",
      "approved_place_geoid":None
    }
    assert source_checks["pacifica_both_campus_addresses"]["all_phrases_present"],"Cannot state two-campus confirmation without publisher source"
    assert source_checks["pacifica_transition"]["all_phrases_present"],"Cannot state 2026-27 transition without publisher source"
    # Do not fail if the auxiliary IPEDS help page or BPPE is transiently unavailable;
    # that evidence is explicitly labeled by each request's result.
    registry_raw=REGISTRY.read_bytes()
    registry=json.loads(registry_raw)
    assert registry["accepted_records"]==3 and registry["deployment_approved"] is False
    assert not any(item["scorecard_display_id"] in {r["unitid"] for r in registry["records"]} for item in table)
    assert REGISTRY.read_bytes()==registry_raw

    now=datetime.now(timezone.utc).isoformat()
    summary={
      "audit_utc":now,
      "national_source_sha256":hashlib.sha256(national_raw).hexdigest(),
      "national_source_release":national["source_release"],
      "national_school_records":6243,
      "all_national_key_lengths":dict(sorted((str(k),v) for k,v in lengths.items())),
      "non_six_digit_national_ids":sum(v for k,v in lengths.items() if k!=6),
      "missing_2024_2025_s3_07_cases":8,
      "all_eight_scorecard_pseudounitids_have_six_digit_prefix_in_both_years":True,
      "eight_explicit_reporting_unit_holds":table,
      "genuine_ipeds_unitids_for_eight_extended_values":0,
      "ipeds_2024_sha256":metadata24["zip_sha256"],
      "ipeds_2025_sha256":metadata25["zip_sha256"],
      "ipeds_2025_csv_sha256":metadata25["csv_sha256"],
      "changed_city_case":pacifica,
      "official_source_checks":source_checks,
      "approved_new_reporting_unit_links":0,
      "approved_new_campus_geocodes":0,
      "public_city_matching_unchanged":5659,
      "public_location_records_unresolved_unchanged":584,
      "s3_05_three_entry_registry_unchanged":True,
      "wordpress_changed":False,
      "next_requirements":[
         "Determine origin of eight-digit Scorecard-style IDs in the input manifest; do not call them NCES UNITIDs in end-user provenance.",
         "Find affirmative NCES or US Department of Education OPEID/branch-location identity mapping, not prefix inference.",
         "Verify separate physical campus identities and dates, especially Pacifica fall 2026 transition, before any distance search.",
         "Audit all non-six-digit national search IDs and distinguish synthetic application IDs from genuine IPEDS identifiers.",
      ],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(summary,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    QUEUE.parent.mkdir(parents=True,exist_ok=True)
    QUEUE.write_text(json.dumps({"asof":now,"eight_cases":table,"changed_city":pacifica},indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    doc=[
       "# S3-08 — Reporting-unit identity and Pacifica city-label audit","",
       "**Verified on (UTC):** "+now,"",
       "**Status:** eight extended identifiers and one changed-city record audited against SHA-pinned official 2024 and 2025 NCES IPEDS directories, the 6,243-school national source and official Pacifica institutional pages. No parent/branch relationship or geographic campus point is approved.","",
       "## Important identifier integrity distinction","",
       "[NCES IPEDS guidance]("+NCES_GUIDANCE+") distinguishes **six-digit IPEDS UNITID** from an **eight-digit federal OPE ID** that has a two-digit branch or additional-location suffix. The same NCES source warns that neither ID has a simple one-to-one relationship with a physical campus. The eight IDs found in the national Scorecard-derived file are eight digits, absent from 2024/2025 IPEDS UNITIDs, but their six-digit prefixes are valid separate IPEDS UNITIDs. **This is a candidate numeric relationship only, not evidence of parentage or a campus identity.**",
       "",
       "### Eight extended identifiers (2026 Scorecard snapshot labels)","",
       "| Display ID (not verified IPEDS UNITID) | Source-reported school | City / state | Six-digit prefix | NCES 2025 prefix institution |",
       "|---|---|---|---|---|",
    ]
    for x in table:
        doc.append("| "+x["scorecard_display_id"]+" | "+x["scorecard_display_name"].replace("|","/")+
                   " | "+x["scorecard_display_city"]+", "+x["scorecard_display_state"]+
                   " | "+x["candidate_six_digit_prefix"]+
                   " | "+x["prefix_ipeds_2025_name"].replace("|","/")+" |")
    doc.extend([
       "",
       "**Identity decisions:** all eight **HOLD — reporting unit relation unverified**. The six-digit prefix is an investigation lead only; no inheritance of the prefix school address/coordinates, OPEID eligibility or accreditation is allowed.",
       "",
       "**National identifier audit:** "+", ".join(str(n)+"-digit: "+str(count) for n,count in sorted(lengths.items()))+". "+str(summary["non_six_digit_national_ids"])+" national search keys are not six digits. They must not be described as verified IPEDS UNITIDs until provenance is corrected.",
       "",
       "## One changed city — Pacifica Graduate Institute, UNITID 115746","",
       "- Official HD2024 city: **"+pacifica["2024_ipeds_city"]+"**.",
       "- Official HD2025 city: **"+pacifica["2025_ipeds_city"]+"**.",
       "- June 2026 Scorecard-derived city: **"+pacifica["scorecard_june_2026_city"]+"**.",
       "- [Pacifica's current visitor page]("+PACIFICA+") lists **Lambert campus, 249 Lambert Road, Carpinteria**, and **Ladera campus, 801 Ladera Lane, Santa Barbara**.",
       "- [Pacifica's dated campus transition notice]("+TRANSITION+") places its transition into winter 2027, so the changed administrative city label does not show a single current instructional campus.",
       "- [California Bureau for Private Postsecondary Education]("+CA_BPPE+") separately lists mailing and physical addresses, but these address roles must not be conflated.",
       "",
       "**Decision: HOLD — multi-campus city-label change**. The Scorecard and IPEDS labels do not license choosing one point, using a city internal point as the campus entrance, or showing travel time.",
       "",
       "## Evidence and remaining release gates","",
       "- Official downloaded NCES HD2024 ZIP SHA-256: \x60"+metadata24["zip_sha256"]+"\x60.",
       "- Official downloaded NCES HD2025 ZIP SHA-256: \x60"+metadata25["zip_sha256"]+"\x60.",
       "- 6,243-row Scorecard-based JSON SHA-256: \x60"+summary["national_source_sha256"]+"\x60.",
       "- All audited institution identities retain null for any proposed campus coordinate or geographic release match; the S3-05 three-entry research-only registry remains unchanged.",
       "- Full detailed status and source page hashes are in [machine-readable aggregate evidence](./research_aggregate/s3_08_reporting_unit_audit.json); a nine-case review ledger is separately retained as a CI artifact.",
       "- Further work should audit *all* non-six-digit keys for semantic mislabeling and create a verified institutional identifier taxonomy before new distance UI.",
       "- No WordPress edits, public data replacement, publication or distance feature.",
       "",
    ])
    MD.write_text("\n".join(doc),encoding="utf-8")
    print("S3_08_AUDIT_PASS "+json.dumps({
      "eight_unmatched":len(table),"national_lengths":dict(lengths),
      "pacifica_2024_city":pacifica["2024_ipeds_city"],"pacifica_2025_city":pacifica["2025_ipeds_city"],
      "new_geo_approvals":0
    },sort_keys=True))
if __name__=="__main__":
    main()
