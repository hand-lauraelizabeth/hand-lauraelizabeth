import copy,json,sys,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parent
if not (BASE/'ny-pilot-20-public-reference.json').exists():BASE=BASE.parent
sys.path.insert(0,str(BASE))
from ny_pilot_public_reference_release_gate import validate_directory
DATA=json.loads((BASE/'ny-pilot-20-public-reference.json').read_text())
class DirectoryGate(unittest.TestCase):
 def test_verified_fixture(self):self.assertTrue(validate_directory(DATA)['pass'])
 def test_no_extra_record(self):
  d=copy.deepcopy(DATA);d['institutions'].append(copy.deepcopy(d['institutions'][0]));self.assertFalse(validate_directory(d)['pass'])
 def test_no_duplicate(self):
  d=copy.deepcopy(DATA);d['institutions'][0]['unitid']=d['institutions'][1]['unitid'];self.assertFalse(validate_directory(d)['pass'])
 def test_no_rank(self):
  d=copy.deepcopy(DATA);d['institutions'][0]['recommendation_score']=0.98;self.assertFalse(validate_directory(d)['pass'])
 def test_no_admission_probability(self):
  d=copy.deepcopy(DATA);d['institutions'][0]['admission_probability']=0.5;self.assertFalse(validate_directory(d)['pass'])
 def test_no_housing_certification(self):
  d=copy.deepcopy(DATA);d['institutions'][0]['current_student_accessible_housing_verified']=True;self.assertFalse(validate_directory(d)['pass'])
 def test_no_unreviewed_majors_claim(self):
  d=copy.deepcopy(DATA);d['institutions'][0]['program_exhaustive_verified']=True;self.assertFalse(validate_directory(d)['pass'])
 def test_no_private_url(self):
  d=copy.deepcopy(DATA);d['institutions'][0]['program_directory_url']='https://drive.google.com/folder/private';self.assertFalse(validate_directory(d)['pass'])
 def test_no_activated_service(self):
  d=copy.deepcopy(DATA);d['matcher_activation_authorized']=True;self.assertFalse(validate_directory(d)['pass'])
 def test_no_id_count_drift(self):
  d=copy.deepcopy(DATA);d['institutions'][0]['system']='SUNY-affiliated';self.assertFalse(validate_directory(d)['pass'])
if __name__=='__main__':unittest.main()