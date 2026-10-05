#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
HTML=(P/"public-explorer.html").read_text(encoding="utf-8")
class PublicExplorerContractTests(unittest.TestCase):
 def test_zero_friction_entry(self):
  self.assertIn("Start with the things that matter to you",HTML)
  self.assertNotIn('type="submit"',HTML)
  for phrase in ["Run analysis","Run matcher","Continue","Find matches"]:
   self.assertNotIn(phrase,HTML)
 def test_initial_page_is_useful_without_script(self):
  self.assertIn("<noscript>",HTML)
  self.assertIn("Unranked",HTML)
  self.assertIn("Data & Information Systems",HTML)
  self.assertIn("Information Technology",HTML)
 def test_demo_is_explicitly_non_authoritative(self):
  self.assertIn("Demonstration data:",HTML)
  self.assertIn("fictional",HTML)
  self.assertIn("should not be used as college advice",HTML)
 def test_controls_update_in_place_and_support_comparison(self):
  for control in ["ccx-interest","ccx-state","ccx-setting","ccx-credential","ccx-income","ccx-price","ccx-housing","ccx-online","ccx-inst-aid","ccx-workstudy","ccx-state-aid","ccx-afford","ccx-career","ccx-transfer","ccx-small","ccx-transit","ccx-walk","ccx-housing-choice","ccx-disability-info"]:
   self.assertIn(f'id="{control}"',HTML)
  self.assertIn("ccx-compare-toggle",HTML)
  self.assertIn("renderCompare()",HTML)
  self.assertIn('aria-live="polite"',HTML)
 def test_cost_language_separates_coa_net_price_and_income_context(self):
  self.assertIn("cost of attendance",HTML.lower())
  self.assertIn("average net price after grants/scholarships",HTML.lower())
  self.assertIn("Household income range",HTML)
  self.assertIn("not a personalized aid estimate",HTML)
  self.assertIn("does not invent a family-size adjustment",HTML)
 def test_housing_setting_aid_and_accessibility_are_distinct(self):
  for phrase in ["Campus setting","Housing preference","Institutional grants/scholarships","Federal Work-Study","State/local grant-aid","Better public-transit access","More walkable access to daily needs","Documented disability-services information"]:
   self.assertIn(phrase,HTML)
  self.assertIn("Roommate versus private-room options require school-specific evidence",HTML)
  self.assertIn("separate signals",HTML)
 def test_no_undeclared_default_fit_score(self):
  self.assertIn("value:null",HTML)
  self.assertIn("'Unranked'",HTML)
  self.assertNotIn("50 fit",HTML)
if __name__=="__main__":unittest.main()
