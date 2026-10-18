"""Chromium behavioral tests for private NYC 311 aggregate preview. Synthetic only."""
import copy
import json
import os
import shutil
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).with_name('private-review.html').read_text(encoding='utf-8')
SAFE = {'dataset_id': 'erm2-nwe9', 'publication_authorized': False,
        'source_sha256': 'a'*64, 'source': 'https://data.cityofnewyork.us/d/erm2-nwe9', 'snapshot_as_of':'2026-10-18', 'rules': {'display_minimum_cell_count': 10},
        'aggregates': [{'month':'2026-09','borough':'QUEENS','agency':'DOT','problem':'Pothole',
                        'requests':25,'closed_with_valid_interval':12,'closure_count_suppressed':False},
                       {'month':'2026-09','borough':'BRONX','agency':'DOT','problem':'Noise',
                        'requests':25,'closed_with_valid_interval':None,'closure_count_suppressed':True}]}

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        browser_path = os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('chromium-browser')
        launch_options = {'headless': True, 'args': ['--no-sandbox']}
        if browser_path:
            launch_options['executable_path'] = browser_path
        cls.browser = cls.playwright.chromium.launch(**launch_options)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()
    def setUp(self):
        self.page = self.browser.new_page(viewport={'width':390,'height':800})
        self.page.set_content(HTML)
    def tearDown(self):
        self.page.close()
    def load(self, data):
        self.page.locator('#file').set_input_files({'name':'fixture.json','mimeType':'application/json','buffer':json.dumps(data).encode()})
        self.page.wait_for_timeout(30)
        return self.page.locator('#status').inner_text()
    def test_default_state_is_empty(self):
        self.assertEqual(self.page.locator('tbody tr').count(),0)
        self.assertTrue(self.page.locator('#borough').is_disabled())
    def test_safe_load_and_borough_filter(self):
        self.assertIn('2 locally screened', self.load(SAFE))
        self.assertEqual(self.page.locator('tbody tr').count(),2)
        self.page.locator('#borough').select_option('QUEENS')
        self.assertEqual(self.page.locator('tbody tr').count(),1)
        self.assertIn('Pothole',self.page.locator('tbody').inner_text())
    def test_suppressed_is_not_zero(self):
        self.load(SAFE)
        self.assertIn('Withheld',self.page.locator('tbody').inner_text())
        self.assertNotIn('None',self.page.locator('tbody').inner_text())
    def test_small_group_rejected(self):
        d=copy.deepcopy(SAFE);d['aggregates'][0]['requests']=9
        self.assertIn('File rejected',self.load(d));self.assertEqual(self.page.locator('tbody tr').count(),0)
    def test_complementary_small_group_rejected(self):
        d=copy.deepcopy(SAFE);d['aggregates'][0]['closed_with_valid_interval']=24
        self.assertIn('File rejected',self.load(d))
    def test_unsafe_zero_closed_rejected(self):
        d=copy.deepcopy(SAFE);d['aggregates'][0]['closed_with_valid_interval']=0
        self.assertIn('File rejected',self.load(d))
    def test_suppression_flag_mismatch_rejected(self):
        d=copy.deepcopy(SAFE);d['aggregates'][1]['closure_count_suppressed']=False
        self.assertIn('File rejected',self.load(d))
    def test_bad_month_rejected(self):
        d=copy.deepcopy(SAFE);d['aggregates'][0]['month']='2026-10'
        self.assertIn('File rejected',self.load(d))
    def test_missing_source_hash_rejected(self):
        d=copy.deepcopy(SAFE);d['source_sha256']='not-verified'
        self.assertIn('File rejected',self.load(d))
    def test_malicious_markup_renders_as_text(self):
        d=copy.deepcopy(SAFE);d['aggregates'][0]['problem']='<img src=x onerror=alert(1)>'
        self.load(d)
        self.assertEqual(self.page.locator('tbody img').count(),0)
        self.assertIn('<img src=x',self.page.locator('tbody').inner_text())
    def test_rejected_file_clears_previous_rows(self):
        self.load(SAFE);self.assertEqual(self.page.locator('tbody tr').count(),2)
        d=copy.deepcopy(SAFE);d['aggregates'][0]['requests']=9
        self.load(d)
        self.assertEqual(self.page.locator('tbody tr').count(),0)
        self.assertTrue(self.page.locator('#borough').is_disabled())
    def test_duplicate_aggregate_rejected(self):
        d=copy.deepcopy(SAFE);d['aggregates'].append(copy.deepcopy(d['aggregates'][0]))
        self.assertIn('File rejected',self.load(d))
    def test_source_url_mismatch_rejected(self):
        d=copy.deepcopy(SAFE);d['source']='https://example.org/not-nyc'
        self.assertIn('File rejected',self.load(d))
    def test_test_only_threshold_rejected(self):
        d=copy.deepcopy(SAFE);d['rules']['test_only_threshold']=True
        self.assertIn('File rejected',self.load(d))
    def test_string_threshold_rejected(self):
        d=copy.deepcopy(SAFE);d['rules']['display_minimum_cell_count']='10'
        self.assertIn('File rejected',self.load(d))
    def test_keyboard_and_small_viewport(self):
        self.load(SAFE)
        self.page.locator('#borough').focus()
        self.assertTrue(self.page.locator('#borough').evaluate('(el)=>document.activeElement===el'))
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)

if __name__ == '__main__': unittest.main(verbosity=2)
