import unittest
from ny_pilot_admissions_governance import validate_score,compare_reported_means,calibration_audit
class AdmissionGates(unittest.TestCase):
 def test_100_point_stays_100(self):self.assertEqual(validate_score(92.9,'hs_percent_100'),92.9)
 def test_transfer_gpa(self):self.assertEqual(validate_score(3.3,'college_gpa_4'),3.3)
 def test_explicit_scale(self):
  with self.assertRaises(ValueError):validate_score(3.8,'unknown')
 def test_out_of_bounds(self):
  with self.assertRaises(ValueError):validate_score(99,'college_gpa_4')
 def test_no_false_gpa_conversion(self):self.assertEqual(compare_reported_means(3.6,'college_gpa_4',92.9,'hs_percent_100','CUNY')['state'],'incomparable_grading_scales')
 def test_same_scale_is_descriptive(self):
  r=compare_reported_means(94.0,'hs_percent_100',92.9,'hs_percent_100','CUNY 2026');self.assertEqual(r['difference_in_original_scale'],1.1);self.assertIsNone(r['admission_probability'])
 def test_missing(self):self.assertEqual(compare_reported_means(None,'college_gpa_4',3.1,'college_gpa_4','CUNY')['state'],'insufficient_evidence')
 def test_no_authorization(self):self.assertEqual(calibration_audit([{'predicted_probability':.5,'admitted_offer':1}])['status'],'BLOCKED_NO_AUTHORIZED_LABELLED_VALIDATION_DATA')
 def test_small_cohort(self):self.assertEqual(calibration_audit([{'predicted_probability':.5,'admitted_offer':1}],validation_data_authorized=True)['status'],'INSUFFICIENT_VALIDATION_SAMPLE')
 def test_metrics_without_publication(self):
  data=[{'predicted_probability':(.25 if i%2==0 else .75),'admitted_offer':i%2,'independent_holdout_cohort':'synthetic_test'} for i in range(240)]
  r=calibration_audit(data,validation_data_authorized=True);self.assertEqual(r['status'],'DIAGNOSTIC_ONLY_NOT_CALIBRATION_APPROVAL');self.assertFalse(r['admission_probability_publication_allowed']);self.assertAlmostEqual(r['brier_score'],.0625)
 def test_missing_cohort_rejected(self):
  data=[{'predicted_probability':.5,'admitted_offer':0} for _ in range(220)]
  with self.assertRaises(ValueError):calibration_audit(data,validation_data_authorized=True)
if __name__=='__main__':unittest.main()