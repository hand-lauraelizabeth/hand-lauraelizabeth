"""Synthetic-only checks for September NYC 311 API aggregate audit."""
import copy
import unittest
from audit_september_api import audit

S=[{"n":"323628","distinct_keys":"323628","nonnull_keys":"323628"}]
B=[{"borough":b,"n":str(n),"distinct_keys":str(n)} for b,n in [
("BRONX",59212),("BROOKLYN",105705),("MANHATTAN",64994),
("QUEENS",80443),("STATEN ISLAND",12876),("Unspecified",398)]]
M=[{"month":"2026-09-01T00:00:00.000","n":"323628"}]

class TestSourceAudit(unittest.TestCase):
 def test_valid_aggregate_stays_private(self):
  r=audit(S,B,M,expected_count=323628)
  self.assertEqual(r["total_rows"],323628)
  self.assertFalse(r["full_csv_reconciled"])
  self.assertFalse(r["publication_authorized"])
 def test_key_mismatch(self):
  s=copy.deepcopy(S);s[0]["distinct_keys"]="323627"
  with self.assertRaises(ValueError):audit(s,B,M)
 def test_source_drift(self):
  with self.assertRaises(ValueError):audit(S,B,M,expected_count=323627)
 def test_borough_mismatch(self):
  b=copy.deepcopy(B);b[0]["n"]="59213";b[0]["distinct_keys"]="59213"
  with self.assertRaises(ValueError):audit(S,b,M)
 def test_wrong_month(self):
  m=copy.deepcopy(M);m[0]["month"]="2026-10-01T00:00:00.000"
  with self.assertRaises(ValueError):audit(S,B,m)
if __name__=="__main__":unittest.main()
