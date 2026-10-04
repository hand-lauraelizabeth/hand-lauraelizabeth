from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "college-career-matching"
MANIFEST = PROJECT / "source_manifest.json"
MATRIX = PROJECT / "MVP_Field_Level_Source_Matrix.csv"
COVERAGE_BASELINES = PROJECT / "coverage_baselines.json"

issues: list[str] = []


def fail(message: str) -> None:
    issues.append(message)


def is_https(url: str) -> bool:
    try:
        return urlparse(url).scheme == "https"
    except Exception:
        return False


if not MANIFEST.exists():
    fail(f"missing manifest: {MANIFEST.relative_to(ROOT)}")
    manifest = {}
else:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in source manifest: {exc}")
        manifest = {}

required_top = {"schema_version", "as_of_date", "project", "principles", "sources", "join_contracts"}
missing_top = required_top - set(manifest)
if missing_top:
    fail(f"manifest missing top-level keys: {sorted(missing_top)}")

try:
    date.fromisoformat(str(manifest.get("as_of_date", "")))
except ValueError:
    fail("manifest as_of_date must be ISO YYYY-MM-DD")

sources = manifest.get("sources", [])
if not isinstance(sources, list) or not sources:
    fail("manifest sources must be a non-empty list")
    sources = []

source_ids: list[str] = []
required_source_fields = {
    "source_id", "title", "agency", "status", "access_type", "official_url",
    "release", "license_or_terms", "sensitivity", "canonical_keys",
    "refresh_policy", "retrieval_mode", "required_metadata",
    "required_artifacts", "qa",
}

for source in sources:
    if not isinstance(source, dict):
        fail("every source entry must be an object")
        continue

    missing = required_source_fields - set(source)
    if missing:
        fail(f"source {source.get('source_id', '<unknown>')} missing: {sorted(missing)}")

    source_id = str(source.get("source_id", "")).strip()
    if not source_id:
        fail("source entry has blank source_id")
    else:
        source_ids.append(source_id)

    if source.get("status") == "production_core" and source.get("sensitivity") != "public":
        fail(f"{source_id}: production_core source must be public")

    official_url = str(source.get("official_url", ""))
    if not is_https(official_url):
        fail(f"{source_id}: official_url must be HTTPS")

    access_url = source.get("access_url")
    if access_url:
        if not is_https(str(access_url)):
            fail(f"{source_id}: access_url must be HTTPS")
        lower = str(access_url).lower()
        if "api_key=" in lower or "demo_key" in lower:
            fail(f"{source_id}: access_url must not contain an API key")

    if source.get("access_type") == "post_download" and not access_url:
        fail(f"{source_id}: post_download requires access_url")

    if source.get("access_type") == "multi_file_download":
        files = source.get("files")
        if not isinstance(files, dict) or not files:
            fail(f"{source_id}: multi_file_download requires a non-empty files mapping")
        else:
            for file_name, file_url in files.items():
                if not str(file_name).strip():
                    fail(f"{source_id}: file mapping contains a blank name")
                if not is_https(str(file_url)):
                    fail(f"{source_id}: file URL for {file_name!r} must be HTTPS")
                if "api_key=" in str(file_url).lower():
                    fail(f"{source_id}: file URL for {file_name!r} must not contain an API key")

    release = source.get("release")
    if not isinstance(release, dict) or not release.get("label") or not release.get("policy"):
        fail(f"{source_id}: release requires label and policy")

    keys = source.get("canonical_keys")
    if not isinstance(keys, list) or not keys or any(not str(k).strip() for k in keys):
        fail(f"{source_id}: canonical_keys must be a non-empty list")

    for field in ("required_metadata", "required_artifacts", "qa"):
        value = source.get(field)
        if not isinstance(value, list) or not value:
            fail(f"{source_id}: {field} must be a non-empty list")

    auth = source.get("authentication")
    if auth:
        if auth.get("secret_in_repository") is not False:
            fail(f"{source_id}: authentication secrets must not be stored in repository")
        if not auth.get("environment_variable"):
            fail(f"{source_id}: authenticated source needs an environment_variable name")

if len(source_ids) != len(set(source_ids)):
    fail("source_id values must be unique")

expected_sources = {
    "college_scorecard",
    "dapip_accreditation",
    "ipeds_directory_2025",
    "ipeds_completions_2025",
    "cip_soc_crosswalk_2020_2018",
    "onet_31_0",
    "dapip_accreditation",
    "bls_employment_projections_2025_2035",
    "bls_oews_may_2025",
}
missing_expected = expected_sources - set(source_ids)
if missing_expected:
    fail(f"manifest missing required MVP sources: {sorted(missing_expected)}")

