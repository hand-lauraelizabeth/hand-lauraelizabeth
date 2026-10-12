"""Rebuild verified 2022/2023 SAT/ACT school evidence from owner-supplied Scorecard ZIPs.

All-years ZIP is intentionally private and never committed. Uses only FALL 2023
and FALL 2022 institutional cohorts to fill fully absent fall 2024 *exam* data.
Never mixes cohort years inside an exam; older-year actual 50ths are required
for the category ranges. SAT total quartiles are section sums, not true total
score quartiles. Outlying historical section-sum spreads >500 are withheld.
"""
import argparse, csv, gzip, hashlib, io, json, zipfile
from pathlib import Path

CURRENT_SHA = "f56a181b000ca4914e924c16b6b81dcc656e25aeb2ac68ab7d271ac0f29ffd58"
ALL_SHA = "bfe3add63069fea1fa61c8b910bfaef9d29baa3ae68702e6595b04d2023293a1"
YEAR_FILES = [("2023_24","2023"),("2022_23","2022")]
URL = "https://collegescorecard.ed.gov/data/"
EXPECTED = {"rows":1247,"sat_avg":1164,"act_reference":1015,"sat_complete_bands":1051,"act_complete_bands":965}

def checksum(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def num(value):
    try:
        v = float(value)
        if v.is_integer():
            return int(v)
    except (TypeError, ValueError):
        pass
    return None

def ordered(values,lo,hi):
    return (len(values)==3 and all(type(x)==int and lo<=x<=hi for x in values)
            and values[0]<=values[1]<=values[2])

def latest_ids(archive):
    with zipfile.ZipFile(archive) as z:
        csvs=[n for n in z.namelist() if n.endswith(".csv") and not n.startswith("__MACOSX/")]
        if len(csvs)!=1: raise ValueError("Expected one source CSV")
        with z.open(csvs[0]) as f:
            reader=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
            ids={r["UNITID"] for r in reader if r.get("CURROPER")=="1"}
    if len(ids)!=6243:raise ValueError("Operating institutional universe mismatch")
    return ids

def archived_exam_rows(z,year,ids):
    filename=next((name for name in z.namelist() if name.endswith(f"MERGED{year}_PP.csv") and not name.startswith("__MACOSX/")),None)
    if not filename:raise ValueError("Missing historical year "+year)
    with z.open(filename) as f:
        rows=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
        required={"UNITID","SAT_AVG","SATVR25","SATVR50","SATVR75","SATMT25","SATMT50","SATMT75","ACTCM25","ACTCM50","ACTCM75"}
        if not required.issubset(rows.fieldnames or []):raise ValueError("Missing official field")
        seen=set()
        for row in rows:
            uid=row["UNITID"]
            if uid not in ids:continue
            if uid in seen:raise ValueError("Duplicate historical UNITID")
            seen.add(uid)
            a=[num(row["SATVR"+p]) for p in ("25","50","75")]
            b=[num(row["SATMT"+p]) for p in ("25","50","75")]
            sat=[x+y for x,y in zip(a,b)] if ordered(a,200,800) and ordered(b,200,800) else [None]*3
            if not ordered(sat,400,1600) or sat[2]-sat[0]>500:sat=[None]*3
            act=[num(row["ACTCM"+p]) for p in ("25","50","75")]
            if not ordered(act,1,36) or act[2]-act[0]>18:act=[None]*3
            avg=num(row["SAT_AVG"])
            if avg is None or not 400<=avg<=1600:avg=None
            if avg is not None or sat[0] is not None or act[0] is not None:
                # ACTCM50 is a real median. ACTCMMID is NA in these files;
                # do not treat the actual median as a computed midpoint.
                yield uid,avg,sat,act

def build(base,archive,current_archive):
    if checksum(archive)!=ALL_SHA or checksum(current_archive)!=CURRENT_SHA:
        raise ValueError("Official archive checksum mismatch")
    ids=latest_ids(current_archive)
    doc=json.loads(Path(base).read_text())
    if doc["schema_version"]!=2 or doc["source_archive_sha256"]!=CURRENT_SHA or doc["school_count"]!=6243:
        raise ValueError("Unexpected current verified score overlay")
    old=doc["institutions"]
    if not set(old).issubset(ids):raise ValueError("Non-operating institution in current overlay")
    data={uid:list(row) for uid,row in old.items()}
    sources=dict(doc["source_registry"])
    with zipfile.ZipFile(archive) as z:
        for year,cohort_year in YEAR_FILES:
            source_id="scorecard_historical_"+cohort_year
            sources[source_id]={
                "provider":"U.S. Department of Education",
                "dataset":"College Scorecard historic institution-level "+year+" / IPEDS admissions",
                "url":URL,"release":"2026-06-10","cohort":"Fall "+cohort_year,
                "fields":"SAT_AVG, SATVR25/50/75, SATMT25/50/75, ACTCM25/50/75",
                "sat_composite_estimated":True,"is_historical":True,
                "source_archive_sha256":ALL_SHA,
                "source_file":"MERGED"+year+"_PP.csv","act_reference_field":"ACTCM50",
            }
            for uid,avg,sat,act in archived_exam_rows(z,year,ids):
                row=data.get(uid,[None]*10)
                changed=False
                if not any(x is not None for x in [row[0],*row[2:5]]) and (avg is not None or sat[0] is not None):
                    row[0]=avg;row[2:5]=sat;row[8]=source_id;changed=True
                if not any(x is not None for x in [row[1],*row[5:8]]) and act[0] is not None:
                    row[1]=act[1];row[5:8]=act;row[9]=source_id;changed=True
                if changed:data[uid]=row
    for uid,row in data.items():
        if uid not in ids or len(row)!=10:raise ValueError("Invalid historical row")
        for index in (8,9):
            if row[index] is not None and row[index] not in sources:
                raise ValueError("Missing source provenance")
    cnt=lambda index:sum(row[index] is not None for row in data.values())
    counts={"rows":len(data),"sat_avg":cnt(0),"act_reference":cnt(1),
            "sat_complete_bands":cnt(2),"act_complete_bands":cnt(5)}
    if counts!=EXPECTED:raise ValueError("Coverage drift: "+repr(counts))
    doc["schema_version"]=3
    doc["historical_archive_sha256"]=ALL_SHA
    doc["historical_backfill"]={
        "policy":"Latest available separate exam cohort only when latest verified exam metrics entirely unavailable",
        "cohorts_in_order":["Fall 2023","Fall 2022"],
        "do_not_mix_years_within_exam":True,
        "report_as_historical":True,
        "conventional_category_qualified_as_historical":True,
        "historical_pre_2022_excluded_from_matching":True
    }
    doc["source_registry"]=sources
    doc["school_scores"]={"sat_avg":cnt(0),"act_reference":cnt(1)}
    doc["verified_band_counts"]={"sat_complete_bands":cnt(2),"act_complete_bands":cnt(5)}
    doc["institutions"]=dict(sorted(data.items()))
    raw=json.dumps(doc,separators=(",",":"),ensure_ascii=False).encode()
    packed=gzip.compress(raw,compresslevel=9,mtime=0)
    if 259736+len(packed)>750*1024:raise ValueError("Exceeded 750 KiB combined gzip budget")
    return raw,packed,counts

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--current-archive",type=Path,required=True)
    p.add_argument("--overlay",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    raw,gz,counts=build(args.overlay,args.archive,args.current_archive)
    if args.check:
        if args.output.read_bytes()!=raw:raise ValueError("Source data JSON drift")
    else:
        args.output.write_bytes(raw)
        args.output.with_suffix(args.output.suffix+".gz").write_bytes(gz)
    print(json.dumps({"pass":True,"counts":counts,"json_bytes":len(raw),
                      "gzip_bytes":len(gz),"combined_national_plus_scores_gzip":259736+len(gz)}))
