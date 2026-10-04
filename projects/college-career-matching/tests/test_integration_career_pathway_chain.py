#!/usr/bin/env python3
"""End-to-end synthetic test: program/CIP → SOCs → preferences → optionality."""
from __future__ import annotations
import csv,subprocess,sys,tempfile,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
def write_csv(path,rows):
 with path.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def read_csv(path):
 with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def run(script,*args):
 p=subprocess.run([sys.executable,str(PROJECT/script),*map(str,args)],text=True,capture_output=True)
 if p.returncode:raise AssertionError(f'{script} failed\nSTDOUT:{p.stdout}\nSTDERR:{p.stderr}')
class CareerPathwayChainIntegration(unittest.TestCase):
 def test_program_to_multiple_careers_alignment_and_optionality(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);agg=d/'agg';align=d/'align';opt=d/'opt'
   write_csv(d/'programs.csv',[{'UNITID':'FIC-U1','program_id':'FIC-P1','cip_code':'99.9999'}]);write_csv(d/'candidates.csv',[{'candidate_id':'FIC-U1::FIC-P1','UNITID':'FIC-U1','program_id':'FIC-P1'}]);write_csv(d/'cip_soc.csv',[{'cip_code':'99.9999','occ_code':x} for x in ['99-0001','99-0002','99-0003']]);write_csv(d/'occupation_evidence.csv',[{'occ_code':'99-0001','annual_wage':'50000','projection_growth':'5'},{'occ_code':'99-0002','annual_wage':'70000','projection_growth':'10'},{'occ_code':'99-0003','annual_wage':'SUPPRESSED','projection_growth':'2'}])
   run('program_career_pathway_aggregator.py','--programs',d/'programs.csv','--cip-soc',d/'cip_soc.csv','--occupation-evidence',d/'occupation_evidence.csv','--candidates',d/'candidates.csv','--out-dir',agg);paths=read_csv(agg/'program_career_pathway_evidence.csv');self.assertEqual(len(paths),3);summary=read_csv(agg/'program_career_pathway_summary.csv')[0];self.assertEqual(summary['annual_wage__observed_n'],'2');self.assertEqual(float(summary['annual_wage__median']),60000)
   write_csv(d/'attrs.csv',[{'occ_code':'99-0001','attribute_id':'creative','attribute_value':'8'},{'occ_code':'99-0001','attribute_id':'analysis','attribute_value':'7'},{'occ_code':'99-0002','attribute_id':'creative','attribute_value':'5'},{'occ_code':'99-0002','attribute_id':'analysis','attribute_value':'9'},{'occ_code':'99-0003','attribute_id':'creative','attribute_value':'9'}]);write_csv(d/'prefs.csv',[{'preference_id':'PREF-C','attribute_id':'creative','operator':'target_distance','target_value':'9','importance':'2','priority_explicit':'true','scale_min':'0','scale_max':'10'},{'preference_id':'PREF-A','attribute_id':'analysis','operator':'target_distance','target_value':'8','importance':'1','priority_explicit':'true','scale_min':'0','scale_max':'10'},{'preference_id':'PREF-OFF','attribute_id':'social','operator':'target_distance','target_value':'10','importance':'99','priority_explicit':'false','scale_min':'0','scale_max':'10'}]);run('career_preference_alignment.py','--pathways',agg/'program_career_pathway_evidence.csv','--occupation-attributes',d/'attrs.csv','--preferences',d/'prefs.csv','--out-dir',align);aligned=read_csv(align/'career_pathway_alignment.csv');by={r['occ_code']:r for r in aligned};self.assertEqual(by['99-0003']['career_alignment_observed_preferences'],'1');self.assertAlmostEqual(float(by['99-0003']['career_alignment_coverage_rate']),.5);self.assertAlmostEqual(float(by['99-0003']['career_alignment_score']),1)
   write_csv(d/'labels.csv',[{'occ_code':'99-0001','occupation_title':'Fictional Design Analyst'},{'occ_code':'99-0002','occupation_title':'Fictional Systems Planner'},{'occ_code':'99-0003','occupation_title':'Fictional Creative Modeler'}]);run('career_pathway_optionality_summarizer.py','--alignment',align/'career_pathway_alignment.csv','--occupation-labels',d/'labels.csv','--threshold','0.8','--out-dir',opt);o=read_csv(opt/'career_optionality_summary.csv')[0];self.assertEqual(o['career_pathway_count'],'3');self.assertEqual(o['career_optionality_status'],'observed')
if __name__=='__main__':unittest.main()
