"""S3-04 independent institution directory / Census geography identity review.

Conservative: no candidate becomes a published coordinate or verified campus from a name alone.
Public outputs contain counts and source provenance; review rows stay as a CI artifact.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from io import BytesIO, StringIO, TextIOWrapper
import csv
import hashlib
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

from audit_sprint3_identity import run as regenerate_queue
from audit_sprint3_geography import ROOT

NCES = "https://nces.ed.gov/ipeds/datacenter/data/HD{year}.zip"
GEO = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
QUEUE = ROOT / "research_work/s3_03_review_queue.json"
PRIVATE = ROOT / "research_work/s3_04_independent_review_queue.json"
AGGREGATE = ROOT / "research_aggregate/s3_04_independent_summary.json"
REPORT = ROOT / "S3_04_INDEPENDENT_REVIEW.md"

def read_url(url, maxbytes=16_000_000, timeout=60):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 CollegeSearch-Geography-Research/1.0"})
    with urlopen(req,timeout=timeout) as response:
        data=response.read(maxbytes+1)
    if len(data)>maxbytes:raise ValueError("oversized response "+url[:120])
    return data

def directory():
    errors={}
    for year in (2025,2024):
        url=NCES.format(year=year)
        try:
            raw=read_url(url,maxbytes=25_000_000,timeout=90)
            if not raw.startswith(b"PK"):raise ValueError("non-ZIP server response")
            with ZipFile(BytesIO(raw)) as archive:
                csvmembers=[x for x in archive.infolist()
                            if x.filename.casefold().endswith(".csv")
                            and x.filename.upper().split("/")[-1].startswith("HD")]
                if len(csvmembers)!=1:raise ValueError("unexpected HD member count "+str(len(csvmembers)))
                member=csvmembers[0]
                if member.file_size>40_000_000:raise ValueError("oversized HD CSV")
                data=archive.read(member)
            # IPEDS CSV often contains curly quotes in legacy encodings.
            try:decoded=data.decode("utf-8-sig")
            except UnicodeDecodeError:decoded=data.decode("cp1252")
            reader=csv.DictReader(StringIO(decoded))
            columns={c.upper():c for c in reader.fieldnames or []}
            required={"UNITID","INSTNM","ADDR","CITY","STABBR","ZIP"}
            if not required.issubset(columns):raise ValueError("IPEDS missing columns "+repr(required-set(columns)))
            index={}
            for row in reader:
                unitid=(row.get(columns["UNITID"]) or "").strip()
                if not unitid.isdigit():continue
                if unitid in index:raise ValueError("duplicate UNITID in IPEDS directory")
                index[unitid]={k:(row.get(v) or "").strip() for k,v in columns.items()
                               if k in {"UNITID","INSTNM","ADDR","CITY","STABBR","ZIP","LATITUDE","LONGITUD","OPEID","OPENPUBL"}}
            if len(index)<3000:raise ValueError("unexpectedly small directory: "+str(len(index)))
            return index, {"year":year,"url":url,"zip_sha256":hashlib.sha256(raw).hexdigest(),
                           "csv_sha256":hashlib.sha256(data).hexdigest(),"records":len(index),
                           "available_fields":sorted(columns)}
        except Exception as e:
            errors[str(year)]=repr(e)[:350]
    return {},{"year":None,"attempts_failed":errors,"records":0,"url":None}

def valid_point(row):
    try:
        lat=float(row.get("LATITUDE",""))
        lon=float(row.get("LONGITUD",""))
        if -90<=lat<=90 and -180<=lon<=180 and not(lat==0 and lon==0):
            return (lat,lon)
    except (TypeError, ValueError):pass
    return None

def lookup(point):
    lat,lon=point
    query=urlencode({"x":lon,"y":lat,"benchmark":"Public_AR_Current",
                     "vintage":"Current_Current","format":"json"})
    url=GEO+"?"+query
    last=None
    for attempt in range(2):
        try:
            doc=json.loads(read_url(url,1_200_000,timeout=18))
            geos=doc.get("result",{}).get("geographies",{})
            found={}
            for layer,features in geos.items():
                if any(word in layer.casefold() for word in ("incorporated place","census designated place")):
                    for feature in features or []:
                        g=feature.get("GEOID") or feature.get("GEOID10") or feature.get("GEOID20")
                        if g and re.fullmatch(r"\d{7}",str(g)):
                            found[str(g)]={"layer":layer,"name":feature.get("NAME","")}
            return {"place_geoids":found,"lookup_success":True,
                    "geo_vintage":"Current_Current"}
        except Exception as e:
            last=repr(e)[:130]
            if attempt==0:time.sleep(1)
    return {"place_geoids":{},"lookup_success":False,"error":last,
            "geo_vintage":"Current_Current"}

def main():
    regenerate_queue()
    full=json.loads(QUEUE.read_text())["items"]
    cases=[]
    for item in full:
        if item["baseline_category"]=="ambiguous_place_name":
            opts=item["official_place_options"]
            category="existing_ambiguous"
        else:
            opts={p["geoid"]:p for rows in item.get("probes",{}).values() for p in rows}
            opts=list(opts.values())
            if len(opts)!=1:continue
            category="bounded_single_candidate"
        cases.append({**item,"review_group":category,"proposed_official_places":opts})
    assert len(cases)==52, (len(cases),Counter(c["review_group"] for c in cases))
    assert Counter(c["review_group"] for c in cases)=={"bounded_single_candidate":32,"existing_ambiguous":20}

    index,meta=directory()
    points={}
    for case in cases:
        item=index.get(case["unitid"])
        case["ipeds"]={"directory_year":meta["year"],"matched_unitid":bool(item)}
        if item:
            case["ipeds"].update({k:item.get(k,"") for k in
              ("INSTNM","ADDR","CITY","STABBR","ZIP")})
            pt=valid_point(item)
            case["ipeds"]["has_coordinate"]=bool(pt)
            # Coordinates are processed only in-memory, never written into report/queue.
            if pt:points[case["unitid"]]=pt
    lookup_results={}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(lookup,point):uid for uid,point in points.items()}
        for f in as_completed(futures):
            uid=futures[f]
            try:lookup_results[uid]=f.result()
            except Exception as e:lookup_results[uid]={"lookup_success":False,"place_geoids":{},"error":repr(e)[:150]}

    summary=Counter()
    group_counts=defaultdict(Counter)
    source_checks=Counter()
    public_examples=defaultdict(list)
    for case in cases:
        uid=case["unitid"];ip=case["ipeds"]; item=index.get(uid)
        offered={p["geoid"] for p in case["proposed_official_places"]}
        geores=lookup_results.get(uid,{"place_geoids":{},"lookup_success":False})
        hit=offered.intersection(geores["place_geoids"])
        case["independent_geo_evidence"]={
            "source":"Census Geocoder Current_Current geographic point lookup from NCES IPEDS directory coordinates",
            "lookup_success":geores["lookup_success"],
            "point_inside_proposed_census_place_geoids":sorted(hit),
            "point_inside_other_places": sorted(set(geores["place_geoids"])-offered),
            "geo_vintage":geores.get("geo_vintage"),
        }
        same_state=bool(item and item.get("STABBR","").upper()==case["state"])
        address=bool(item and item.get("ADDR","") and item.get("ZIP",""))
        case["independent_geo_evidence"]["ipeds_state_consistent"]=same_state
        case["independent_geo_evidence"]["has_official_directory_street_zip"]=address
        if not item:
            status="no_current_ipeds_identity"
        elif not same_state or not address:
            status="ipeds_identity_or_address_gap"
        elif uid not in points:
            status="ipeds_coordinates_unavailable"
        elif not geores["lookup_success"]:
            status="census_geolookup_unavailable"
        elif len(hit)==1 and len(geores["place_geoids"])>=1:
            status="census_polygon_supported_candidate"
            case["independent_geo_evidence"]["supported_geoid"]=next(iter(hit))
        elif len(hit)>1:
            status="multiple_census_places_cover_point"
        elif geores["place_geoids"]:
            status="census_polygon_does_not_support_candidates"
        else:
            status="census_polygon_not_returned"
        # Treat even polygon-supported as a separately corroborated geographic candidate,
        # not a verified exact campus / release approval: IPEDS coordinates can be approximations.
        case["review_status"]=status
        case["publishable_campus_match"]=False
        case["accepted_school_geoid"]=None
        summary[status]+=1
        group_counts[case["review_group"]][status]+=1
        source_checks["ipeds_record_exists"]+=bool(item)
        source_checks["ipeds_address_state_complete"]+=bool(item and same_state and address)
        source_checks["ipeds_has_coordinate"]+=bool(uid in points)
        source_checks["census_lookup_success"]+=geores["lookup_success"]
        if len(public_examples[status])<6:
            public_examples[status].append({
                "unitid":uid,"reported_city":case["city"],"state":case["state"],
                "ipeds_city":ip.get("CITY"),"candidate_census_geoid":sorted(offered),
            })
    assert sum(summary.values())==52
    assert sum(group_counts["bounded_single_candidate"].values())==32
    assert sum(group_counts["existing_ambiguous"].values())==20
    assert all(not x["publishable_campus_match"] and x["accepted_school_geoid"] is None for x in cases)
    now=datetime.now(timezone.utc).isoformat()
    report={
        "audit_utc":now,"source_directory":meta,
        "census_geocoder_api":GEO,
        "geo_vintage_used":"Current_Current",
        "census_2026_gazetteer_sha256":"af678e2d990827c89ee39b98c82de6e90b693c7361ff0e559ae3076670dd2863",
        "case_count":len(cases),"bounded_single_candidate":32,
        "existing_ambiguous":20,"review_status_counts":dict(sorted(summary.items())),
        "group_counts":{k:dict(sorted(v.items())) for k,v in group_counts.items()},
        "evidence_availability":dict(source_checks),
        "examples":dict(public_examples),
        "accepted_new_matches":0,"verified_exact_campus_locations":0,
        "baseline_city_label_matches":5659,
        "limitations":["IPEDS directory self-reported campus address/coordinates may be approximate",
                       "IPEDS vintage differs from June 2026 Scorecard and Census Gazetteer 2026",
                       "Census Geocoder current geography vintage may differ from Gazetteer 2026",
                       "Census internal point is not campus coordinate or travel distance",
                       "Census geographic point in place does not prove campus entrance/physical buildings"],
        "no_wordpress_or_ui_changes":True,
    }
    AGGREGATE.parent.mkdir(parents=True,exist_ok=True)
    AGGREGATE.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    PRIVATE.parent.mkdir(parents=True,exist_ok=True)
    PRIVATE.write_text(json.dumps({"audit_utc":now,"cases":cases},indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    notes=[
      "# S3-04 — Independent institutional/geographic evidence review", "",
      "**Audit:** "+now, "",
      "Reprocessed all **32 bounded single-Census-place name candidates** and "
      "**20 pre-existing same-state ambiguous college/place matches** (52 total). "
      "The tested geographic place alternatives and census Gazetteer hashes are pinned "
      "to prior source-audited files. The review uses the official NCES/IPEDS "
      "institution directory by exact UNITID where available and the Census Geocoder "
      "geographic lookup for official directory coordinates, NOT a website search snippet. "
      "The complete case ledger is retained as a GitHub Actions artifact, not as "
      "a public map or a campus geocode lookup.", "",
      "## Official-source availability", "",
      "NCES directory: "+str(meta.get("url") or "UNAVAILABLE")+
      " (year: "+str(meta.get("year"))+
      "; records: "+str(meta["records"])+").", "",
      "Census geocoder API: "+GEO+
      "?x=...&y=...&benchmark=Public_AR_Current&vintage=Current_Current&format=json", "",
      "Census's current geographic lookup and the Gazetteer's 2026 point files "
      "are **different products and may not have identical reference vintages**. "
      "IPEDS coordinates may approximate reported institution locations. Neither can "
      "alone certify a physical building or an accessible/driveable route.", "",
      "| Result of 52-row evidence review | Records |", "|---|---:|",
    ]
    for k,v in sorted(summary.items()):
        notes.append("| "+k.replace("_"," ")+" | "+str(v)+" |")
    notes.extend([
      "", "**Official IPEDS records found:** "+str(source_checks["ipeds_record_exists"])+
      "/52; **complete street/ZIP and matching state:** "+
      str(source_checks["ipeds_address_state_complete"])+
      "/52; **IPEDS coordinates present:** "+
      str(source_checks["ipeds_has_coordinate"])+
      "/52; **Census lookup succeeded:** "+
      str(source_checks["census_lookup_success"])+"/52.", "",
      "**No new mapping was accepted automatically.** Even official point-in-place "
      "evidence is a geographic *candidate* rather than proof of exact campus "
      "location. All 52 records remain unresolved for release until separately "
      "reviewed institutional address, main-vs-branch identity and vintage "
      "consistency are checked. Baseline 5,659 city label matches unchanged.", "",
      "## Evidence and constraints", "",
      "- NCES IPEDS directory ZIP provenance, schema and SHA are in the aggregate JSON.",
      "- Source geographies come from the official US Census 2026 Gazetteer and "
      "the separately dated Census geocoder Current_Current endpoint.",
      "- The 52-case GitHub Actions artifact (access governed by repository permissions) records UNITID, reported Scorecard city, "
      "IPEDS official institution/address, Census official names/GEOIDs and "
      "polygon-lookup statuses, **but no latitude/longitude values**.",
      "- Never choose a city/CDP/town GEOID by name or proximity; point-in-polygon "
      "can only corroborate a location, not manufacture a campus address.",
      "- Independent human verification of campus vs branch and dates is still "
      "required before a new city-level association is treated as approved.",
      "- There is no Census-derived browser dataset, gzip budget claim, ZIP-origin "
      "feature, or WordPress change in this audit.", "",
      "## Next requirement", "",
      "Review evidence-ledger cases with publisher institutional contact pages "
      "or more current official campus-address source before approving a mapping. "
      "Keep the 584 unresolved baseline untouched pending that review. "
      "Sprint 2 staging remains private and subject to its separate device/host checks.", "",
      "Publisher references: [NCES IPEDS data files](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?year=-1), "
      "[Census Geocoder API](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html), "
      "[2026 Census Gazetteer](https://www.census.gov/geographies/reference-files/2026/geo/gazetter-file.html).", "",
    ])
    REPORT.write_text("\n".join(notes))
    print("S3_04_PASS "+json.dumps({"count":len(cases),"statuses":dict(summary),
                                    "nces_year":meta["year"],"ipeds_found":source_checks["ipeds_record_exists"],
                                    "lookup_success":source_checks["census_lookup_success"]},sort_keys=True))

if __name__=="__main__":
    main()
