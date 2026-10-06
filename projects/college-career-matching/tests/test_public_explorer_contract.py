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
  for control in ["ccx-decision-mode","ccx-cip","ccx-state","ccx-setting","ccx-credential","ccx-income","ccx-price","ccx-housing","ccx-online","ccx-inst-aid","ccx-workstudy","ccx-state-aid","ccx-afford","ccx-career","ccx-transfer","ccx-small","ccx-transit","ccx-walk","ccx-housing-choice","ccx-disability-info"]:
   self.assertIn(f'id="{control}"',HTML)
  self.assertNotIn('id="ccx-interest"',HTML);self.assertIn("Field choices come from authoritative CIP classifications",HTML)
 def test_decision_orientation_is_sent_through_governed_request(self):
  self.assertIn("How are you exploring?",HTML)
  for mode in ["broad_exploration","career_first","college_program_first","transfer","returning_student","compare_known"]:
   self.assertIn(f'value="{mode}"',HTML)
  self.assertIn("decisionMode:q('ccx-decision-mode').value",HTML)
  self.assertIn("decision_mode:s.decisionMode||'broad_exploration'",HTML)
  self.assertNotIn("decision_mode:'broad_exploration',constraints",HTML)
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
  self.assertIn("MatchingServiceClient",HTML);self.assertIn("assertContract",HTML);self.assertIn("client.match(request,{signal})",HTML);self.assertIn("renderResponse(response)",HTML)
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
 def test_service_failures_clear_stale_results_and_identity_errors_disable_controls(self):
  for token in ["function setInteractive(enabled)","function clearServiceResults(","serviceStatus='request-error'","Previous results were cleared","serviceStatus='error'","Controls are disabled until a valid service identity is available."]:
   self.assertIn(token,HTML)
 def test_criteria_changes_clear_cross_page_comparisons_and_unknown_evidence_remains_visible(self):
  self.assertIn("selectedRecords=new Map()",HTML);self.assertIn("function criteriaChanged()",HTML);self.assertIn("selected.clear();selectedRecords.clear();renderCompare();scheduleRefresh()",HTML)
  self.assertIn("unresolved must-have evidence field",HTML)
 def test_pagination_is_service_driven_and_comparisons_can_span_pages(self):
  for token in ['id="ccx-page-size"','id="ccx-pagination"','id="ccx-prev"','id="ccx-next"',"page:currentPage,page_size:pageSize","function renderPagination(response)","async function goToPage(page)","const host=q('ccx-compare-table'),note=q('ccx-compare-note'),clear=q('ccx-clear'),ids=[...selected]","client.compare(ids,context,{signal})","Service pagination does not match the governed request","getPaginationState"]:
   self.assertIn(token,HTML)
  self.assertNotIn("results.slice(",HTML)
 def test_requests_are_last_writer_wins_and_retry_revalidates_service(self):
  for token in ['id="ccx-retry"',"requestGeneration=0","activeRequestController","generation!==requestGeneration","client.match(request,{signal})","async function retryService()","assertRuntimeMetadata(runtimeConfig,recoveredMetadata)","Rechecking governed service","getRequestGeneration"]:
   self.assertIn(token,HTML)
 def test_request_abort_is_not_the_only_stale_response_guard(self):
  self.assertIn("if(activeRequestController)activeRequestController.abort()",HTML)
  self.assertIn("if(generation!==requestGeneration)return",HTML)
  self.assertIn("generation!==requestGeneration||err&&err.name==='AbortError'",HTML)
 def test_candidate_details_are_on_demand_version_checked_and_cached(self):
  for token in ["candidateDetailCache=new Map()","client.candidate(id)","assertContract(await promise,'candidate')","Candidate detail identity mismatch","Candidate detail data version does not match loaded metadata","data-detail-key","getCandidateDetailState"]:
   self.assertIn(token,HTML)
 def test_candidate_drilldown_keeps_evidence_families_separate(self):
  for phrase in ["Cost & debt evidence","Aid context","Program / field outcomes","Transfer & pathway evidence","Labor-market evidence","Source status & provenance","Net price is not the same as tuition","Current-market evidence and long-term projections are separate","Absence of accreditation evidence is unknown coverage"]:
   self.assertIn(phrase,HTML)
 def test_program_compare_uses_governed_compare_service_not_match_card_fields(self):
  for token in ["async function renderCompare()","client.compare(ids,context,{signal})","assertContract(await client.compare","Compare response candidate identity/order mismatch","renderCompareResponse(response)","compareCache=new Map()","getCompareState"]:
   self.assertIn(token,HTML)
  self.assertNotIn("Side-by-side display of fields already returned by the match service",HTML)
 def test_governed_compare_renders_evidence_families_without_winner_logic(self):
  for phrase in ["Cost & debt evidence","Aid context","Program / field outcomes","Transfer & career evidence","Labor-market evidence","Source status & unresolved evidence","no winner is calculated in the browser"]:
   self.assertIn(phrase,HTML)
 def test_service_versions_are_cross_checked(self):
  self.assertIn("response.data_version!==metadata.data_version",HTML);self.assertIn("response.model_version!==metadata.model_version",HTML)

if __name__=="__main__":unittest.main()
