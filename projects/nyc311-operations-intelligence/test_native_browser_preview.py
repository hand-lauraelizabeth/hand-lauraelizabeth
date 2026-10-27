"""Native Chromium regression for the exact committed, offline NYC 311 synthetic preview.

Run from the repository with: python -m unittest -v
projects/nyc311-operations-intelligence/test_native_browser_preview.py

Requires Selenium and locally installed Chrome/Chromedriver. All values are
fabricated; this does not authenticate official 311 data or clear disclosure.
"""
from pathlib import Path
import unittest

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import Select, WebDriverWait
except ImportError:  # Standard offline unit suite need not install a browser.
    webdriver = None

PREVIEW = Path(__file__).with_name("synthetic_coarse_preview.html").resolve().as_uri()


@unittest.skipUnless(webdriver is not None, 'Selenium unavailable; native browser workflow installs it')
class NativePreviewRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = Options()
        for flag in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                     "--disable-gpu", "--allow-file-access-from-files"):
            options.add_argument(flag)
        cls.browser = webdriver.Chrome(options=options)
        cls.browser.set_page_load_timeout(30)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()

    def setUp(self):
        self.browser.get(PREVIEW)
        WebDriverWait(self.browser, 15).until(
            lambda b: len(b.find_elements(By.CSS_SELECTOR, "#results tr")) == 20
        )

    def test_01_native_mobile_and_desktop_layout(self):
        for width in (320, 375, 768, 1440):
            with self.subTest(width=width):
                self.browser.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": width, "height": 900, "deviceScaleFactor": 1, "mobile": False
                })
                self.browser.get(PREVIEW)
                self.assertEqual(
                    len(self.browser.find_elements(By.CSS_SELECTOR, "#results tr")), 20
                )
                sizes = self.browser.execute_script(
                    "return [innerWidth, document.documentElement.scrollWidth, "
                    "document.querySelector('.scroll').scrollWidth, "
                    "document.querySelector('.scroll').clientWidth]"
                )
                self.assertEqual(sizes[0], width)
                self.assertLessEqual(sizes[1], width + 1,
                                     "Document must not overflow horizontally")
                if width <= 375:
                    self.assertGreater(sizes[2], sizes[3],
                                       "Wide table must scroll inside labeled region")
        self.browser.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})

    def test_02_semantics_and_filter_sort_reset(self):
        self.assertEqual(len(self.browser.find_elements(
            By.CSS_SELECTOR, "#results tr th[scope='row']")), 20)
        self.assertEqual(len(self.browser.find_elements(
            By.CSS_SELECTOR, "thead th[scope='col']")), 3)
        self.assertEqual(len(self.browser.find_elements(
            By.CSS_SELECTOR, "table caption")), 1)
        self.assertEqual(self.browser.find_element(
            By.CSS_SELECTOR, "#summary").get_attribute("role"), "status")
        Select(self.browser.find_element(By.ID, "borough")).select_by_visible_text("Queens")
        Select(self.browser.find_element(By.ID, "group")).select_by_visible_text("Group C")
        rows = self.browser.find_elements(By.CSS_SELECTOR, "#results tr")
        self.assertEqual(len(rows), 1)
        self.assertEqual([c.text for c in rows[0].find_elements(By.CSS_SELECTOR, "th,td")],
                         ["Queens", "Group C", "850"])
        self.assertIn("Queens / Group C", self.browser.find_element(By.ID, "summary").text)
        Select(self.browser.find_element(By.ID, "borough")).select_by_index(0)
        Select(self.browser.find_element(By.ID, "group")).select_by_index(0)
        Select(self.browser.find_element(By.ID, "sort")).select_by_value("high")
        self.assertEqual(self.browser.find_elements(
            By.CSS_SELECTOR, "#results tr td:last-child")[0].text, "1,100")
        Select(self.browser.find_element(By.ID, "sort")).select_by_value("low")
        self.assertEqual(self.browser.find_elements(
            By.CSS_SELECTOR, "#results tr td:last-child")[0].text, "550")
        self.browser.find_element(By.ID, "reset").click()
        self.assertEqual(len(self.browser.find_elements(By.CSS_SELECTOR, "#results tr")), 20)
        self.assertEqual(self.browser.execute_script("return document.activeElement.id"),
                         "borough")

    def test_03_keyboard_disclosure_and_offline_contract(self):
        disclosure = self.browser.find_element(By.CSS_SELECTOR, "details summary")
        disclosure.send_keys(Keys.ENTER)
        self.assertTrue(self.browser.find_element(
            By.CSS_SELECTOR, "details").get_attribute("open") is not None)
        self.assertEqual(self.browser.execute_script(
            "return performance.getEntriesByType('resource').length"), 0)
        self.assertEqual(len(self.browser.find_elements(
            By.CSS_SELECTOR, "script[src],link[rel='stylesheet'],img")), 0)

    def test_04_corrupted_fixture_fails_closed(self):
        script = """const original=JSON.parse;
JSON.parse=function(...args){
 const data=original.apply(this,args);
 if(Array.isArray(data)&&data.length===20&&data[0].borough==='Bronx')
   data[0].requests+=1;
 return data;
};"""
        injection = self.browser.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": script}
        )["identifier"]
        try:
            self.browser.get(PREVIEW)
            self.assertEqual(len(self.browser.find_elements(
                By.CSS_SELECTOR, "#results tr")), 0)
            status = self.browser.find_element(By.ID, "summary")
            self.assertEqual(status.get_attribute("role"), "alert")
            self.assertIn("integrity checks", status.text)
            for control in ("borough", "group", "sort", "reset"):
                self.assertFalse(self.browser.find_element(By.ID, control).is_enabled())
        finally:
            self.browser.execute_cdp_cmd(
                "Page.removeScriptToEvaluateOnNewDocument", {"identifier": injection}
            )


if __name__ == "__main__":
    unittest.main()
