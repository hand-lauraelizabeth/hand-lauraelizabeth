"""Optional LibreOffice Calc CSV reopening test (synthetic records only). Requires Node 22 and LibreOffice."""
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parent
if not shutil.which("libreoffice"):
    raise SystemExit("LibreOffice required for optional interoperability test")
node = """import {normalizeEvidence,exportEvidenceCSV} from './core.mjs';
import {writeFileSync} from 'node:fs';
const rows=normalizeEvidence([
{sourceId:'  A-01  ',date:'2026-10-15',claim:'Quoted "text"\\nsecond line',group:' Case α '},
{sourceId:'é-02',date:'2026-10-16',claim:'＝1+1'},
{sourceId:'B-03',date:'2026-10-17',claim:'=HYPERLINK("https://invalid.example","click")'},
{sourceId:'C-04',date:'2026-10-18',claim:'＠SUM(1,2)'}]);
writeFileSync(process.argv[1],exportEvidenceCSV(rows));"""
with tempfile.TemporaryDirectory(prefix="ft05-lo-") as d:
    tmp = Path(d)
    csv = tmp / "synthetic.csv"
    subprocess.run(["node","--input-type=module","-e",node,str(csv)],cwd=root,check=True,capture_output=True)
    subprocess.run(["libreoffice",f"-env:UserInstallation={(tmp/'profile').as_uri()}","--headless","--convert-to","xlsx","--outdir",str(tmp),str(csv)],check=True,capture_output=True,timeout=30)
    with zipfile.ZipFile(tmp / "synthetic.xlsx") as archive:
        ns={"s":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet=ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        strings=[]
        if "xl/sharedStrings.xml" in archive.namelist():
            shared=ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings=["".join(si.itertext()) for si in shared.findall("s:si",ns)]
        cells={}
        for c in sheet.findall(".//s:c",ns):
            v=c.find("s:v",ns); inline=c.find("s:is",ns)
            if c.attrib.get("t")=="s" and v is not None: value=strings[int(v.text)]
            elif inline is not None: value="".join(inline.itertext())
            else: value=v.text if v is not None else ""
            cells[c.attrib["r"]]=(value,c.find("s:f",ns) is not None)
        expected={"A2":"  A-01  ","C2":'Quoted "text"\nsecond line',"F2":" Case α ","A3":"é-02","C3":"'＝1+1","C4":"""'=HYPERLINK("https://invalid.example","click")""","C5":"'＠SUM(1,2)"}
        for addr,value in expected.items():
            assert cells[addr][0]==value,(addr,cells[addr][0],value)
        assert all(not cells[f"C{r}"][1] for r in range(2,6))
        print("8 LibreOffice CSV-to-XLSX checks passed; dates may be auto-typed")
