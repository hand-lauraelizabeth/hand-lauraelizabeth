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
