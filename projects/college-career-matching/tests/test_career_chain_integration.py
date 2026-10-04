#!/usr/bin/env python3
"""Synthetic integration: program -> CIP/SOC -> preferences -> optionality."""
from __future__ import annotations
import csv, subprocess, sys, tempfile, unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
def write(path,rows):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def read(path):
 with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def run(script,*args):
 p=subprocess.run([sys.executable,str(PROJECT/script),*map(str,args)],text=True,capture_output=True)
 if p.returncode: raise AssertionError(f'{script} failed\n{p.stdout}\n{p.stderr}')
class CareerChain(unittest.TestCase):
 def test_many_to_many_survives_chain(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td); agg=d/'agg'; aln=d/'aln'; opt=d/'opt'
   write(d/'programs.csv',[{'UNITID':'FIC001','program_id':'P-A','cip_code':'99.0001'}])
   write(d/'crosswalk.csv',[{'cip_code':'99.0001','occ_code':x} for x in ['99-0001','99-0002','99-0003']])
   write(d/'occ.csv',[{'occ_code':'99-0001','wage':'70000'},{'occ_code':'99-0002','wage':'90000'},{'occ_code':'99-0003','wage':'50000'}])
   write(d/'candidates.csv',[{'candidate_id':'FIC001::P-A','UNITID':'FIC001','program_id':'P-A'}])
   run('program_career_pathway_aggregator.py','--programs',d/'programs.csv','--cip-soc',d/'crosswalk.csv','--occupation-evidence',d/'occ.csv','--candidates',d/'candidates.csv','--out-dir',agg)
   paths=read(agg/'program_career_pathway_evidence.csv'); self.assertEqual(len(paths),3)
   s=read(agg/'program_career_pathway_summary.csv')[0]; self.assertEqual(s['pathway_count'],'3'); self.assertEqual(float(s['wage__median']),70000)
   write(d/'attrs.csv',[{'occ_code':'99-0001','attribute_id':'creative','attribute_value':'8'},{'occ_code':'99-0001','attribute_id':'structure','attribute_value':'5'},{'occ_code':'99-0002','attribute_id':'creative','attribute_value':'4'},{'occ_code':'99-0002','attribute_id':'structure','attribute_value':'8'},{'occ_code':'99-0003','attribute_id':'creative','attribute_value':'9'}])
   write(d/'prefs.csv',[{'preference_id':'creative','attribute_id':'creative','target_value':'9','importance':'2','priority_explicit':'true','scale_min':'1','scale_max':'10'},{'preference_id':'structure','attribute_id':'structure','target_value':'5','importance':'1','priority_explicit':'true','scale_min':'1','scale_max':'10'},{'preference_id':'hidden','attribute_id':'unused','target_value':'10','importance':'99','priority_explicit':'false','scale_min':'1','scale_max':'10'}])
   run('career_preference_alignment.py','--pathways',agg/'program_career_pathway_evidence.csv','--occupation-attributes',d/'attrs.csv','--preferences',d/'prefs.csv','--out-dir',aln)
   aligned=read(aln/'career_pathway_alignment.csv'); self.assertEqual(len(aligned),3); by={r['occ_code']:r for r in aligned}
   self.assertEqual(by['99-0003']['career_alignment_total_explicit_preferences'],'2'); self.assertAlmostEqual(float(by['99-0003']['career_alignment_coverage_rate']),.5); self.assertAlmostEqual(float(by['99-0003']['career_alignment_score']),1)
   write(d/'labels.csv',[{'occ_code':'99-0001','occupation_title':'Fictional Systems Storyteller'},{'occ_code':'99-0002','occupation_title':'Fictional Operations Designer'},{'occ_code':'99-0003','occupation_title':'Fictional Research Maker'}])
   run('career_pathway_optionality_summarizer.py','--alignment',aln/'career_pathway_alignment.csv','--occupation-labels',d/'labels.csv','--out-dir',opt)
   o=read(opt/'career_optionality_summary.csv')[0]; self.assertEqual(o['career_pathway_count'],'3'); self.assertEqual(o['career_alignment_observed_pathways'],'3'); self.assertEqual(o['strong_alignment_pathway_count'],'')
   reps=read(opt/'career_representative_pathways.csv'); self.assertEqual(len(reps),3); self.assertEqual(reps[0]['occ_code'],'99-0003')
if __name__=='__main__': unittest.main()