joins = manifest.get("join_contracts", [])
join_ids: set[str] = set()
for join in joins if isinstance(joins, list) else []:
    join_id = str(join.get("join_id", "")).strip()
    if not join_id:
        fail("join contract has blank join_id")
        continue
    if join_id in join_ids:
        fail(f"duplicate join_id: {join_id}")
    join_ids.add(join_id)

    for side in ("left_source", "right_source"):
        if join.get(side) not in source_ids:
            fail(f"{join_id}: {side} references unknown source {join.get(side)!r}")

    if not join.get("left_key") or not join.get("right_key"):
        fail(f"{join_id}: both join keys are required")

dapip_join = next((j for j in joins if j.get("join_id") == "ipeds_to_dapip"), None)
if not dapip_join or dapip_join.get("left_key") != ["UNITID"] or dapip_join.get("right_key") != ["UNITID"]:
    fail("IPEDS-DAPIP join must explicitly use UNITID on both sides")

cip_join = next((j for j in joins if j.get("join_id") == "ipeds_program_to_cip_soc"), None)
if not cip_join or cip_join.get("expected_cardinality") != "many_to_many":
    fail("CIP-SOC join must explicitly remain many_to_many")

if not COVERAGE_BASELINES.exists():
    fail(f"missing coverage baselines: {COVERAGE_BASELINES.relative_to(ROOT)}")
    coverage_baselines = {}
else:
    try:
        coverage_baselines = json.loads(COVERAGE_BASELINES.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in coverage baselines: {exc}")
        coverage_baselines = {}

baseline_layers = coverage_baselines.get("layers", {})
for layer in ("institution", "program", "career"):
    config = baseline_layers.get(layer)
    if not isinstance(config, dict):
        fail(f"coverage baselines missing layer: {layer}")
        continue
    minimums = config.get("minimums")
    if not isinstance(minimums, dict) or not minimums:
        fail(f"coverage baseline {layer}: minimums must be a non-empty object")
        continue
    for metric, minimum in minimums.items():
        if not str(metric).strip():
            fail(f"coverage baseline {layer}: metric path must not be blank")
        if not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or minimum < 0:
            fail(f"coverage baseline {layer}.{metric}: minimum must be a non-negative number")

if not MATRIX.exists():
    fail(f"missing source matrix: {MATRIX.relative_to(ROOT)}")
    rows: list[dict[str, str]] = []
else:
    with MATRIX.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_headers = {
            "Layer", "Matcher Field", "Production Source", "Source Variable / Table",
            "Join Key", "Geography / Grain", "Refresh Cadence", "Transformation",
            "Missing-Data Rule", "MVP Use",
        }
        if reader.fieldnames is None:
            fail("source matrix has no header")
            rows = []
        else:
            missing_headers = required_headers - set(reader.fieldnames)
            if missing_headers:
                fail(f"source matrix missing headers: {sorted(missing_headers)}")
            rows = list(reader)

if len(rows) < 84:
    fail(f"source matrix unexpectedly small: {len(rows)} rows; expected at least 84")

pairs: set[tuple[str, str]] = set()
private_terms = ("handshake", "symplicity", "linkedin", "private employer")
for idx, row in enumerate(rows, start=2):
    layer = (row.get("Layer") or "").strip()
    field = (row.get("Matcher Field") or "").strip()
    production_source = (row.get("Production Source") or "").strip()

    if not layer or not field:
        fail(f"source matrix row {idx}: Layer and Matcher Field are required")
        continue

    pair = (layer, field)
    if pair in pairs:
        fail(f"source matrix duplicate Layer/Matcher Field at row {idx}: {pair}")
    pairs.add(pair)

    lowered_source = production_source.lower()
    if any(term in lowered_source for term in private_terms):
        fail(f"source matrix row {idx}: private source appears in production configuration")

    if layer == "User Input" and production_source != "User-entered":
        fail(f"source matrix row {idx}: User Input must use 'User-entered' as source")
    if layer == "Derived" and production_source != "Derived":
        fail(f"source matrix row {idx}: Derived fields must use 'Derived' as source")

if issues:
    print("College + Career source contract validation failed:")
    for issue in issues:
        print(f"- {issue}")
    sys.exit(1)

print(
    "College + Career source contract validation passed: "
    f"{len(source_ids)} sources, {len(join_ids)} joins, {len(rows)} matrix fields, and 3 coverage baseline layers."
)
