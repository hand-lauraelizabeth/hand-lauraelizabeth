#!/usr/bin/env python3
"""Integration tests that execute project scripts against tiny synthetic files."""
from __future__ import annotations
import csv, json, subprocess, sys, tempfile, unittest
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]

def write_csv(path,rows):
    cols=list(rows[0].keys())
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

def read_csv(path):
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def run(script,*args,expect=0):
    p=subprocess.run([sys.executable,str(PROJECT/script),*map(str,args)],text=True,capture_output=True)
    if p.returncode!=expect: raise AssertionError(f"{script} returned {p.returncode}, expected {expect}\nSTDOUT:{p.stdout}\nSTDERR:{p.stderr}")
    return p

class IntegrationTests(unittest.TestCase):
    def test_dimension_composer_blocks_partial_and_uses_explicit_priorities_only(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); out=d/"out"
            write_csv(d/"features.csv",[
                {"candidate_id":"FIC-1","feature_id":"aff_a","dimension":"affordability","normalized_value":"0.8","evidence_state":"observed"},
                {"candidate_id":"FIC-1","feature_id":"aff_b","dimension":"affordability","normalized_value":"","evidence_state":"unknown"},
                {"candidate_id":"FIC-1","feature_id":"career_a","dimension":"career_pathway_fit","normalized_value":"0.6","evidence_state":"observed"},
            ])
            write_csv(d/"policy.csv",[
                {"feature_id":"aff_a","within_dimension_weight":"1","partial_policy":"block"},
                {"feature_id":"aff_b","within_dimension_weight":"1","partial_policy":"block"},
                {"feature_id":"career_a","within_dimension_weight":"1","partial_policy":"block"},
            ])
            write_csv(d/"prefs.csv",[
                {"dimension":"affordability","importance":"3","priority_explicit":"true"},
                {"dimension":"career_pathway_fit","importance":"2","priority_explicit":"true"},
                {"dimension":"college_fit","importance":"99","priority_explicit":"false"},
            ])
            run("dimension_composer_weight_scenarios.py","--normalized-features",d/"features.csv","--composition-policy",d/"policy.csv","--preferences",d/"prefs.csv","--out-dir",out)
            dims=read_csv(out/"composed_candidate_dimensions.csv")
            aff=next(r for r in dims if r["dimension"]=="affordability")
            self.assertEqual(aff["dimension_status"],"partial_blocked"); self.assertEqual(aff["dimension_value"],"")
            weights=read_csv(out/"explicit_preference_weight_scenarios.csv")
            baseline=[r for r in weights if r["scenario_id"]=="baseline"]
            self.assertEqual({r["dimension"] for r in baseline},{"affordability","career_pathway_fit"})
            bw={r["dimension"]:float(r["weight"]) for r in baseline}; self.assertAlmostEqual(bw["affordability"],.6); self.assertAlmostEqual(bw["career_pathway_fit"],.4)

    def test_campus_context_normalization_feeds_explicit_weight_scenarios(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); norm=d/"norm"; composed=d/"composed"
            write_csv(d/"reference.csv",[
                {"UNITID":"1","campus__transit_stop_distance_m":"100","campus__transit_stop_distance_m__state":"observed","campus__walkability_index":"5","campus__walkability_index__state":"observed"},
                {"UNITID":"2","campus__transit_stop_distance_m":"300","campus__transit_stop_distance_m__state":"observed","campus__walkability_index":"10","campus__walkability_index__state":"observed"},
                {"UNITID":"3","campus__transit_stop_distance_m":"700","campus__transit_stop_distance_m__state":"observed","campus__walkability_index":"15","campus__walkability_index__state":"observed"},
                {"UNITID":"4","campus__transit_stop_distance_m":"1100","campus__transit_stop_distance_m__state":"observed","campus__walkability_index":"20","campus__walkability_index__state":"observed"},
            ])
            write_csv(d/"candidates.csv",[
                {"candidate_id":"A","campus__transit_stop_distance_m":"300","campus__transit_stop_distance_m__state":"observed","campus__walkability_index":"15","campus__walkability_index__state":"observed","campus__housing_choice_state":"choice_available","campus__disability_services_evidence_available":"true","campus__disability_services_registered_share__state":"observed"},
                {"candidate_id":"B","campus__transit_stop_distance_m":"700","campus__transit_stop_distance_m__state":"observed","campus__walkability_index":"10","campus__walkability_index__state":"observed","campus__housing_choice_state":"required_for_all_ftft","campus__disability_services_evidence_available":"","campus__disability_services_registered_share__state":"not_published"},
            ])
            run("campus_context_preference_normalizer.py","--candidates",d/"candidates.csv","--reference",d/"reference.csv","--reference-id","SYN-REF-1","--out-dir",norm)
            write_csv(d/"prefs.csv",[
                {"dimension":"transit_access_fit","importance":"4","priority_explicit":"true"},
                {"dimension":"accessibility_evidence_fit","importance":"2","priority_explicit":"true"},
                {"dimension":"walkability_fit","importance":"99","priority_explicit":"false"},
                {"dimension":"housing_context_fit","importance":"99","priority_explicit":"false"},
            ])
            run("dimension_composer_weight_scenarios.py","--normalized-features",norm/"campus_context_normalized_features.csv","--composition-policy",norm/"campus_context_composition_policy.csv","--preferences",d/"prefs.csv","--out-dir",composed)
            dims=read_csv(composed/"composed_candidate_dimensions.csv")
            b_access=next(r for r in dims if r["candidate_id"]=="B" and r["dimension"]=="accessibility_evidence_fit")
            self.assertEqual(b_access["dimension_status"],"partial_blocked");self.assertEqual(b_access["dimension_value"],"")
            baseline=[r for r in read_csv(composed/"explicit_preference_weight_scenarios.csv") if r["scenario_id"]=="baseline"]
            self.assertEqual({r["dimension"] for r in baseline},{"transit_access_fit","accessibility_evidence_fit"})
            weights={r["dimension"]:float(r["weight"]) for r in baseline};self.assertAlmostEqual(weights["transit_access_fit"],2/3);self.assertAlmostEqual(weights["accessibility_evidence_fit"],1/3)

    def test_baseline_ranking_sensitivity_and_release_gate_share_explicit_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); comp=d/"comp"; rank=d/"rank"; sens=d/"sens"; gate=d/"gate"; review=d/"review"
            write_csv(d/"normalized.csv",[
                {"candidate_id":"A","feature_id":"t","dimension":"transit_access_fit","normalized_value":"0.8","evidence_state":"observed"},
                {"candidate_id":"A","feature_id":"w","dimension":"walkability_fit","normalized_value":"0.4","evidence_state":"observed"},
                {"candidate_id":"B","feature_id":"t","dimension":"transit_access_fit","normalized_value":"0.5","evidence_state":"observed"},
                {"candidate_id":"B","feature_id":"w","dimension":"walkability_fit","normalized_value":"0.9","evidence_state":"observed"},
            ])
            write_csv(d/"policy.csv",[
                {"feature_id":"t","within_dimension_weight":"1","partial_policy":"block"},
                {"feature_id":"w","within_dimension_weight":"1","partial_policy":"block"},
            ])
            write_csv(d/"prefs.csv",[
                {"dimension":"transit_access_fit","importance":"3","priority_explicit":"true"},
                {"dimension":"walkability_fit","importance":"1","priority_explicit":"true"},
            ])
            run("dimension_composer_weight_scenarios.py","--normalized-features",d/"normalized.csv","--composition-policy",d/"policy.csv","--preferences",d/"prefs.csv","--out-dir",comp)
            run("recommendation_baseline_materializer.py","--dimensions",comp/"composed_candidate_dimensions.csv","--weights",comp/"explicit_preference_weight_scenarios.csv","--out-dir",rank)
            ranked=read_csv(rank/"recommendation_baseline_ranked.csv");self.assertEqual(ranked[0]["candidate_id"],"A");self.assertEqual(ranked[0]["ranking_status"],"ranked_pending_validation")
            run("recommendation_sensitivity_harness.py","--candidates",rank/"recommendation_sensitivity_candidate_dimensions.csv","--weights",comp/"explicit_preference_weight_scenarios.csv","--top-k","1","--out-dir",sens)
            sensitivity=read_csv(sens/"recommendation_sensitivity.csv");self.assertEqual({r["candidate_id"] for r in sensitivity},{"A","B"})
            # First prove a blocked gate cannot expose the ranking.
            write_csv(d/"blocked_gate.csv",[{"stage_id":"ranking","artifact_path":str(rank/"recommendation_baseline_summary.json"),"required":"true","check_path":"status","operator":"eq","expected":"DOES_NOT_MATCH"}])
            run("recommendation_release_gate.py","--gate-manifest",d/"blocked_gate.csv","--out-dir",gate/"blocked")
            run("recommendation_rank_review_gate.py","--ranked",rank/"recommendation_baseline_ranked.csv","--ranking-summary",rank/"recommendation_baseline_summary.json","--release-decision",gate/"blocked"/"recommendation_release_decision.json","--out-dir",review/"blocked")
            blocked=json.loads((review/"blocked"/"ranked_result_review_eligibility.json").read_text());self.assertEqual(blocked["review_eligible_ranked_count"],0)
            # Then require ranking + sensitivity artifacts without inventing an instability threshold.
            write_csv(d/"passing_gate.csv",[
                {"stage_id":"ranking","artifact_path":str(rank/"recommendation_baseline_summary.json"),"required":"true","check_path":"status","operator":"eq","expected":"RANKING_READY_FOR_VALIDATION"},
                {"stage_id":"sensitivity","artifact_path":str(sens/"recommendation_sensitivity_summary.json"),"required":"true","check_path":"scenario_count","operator":"exists","expected":""},
            ])
            run("recommendation_release_gate.py","--gate-manifest",d/"passing_gate.csv","--out-dir",gate/"passing")
            decision=json.loads((gate/"passing"/"recommendation_release_decision.json").read_text());self.assertEqual(decision["release_decision"],"ELIGIBLE_FOR_REVIEW")
            run("recommendation_rank_review_gate.py","--ranked",rank/"recommendation_baseline_ranked.csv","--ranking-summary",rank/"recommendation_baseline_summary.json","--release-decision",gate/"passing"/"recommendation_release_decision.json","--out-dir",review/"passing")
            eligible=read_csv(review/"passing"/"review_eligible_ranked_candidates.csv");self.assertEqual(len(eligible),2);self.assertTrue(all(r["review_eligibility"]=="eligible_for_review" for r in eligible))

    def test_review_gated_ranking_bundle_controls_service_pagination_only_for_bound_context(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            request={"schema_version":"1.0","decision_mode":"broad_exploration","constraints":[],"preferences":[{"preference_id":"cost","dimension":"affordability","importance":3,"priority_explicit":True}],"career_preferences":[],"geography":{"school_location_semantics":"no_preference","selected_states":[],"work_market_semantics":"unspecified","intended_work_market":None},"page":1,"page_size":1}
            candidates=[
                {"candidate_id":"A","UNITID":"1","institution_name":"Zulu College","program_id":"P1","program_name":"Synthetic A","cip_code":"99.0001"},
                {"candidate_id":"B","UNITID":"2","institution_name":"Alpha College","program_id":"P1","program_name":"Synthetic B","cip_code":"99.0002"},
                {"candidate_id":"C","UNITID":"3","institution_name":"Middle College","program_id":"P1","program_name":"Synthetic C","cip_code":"99.0003"},
            ]
            (d/"request.json").write_text(json.dumps(request));(d/"candidates.json").write_text(json.dumps(candidates))
            write_csv(d/"ranked.csv",[
                {"candidate_id":"C","ranking_status":"ranked_pending_validation","baseline_score":"0.9","rank":"1","missing_weighted_dimensions":"","partial_weighted_dimensions":"","weighted_dimension_count":"1","review_eligibility":"eligible_for_review"},
                {"candidate_id":"A","ranking_status":"ranked_pending_validation","baseline_score":"0.7","rank":"2","missing_weighted_dimensions":"","partial_weighted_dimensions":"","weighted_dimension_count":"1","review_eligibility":"eligible_for_review"},
            ])
            (d/"review.json").write_text(json.dumps({"status":"RANKED_RESULTS_ELIGIBLE_FOR_REVIEW","recommendation_release_decision":"ELIGIBLE_FOR_REVIEW","ranking_status":"RANKING_READY_FOR_VALIDATION","ranked_input_count":2,"review_eligible_ranked_count":2,"production_authorized":False}))
            run("ranked_service_binding.py","--request",d/"request.json","--candidates",d/"candidates.json","--ranked",d/"ranked.csv","--review-summary",d/"review.json","--data-version","D1","--model-version","M1","--output",d/"bundle.json")
            run("match_service_adapter.py","--request",d/"request.json","--candidates",d/"candidates.json","--ranking-bundle",d/"bundle.json","--data-version","D1","--model-version","M1","--output",d/"page1.json")
            p1=json.loads((d/"page1.json").read_text());self.assertEqual(p1["results"][0]["candidate_id"],"C");self.assertEqual(p1["ordering"]["mode"],"review_eligible_ranking")
            request["page"]=2;(d/"request2.json").write_text(json.dumps(request))
            run("match_service_adapter.py","--request",d/"request2.json","--candidates",d/"candidates.json","--ranking-bundle",d/"bundle.json","--data-version","D1","--model-version","M1","--output",d/"page2.json")
            p2=json.loads((d/"page2.json").read_text());self.assertEqual(p2["results"][0]["candidate_id"],"A");self.assertEqual(p1["ordering"]["ranking_context_id"],p2["ordering"]["ranking_context_id"])
            request["preferences"][0]["importance"]=4;(d/"stale.json").write_text(json.dumps(request))
            p=subprocess.run([sys.executable,str(PROJECT/"match_service_adapter.py"),"--request",str(d/"stale.json"),"--candidates",str(d/"candidates.json"),"--ranking-bundle",str(d/"bundle.json"),"--data-version","D1","--model-version","M1","--output",str(d/"stale-out.json")],text=True,capture_output=True)
            self.assertNotEqual(p.returncode,0);self.assertIn("context does not match",p.stderr)

    def test_feature_registry_keeps_coverage_out_of_comparison_direction(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); out=d/"out"
            write_csv(d/"features.csv",[{"candidate_id":"FIC-1","net_price":"12000","career_coverage":"0.5"}])
            write_csv(d/"registry.csv",[
                {"feature_id":"net_price","source_column":"net_price","dimension":"affordability","role":"comparison","direction":"lower_better","source_family":"synthetic","source_vintage":"TEST","grain":"candidate","normalization_policy":"synthetic_ref"},
                {"feature_id":"career_cov","source_column":"career_coverage","dimension":"evidence_quality_coverage","role":"coverage","direction":"none","source_family":"synthetic","source_vintage":"TEST","grain":"candidate","normalization_policy":"none"},
            ])
            run("recommendation_feature_registry.py","--features",d/"features.csv","--registry",d/"registry.csv","--out-dir",out)
            lineage=read_csv(out/"recommendation_feature_lineage.csv")
            cov=next(r for r in lineage if r["feature_id"]=="career_cov"); self.assertEqual(cov["role"],"coverage"); self.assertEqual(cov["direction"],"none")

    def test_release_gate_blocks_missing_required_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); out=d/"out"
            write_csv(d/"gate.csv",[{"stage_id":"required_qa","artifact_path":str(d/"missing.json"),"required":"true","check_path":"status","operator":"eq","expected":"PASS"}])
            run("recommendation_release_gate.py","--gate-manifest",d/"gate.csv","--out-dir",out)
            result=json.loads((out/"recommendation_release_decision.json").read_text())
            self.assertEqual(result["release_decision"],"BLOCKED"); self.assertEqual(result["blocked_required_checks"],1)

    def test_pipeline_runner_blocks_downstream_after_required_failure(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); run_dir=d/"run"
            write_csv(d/"stages.csv",[
                {"stage_id":"first","command":"{python} -c \"import sys; sys.exit(3)\"","depends_on":"","required":"true","inputs":"","outputs":""},
                {"stage_id":"second","command":"{python} -c \"from pathlib import Path; Path(r'{run_dir}/should_not_exist').write_text('x')\"","depends_on":"first","required":"true","inputs":"","outputs":"{run_dir}/should_not_exist"},
            ])
            run("recommendation_pipeline_runner.py","--stage-manifest",d/"stages.csv","--run-dir",run_dir,expect=2)
            manifest=json.loads((run_dir/"recommendation_pipeline_run_manifest.json").read_text())
            by={r["stage_id"]:r for r in manifest["stages"]}
            self.assertEqual(by["first"]["status"],"FAIL"); self.assertEqual(by["second"]["status"],"BLOCKED_BY_DEPENDENCY")
            self.assertFalse((run_dir/"should_not_exist").exists())
            self.assertIn("run_started_utc",manifest); self.assertIn("run_finished_utc",manifest)
            self.assertIn("argv",by["first"]); self.assertNotIn("command",by["first"])

    def test_pipeline_runner_does_not_interpret_shell_metacharacters(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); run_dir=d/"run"; injected=d/"injected"
            # A semicolon is passed as an ordinary argv token; no second shell command can execute.
            write_csv(d/"stages.csv",[{
                "stage_id":"safe","command":f"{{python}} -c \"import sys; print(sys.argv[1:])\" ';' touch {injected}",
                "depends_on":"","required":"true","inputs":"","outputs":""
            }])
            run("recommendation_pipeline_runner.py","--stage-manifest",d/"stages.csv","--run-dir",run_dir)
            self.assertFalse(injected.exists())
            manifest=json.loads((run_dir/"recommendation_pipeline_run_manifest.json").read_text())
            self.assertEqual(manifest["overall_status"],"PIPELINE_COMPLETED")
            self.assertIn(";",manifest["stages"][0]["argv"])

if __name__=="__main__": unittest.main()
