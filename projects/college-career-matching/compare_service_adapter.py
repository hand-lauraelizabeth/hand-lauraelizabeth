#!/usr/bin/env python3
"""Side-by-side comparison response. Preserves evidence states; does not invent winners."""
from __future__ import annotations
from candidate_detail_service import candidate_detail

def compare(candidates,current_labor=None,projections=None,work_market=None,data_version=None):
    if not 2 <= len(candidates) <= 5: raise ValueError("compare requires 2 to 5 candidates")
    ids=[str(c.get("candidate_id","")).strip() for c in candidates]
    if not all(ids) or len(ids)!=len(set(ids)): raise ValueError("compare candidates require unique candidate_id")
    details=[candidate_detail(c,current_labor,projections,work_market,data_version) for c in candidates]
    return {"schema_version":"1.0","data_version":data_version,"candidate_ids":ids,"candidates":details,
      "comparison_dimensions":[
        {"id":"affordability","label":"Affordability","fields":["net_price","tuition_in_state","tuition_out_of_state","cost_of_attendance","institution_median_debt"]},
        {"id":"aid_context","label":"Aid context","fields":["institutional_grant_share","work_study_share","state_local_grant_share"]},
        {"id":"program_outcomes","label":"Program / field outcomes","fields":["median_earnings","median_debt","completion_rate"]},
        {"id":"transfer","label":"Transfer evidence","fields":["evidence_record_count","evidence_levels","source_systems"]},
        {"id":"career","label":"Career pathways","fields":["pathway_count","pathways","representative_pathways"]},
        {"id":"current_labor","label":"Current selected-market evidence","fields":["employment","median_wage","evidence_state"]},
        {"id":"long_term_outlook","label":"Long-term outlook","fields":["employment_change_pct","annual_openings","projection_year","evidence_state"]},
        {"id":"accreditation","label":"Accreditation evidence","fields":["covered","statuses","agency_names"]},
        {"id":"freshness","label":"Source freshness / provenance","fields":["source_freshness","data_version"]},
        {"id":"unknowns","label":"Unresolved evidence","fields":["unknowns"]}
      ],
      "semantic_rules":{"no_automatic_winner":True,"missing_is_not_zero":True,"current_market_is_not_long_term_outlook":True,"institution_outcomes_are_not_program_outcomes":True,"aid_reporting_is_not_individual_award":True,"accreditation_absence_is_unknown_not_unaccredited":True}}
