#!/usr/bin/env python3
"""Regression tests for corrected partial-dimension and program-identity semantics."""
from __future__ import annotations
import csv, subprocess, sys, tempfile, unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
def write(p,rows):
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def read(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def run(script,*args):
 p=subprocess.run([sys.executable,str(PROJECT/script),*map(str,args)],text=True,capture_output=True)
 if p.returncode:raise AssertionError(f'{script} failed\n{p.stdout}\n{p.stderr}')
class SemanticFixRegression(unittest.TestCase):
 def test_normalizer_blocks_partial_unless_manifest_allows_renormalization(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);write(d/'c.csv',[{'candidate_id':'A','f1':'0.8','f2':''}])
   base=[{'feature':'f1','dimension':'fit','transform':'identity_0_1','direction':'higher_better','feature_weight':'1','missing_policy':'unknown','reference_id':'SYN','reference_min':'0','reference_max':'1','partial_policy':'block'},{'feature':'f2','dimension':'fit','transform':'identity_0_1','direction':'higher_better','feature_weight':'1','missing_policy':'unknown','reference_id':'SYN','reference_min':'0','reference_max':'1','partial_policy':'block'}]
   write(d/'m.csv',base);run('candidate_dimension_normalizer.py','--candidates',d/'c.csv','--manifest',d/'m.csv','--out-dir',d/'blocked');r=read(d/'blocked'/'candidate_dimensions_long.csv')[0];self.assertEqual(r['dimension_evidence_state'],'partial_blocked');self.assertEqual(r['dimension_value'],'')
   for x in base:x['partial_policy']='renormalize_observed'
   write(d/'m2.csv',base);run('candidate_dimension_normalizer.py','--candidates',d/'c.csv','--manifest',d/'m2.csv','--out-dir',d/'allowed');r=read(d/'allowed'/'candidate_dimensions_long.csv')[0];self.assertEqual(r['dimension_evidence_state'],'partial_renormalized');self.assertAlmostEqual(float(r['dimension_value']),.8)
 def test_program_summary_keeps_same_local_program_id_separate_across_institutions(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);write(d/'p.csv',[{'UNITID':'FIC-A','program_id':'P1','cip_code':'99.1'},{'UNITID':'FIC-B','program_id':'P1','cip_code':'99.2'}]);write(d/'x.csv',[{'cip_code':'99.1','occ_code':'99-1'},{'cip_code':'99.2','occ_code':'99-2'}]);write(d/'o.csv',[{'occ_code':'99-1','wage':'10'},{'occ_code':'99-2','wage':'20'}]);run('program_career_pathway_aggregator.py','--programs',d/'p.csv','--cip-soc',d/'x.csv','--occupation-evidence',d/'o.csv','--out-dir',d/'out');rows=read(d/'out'/'program_career_pathway_summary.csv');self.assertEqual(len(rows),2);self.assertEqual({(r['UNITID'],r['program_id']) for r in rows},{('FIC-A','P1'),('FIC-B','P1')})
if __name__=='__main__':unittest.main()
