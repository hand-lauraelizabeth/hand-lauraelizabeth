"""Dataset-only regression tests; these do not authorize admissions prediction or rankings."""
import hashlib, json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/'shards' if (ROOT/'shards'/'manifest.v1.json').exists() else ROOT.parent/'data'/'national'
M=json.loads((P/'manifest.v1.json').read_text())
class NationalSnapshotTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows=[]
  for i,part in enumerate(M['shards']):
   p=P/part['file'];raw=p.read_bytes()
   assert hashlib.sha256(raw).hexdigest()==part['sha256'],part['file']
   d=json.loads(raw);assert d['part']==i and d['schema_version']=='1.0'
   assert len(d['records'])==part['count']
   cls.rows.extend(d['records'])
  cls.fields={key:i for i,key in enumerate(M['row_layout'])}
 def item(self,uid):
  return next(x for x in self.rows if x[0]==uid)
 def test_source_is_not_public_rank_model(self):
  self.assertIs(M['scoring_authorized'],False);self.assertIs(M['admission_predictions_authorized'],False);self.assertIs(M['program_ranking_authorized'],False)
 def test_snapshot_covers_national_operating_rows(self):
  self.assertEqual(M['expected_records'],6243);self.assertEqual(len(self.rows),6243)
 def test_unique_six_or_eight_digit_unitids(self):
  import re
  ids=[r[0] for r in self.rows]
  self.assertEqual(len(set(ids)),len(ids));self.assertTrue(all(re.fullmatch(r'\d{6}(?:\d{2})?',x) for x in ids));self.assertTrue(any(len(x)==8 for x in ids))
 def test_states_and_territories(self):
  self.assertEqual(len({r[self.fields['state']] for r in self.rows}),59)
 def test_mapped_ny_pilot(self):
  pilots=[pathlib.Path('/mnt/data/NY20_Live_Integration_2026-10-09/ny20-institution-evidence.v1.json'),ROOT.parent/'data'/'ny20-institution-evidence.v1.json']
  pilot=next((x for x in pilots if x.exists()),None)
  self.assertIsNotNone(pilot)
  old=json.loads(pilot.read_text())
  for r in old['institutions']:
   new=self.item(r['unitid']);self.assertEqual(new[self.fields['name']],r['name']);self.assertEqual(new[self.fields['size']],r['size']['value']);self.assertEqual(new[self.fields['net_price']],r['net_price']['value'])
 def test_income_five_bands_and_missing(self):
  for r in self.rows:
   a=r[self.fields['income_net_prices']];self.assertEqual(len(a),5)
   self.assertTrue(all(x is None or isinstance(x,(int,float)) for x in a))
 def test_historical_field_mix_not_program_catalog(self):
  self.assertIn('subject_mix',M['row_layout']);self.assertFalse(M['program_ranking_authorized'])
  i=self.fields['subject_mix'];self.assertTrue(all(r[i] is None or isinstance(r[i],list) for r in self.rows))
 def test_no_unverified_accreditation_label(self):
  self.assertIs(M['accreditation_independently_verified'],False)
 def test_preserved_unknown_cohort_and_locale(self):
  self.assertIs(M['price_cohort_year_verified'],False);self.assertIs(M['independent_locale_verified'],False)
 def test_url_scheme_safe(self):
  for r in self.rows:
   for key in ['institution_url','net_price_calculator_url']:
    x=r[self.fields[key]]
    self.assertTrue(x is None or x.startswith('https://'))
if __name__=='__main__':unittest.main()