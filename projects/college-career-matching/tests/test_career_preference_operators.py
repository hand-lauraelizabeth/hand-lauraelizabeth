#!/usr/bin/env python3
"""Exercise all declared career-preference operators through the real module."""
from __future__ import annotations
import csv,subprocess,sys,tempfile,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
def write(p,rows):
 with p.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def read(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def run(*args):
 p=subprocess.run([sys.executable,str(PROJECT/'career_preference_alignment.py'),*map(str,args)],text=True,capture_output=True)
 if p.returncode:raise AssertionError(p.stderr)
class OperatorIntegration(unittest.TestCase):
 def test_all_five_operator_semantics(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);write(d/'paths.csv',[{'candidate_id':'FIC','occ_code':'99-1'}]);write(d/'attrs.csv',[{'occ_code':'99-1','attribute_id':'target','attribute_value':'8'},{'occ_code':'99-1','attribute_id':'higher','attribute_value':'8'},{'occ_code':'99-1','attribute_id':'lower','attribute_value':'2'},{'occ_code':'99-1','attribute_id':'range','attribute_value':'6'},{'occ_code':'99-1','attribute_id':'category','attribute_value':'Hybrid'}])
   common={'importance':'1','priority_explicit':'true','scale_min':'0','scale_max':'10','target_min':'','target_max':''}
   prefs=[dict(common,preference_id='p1',attribute_id='target',operator='target_distance',target_value='7'),dict(common,preference_id='p2',attribute_id='higher',operator='higher_preferred',target_value=''),dict(common,preference_id='p3',attribute_id='lower',operator='lower_preferred',target_value=''),dict(common,preference_id='p4',attribute_id='range',operator='range',target_value='',target_min='5',target_max='7'),dict(common,preference_id='p5',attribute_id='category',operator='categorical_match',target_value='hybrid',scale_min='',scale_max='')]
   write(d/'prefs.csv',prefs);run('--pathways',d/'paths.csv','--occupation-attributes',d/'attrs.csv','--preferences',d/'prefs.csv','--out-dir',d/'out');rows=read(d/'out'/'career_preference_alignment_detail.csv');by={r['operator']:float(r['alignment']) for r in rows};self.assertAlmostEqual(by['target_distance'],.9);self.assertAlmostEqual(by['higher_preferred'],.8);self.assertAlmostEqual(by['lower_preferred'],.8);self.assertAlmostEqual(by['range'],1);self.assertAlmostEqual(by['categorical_match'],1)
   summary=read(d/'out'/'career_pathway_alignment.csv')[0];self.assertEqual(summary['career_alignment_observed_preferences'],'5');self.assertAlmostEqual(float(summary['career_alignment_coverage_rate']),1)
if __name__=='__main__':unittest.main()
