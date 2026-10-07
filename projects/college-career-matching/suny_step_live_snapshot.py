#!/usr/bin/env python3
"""Capture the public SUNY STEP Transfer Agreement Inventory as a raw CSV snapshot.

Uses only the Python standard library so it can run in a lightweight local/CI
environment. It parses the authoritative HTML table and preserves the visible
source fields without interpreting institution or program identity.

Source: https://step.transfer.suny.edu/agreements/
"""
from __future__ import annotations
import argparse, csv, html, json, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

SOURCE_URL="https://step.transfer.suny.edu/agreements/"
EXPECTED_HEADERS=["ID","Initial Campus","Partner Campus","Type","Program","Destination","Source"]

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table=False; self.in_row=False; self.in_cell=False
        self.cell=[]; self.row=[]; self.rows=[]
    def handle_starttag(self, tag, attrs):
        if tag=="table" and not self.in_table: self.in_table=True
        elif self.in_table and tag=="tr": self.in_row=True; self.row=[]
        elif self.in_row and tag in {"th","td"}: self.in_cell=True; self.cell=[]
    def handle_data(self, data):
        if self.in_cell: self.cell.append(data)
    def handle_endtag(self, tag):
        if self.in_cell and tag in {"th","td"}:
            self.row.append(" ".join(html.unescape("".join(self.cell)).split()))
            self.in_cell=False
        elif self.in_row and tag=="tr":
            if self.row: self.rows.append(self.row)
            self.in_row=False
        elif self.in_table and tag=="table":
            self.in_table=False

def fetch(url: str) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":"college-career-matcher/1.0 (+portfolio research)"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read().decode("utf-8","replace")

def parse(text: str):
    p=TableParser();p.feed(text)
    if not p.rows: raise ValueError("No HTML table rows found")
    header=p.rows[0]
    if header[:len(EXPECTED_HEADERS)]!=EXPECTED_HEADERS:
        raise ValueError(f"Unexpected STEP headers: {header}")
    records=[]
    for row in p.rows[1:]:
        if len(row)<len(EXPECTED_HEADERS): row=row+[""]*(len(EXPECTED_HEADERS)-len(row))
        records.append(dict(zip(EXPECTED_HEADERS,row[:len(EXPECTED_HEADERS)])))
    return records

def run(output: Path, html_output: Path|None=None):
    text=fetch(SOURCE_URL)
    if html_output:
        html_output.parent.mkdir(parents=True,exist_ok=True);html_output.write_text(text,encoding="utf-8")
    rows=parse(text)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=EXPECTED_HEADERS);w.writeheader();w.writerows(rows)
    return {
        "source_url":SOURCE_URL,
        "retrieved_at":datetime.now(timezone.utc).isoformat(),
        "record_count":len(rows),
        "first_source_id":rows[0]["ID"] if rows else None,
        "last_source_id":rows[-1]["ID"] if rows else None,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--html-output",type=Path)
    ap.add_argument("--metadata-output",type=Path)
    a=ap.parse_args()
    meta=run(a.output,a.html_output)
    if a.metadata_output:
        a.metadata_output.parent.mkdir(parents=True,exist_ok=True)
        a.metadata_output.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(meta,indent=2,sort_keys=True))
if __name__=="__main__": main()
