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
  for control in ["interest","state","credential","price","afford","career","transfer","small","online"]:
   self.assertIn(f'id="{control}"',HTML)
  self.assertIn("compare-toggle",HTML)
  self.assertIn("renderCompare()",HTML)
  self.assertIn('aria-live="polite"',HTML)
 def test_no_undeclared_default_fit_score(self):
  self.assertIn("value:null",HTML)
  self.assertIn("'Unranked'",HTML)
  self.assertNotIn("50 fit",HTML)
if __name__=="__main__":unittest.main()
