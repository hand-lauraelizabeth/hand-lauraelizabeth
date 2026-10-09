import csv
import tempfile
import unittest
import zipfile
from pathlib import Path
from ny_pilot_independent_source_audit import (read_hd2025,reconcile_locale,reconcile_cohort,read_reviewed_cohort_map,build_report,OFFICIAL_DIRECTORY_URL,attestation_valid,sha256)

class IndependentSourceAuditTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
  self.pilot={'institutions':[{'UNITID':str(100000+i),'School':f'School {i}','Scorecard_locale_candidate':'11'} for i in range(20)],
              'cohort_field_audit':[{'UNITID':str(100000+i),'INSTNM':f'School {i}','candidate_scorecard_field_public':f'NPT4{j}_PUB','observed_value':'1200','source_field_value_match':'MATCH'} for i in range(20) for j in range(1,6)]}
  self.hd=self.base/'HD2025.zip'
  csvtxt='UNITID,INSTNM,CITY,STABBR,LOCALE,ZIP\n'+''.join(f'{100000+i},School {i},City,NY,11,10001\n' for i in range(20))
  with zipfile.ZipFile(self.hd,'w') as z:z.writestr('HD2025.csv',csvtxt)
 def test_archive_parses(self):self.assertEqual(len(read_hd2025(self.hd)),20)
 def test_unavailable_fails_closed(self):self.assertEqual(build_report(self.pilot)['counts']['unresolved_locale'],20)
 def test_sources_are_not_guessed(self):
  o=reconcile_locale(self.pilot,read_hd2025(self.hd),source_url=None,sha='abc')
  self.assertEqual(o[0]['locale_review_state'],'VALUE_MATCH_SOURCE_PROVENANCE_NOT_ESTABLISHED')
 def test_attested_source_flag(self):
  evidence=self.base/'hd_attestation.json'
  digest=sha256(self.hd)
  import json
  evidence.write_text(json.dumps({'review_authorized':True,'source_url':OFFICIAL_DIRECTORY_URL,'file_sha256':digest,'retrieval_method':'direct_official_download','reviewer':'source reviewer','review_date':'2026-10-09'}))
  self.assertTrue(attestation_valid(evidence,OFFICIAL_DIRECTORY_URL,digest))
  o=reconcile_locale(self.pilot,read_hd2025(self.hd),source_url=OFFICIAL_DIRECTORY_URL,sha=digest,source_attested=True)
  self.assertTrue(o[0]['locale_field_verified']);self.assertFalse(o[0]['current_site_address_confirmed_by_hd2025'])
 def test_unattested_source_blocked(self):
  o=reconcile_locale(self.pilot,read_hd2025(self.hd),source_url=OFFICIAL_DIRECTORY_URL,sha=sha256(self.hd))
  self.assertFalse(o[0]['locale_field_verified'])
 def test_mismatch_blocks(self):
  rows=read_hd2025(self.hd);rows['100000']['LOCALE']='21'
  self.assertEqual(reconcile_locale(self.pilot,rows,source_url=OFFICIAL_DIRECTORY_URL,sha='hash')[0]['locale_review_state'],'SCORECARD_NCES_LOCALE_CONFLICT')
 def test_reject_scorecard_disguised_as_hd(self):
  f=self.base/'Scorecard.csv';f.write_text('UNITID,LOCALE\n100000,11')
  with self.assertRaises(ValueError):read_hd2025(f)
 def test_missing_cohort_mapping(self):
  rows=reconcile_cohort(self.pilot,{})
  self.assertEqual(len(rows),100);self.assertEqual(sum(x['cohort_year_independently_verified'] for x in rows),0)
 def test_dictionary_without_review_rejected(self):
  p=self.base/'map.csv'
  p.write_text('scorecard_field,dictionary_source_url,official_cohort_year,dictionary_sheet,dictionary_cell,dictionary_sha256,release_date,human_source_review\nNPT41_PUB,https://collegescorecard.ed.gov/files/CollegeScorecardDataDictionary.xlsx,2023-24,Cohort Map,B17,'+ 'a'*64 +',2026-06-10,PENDING\n')
  self.assertEqual(read_reviewed_cohort_map(p)['NPT41_PUB']['cohort_review_state'],'INVALID_OR_UNATTESTED_COHORT_MAPPING')
  with self.assertRaises(ValueError):build_report(self.pilot,cohort_map=p)
 def test_reject_duplicate_ids(self):
  self.pilot['institutions'][1]['UNITID']='100000'
  with self.assertRaises(ValueError):build_report(self.pilot)
if __name__=='__main__':unittest.main()