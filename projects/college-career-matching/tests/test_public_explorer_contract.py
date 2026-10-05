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
  self.assertIn("<noscript>",HTML);self.assertIn("Unranked",HTML);self.assertIn("Data & Information Systems",HTML);self.assertIn("Information Technology",HTML)
 def test_fixture_mode_is_explicitly_non_authoritative(self):
  self.assertIn("Synthetic fixture mode:",HTML);self.assertIn("fictional",HTML);self.assertIn("static fixture records do not change with that request",HTML);self.assertIn("should not be used as college advice",HTML)
 def test_only_governed_active_controls_remain(self):
  for control in ["ccx-cip","ccx-state","ccx-setting","ccx-credential","ccx-income","ccx-price","ccx-housing","ccx-online","ccx-inst-aid","ccx-workstudy","ccx-state-aid","ccx-afford","ccx-career","ccx-transfer","ccx-small","ccx-transit","ccx-walk","ccx-housing-choice","ccx-disability-info"]:
   self.assertIn(f'id="{control}"',HTML)
  self.assertNotIn('id="ccx-interest"',HTML);self.assertIn("Field choices come from authoritative CIP classifications",HTML)
 def test_cost_language_separates_coa_net_price_and_income_context(self):
  self.assertIn("cost of attendance",HTML.lower());self.assertIn("average net price after grants/scholarships",HTML.lower());self.assertIn("Household income range",HTML);self.assertIn("not a personalized aid estimate",HTML);self.assertIn("does not invent a family-size adjustment",HTML)
 def test_housing_setting_aid_and_accessibility_are_distinct(self):
  for phrase in ["Campus setting","Housing preference","Institutional grants/scholarships","Federal Work-Study","State/local grant-aid","Better public-transit access","More walkable access to daily needs","Documented disability-services information"]:
   self.assertIn(phrase,HTML)
  self.assertIn("Roommate versus private-room options require school-specific evidence",HTML);self.assertIn("separate signals",HTML)
 def test_browser_builds_governed_request_fields(self):
  self.assertIn("function buildGovernedRequest(s)",HTML)
  for token in ["cip_code","finance__net_price_overall","finance__net_price_income_48_75","campus__housing_available","campus__housing_required_all_ftft","finance__institutional_grant_evidence","campus__locale_category","transit_access_fit","walkability_fit","housing_context_fit","accessibility_evidence_fit"]:
   self.assertIn(token,HTML)
  self.assertIn("root.getGovernedRequest",HTML)
 def test_filter_choices_are_loaded_from_versioned_options_service(self):
  self.assertIn("client.options()",HTML);self.assertIn("applyServiceOptions(optionResponse)",HTML);self.assertIn("optionResponse.data_version!==metadata.data_version",HTML)
  for token in ["o.cip_fields","o.states","o.campus_settings","o.credential_levels","o.affordability&&o.affordability.income_bands"]:self.assertIn(token,HTML)
 def test_explorer_consumes_service_response_instead_of_local_scoring(self):
  self.assertIn("MatchingServiceClient",HTML);self.assertIn("assertContract",HTML);self.assertIn("client.match(request)",HTML);self.assertIn("renderResponse(response)",HTML)
  self.assertNotIn("var data=[",HTML);self.assertNotIn("function score(",HTML)
  self.assertIn("no browser-side filtering or ranking is performed",HTML)
 def test_ranking_is_rendered_only_from_service_recommendation_metadata(self):
  self.assertIn("review_eligible_ranked",HTML);self.assertIn("rec.baseline_score",HTML);self.assertIn("rec.production_authorized",HTML)
  self.assertIn("browser does not calculate a fit score or rank",HTML)
 def test_runtime_defaults_to_fixture_and_requires_activation_aware_validation(self):
  self.assertIn('id="ccx-runtime-config"',HTML);self.assertIn('"mode":"fixture"',HTML);self.assertIn('"production_authorized":false',HTML)
  for token in ["validateRuntimeConfig","assertRuntimeMetadata","productionAuthorized:runtimeConfig.production_authorized","Authorized production matching service"]:self.assertIn(token,HTML)
 def test_staging_mode_is_visibly_nonproduction(self):
  self.assertIn("Synthetic staging HTTP service",HTML);self.assertIn("Synthetic staging mode:",HTML);self.assertIn("explicitly non-production",HTML)
 def test_compare_is_display_only_not_browser_winner_logic(self):
  self.assertIn("renderCompare()",HTML);self.assertIn("no winner is calculated in the browser",HTML);self.assertIn("ccx-compare-toggle",HTML)
  self.assertNotIn("winner",HTML.lower().replace("no winner",""))
 def test_service_versions_are_cross_checked(self):
  self.assertIn("response.data_version!==metadata.data_version",HTML);self.assertIn("response.model_version!==metadata.model_version",HTML)

if __name__=="__main__":unittest.main()
