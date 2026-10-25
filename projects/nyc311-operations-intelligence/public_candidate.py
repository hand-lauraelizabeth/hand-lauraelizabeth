"""Construct a metadata-minimized, review-only NYC 311 aggregate candidate.

Not a publication authorization: external marginals, integer inference and
temporal differencing remain untested. Private receipts/counts stay private.
"""
import datetime as dt

GRAIN = ("month", "borough", "agency", "problem")
ROW_FIELDS = set(GRAIN) | {"requests", "closed_with_valid_interval"}


def prepare(private):
    """Allowlist only reviewed aggregate fields; reject unsafe source shapes."""
    if not isinstance(private, dict) or private.get("dataset_id") != "erm2-nwe9":
        raise ValueError("Unexpected private source schema")
    rules = private.get("rules")
    rows = private.get("aggregates")
    quality = private.get("quality")
    if not isinstance(rules, dict) or not isinstance(rows, list) or not isinstance(quality, dict):
        raise ValueError("Missing private audit fields")
    threshold = rules.get("display_minimum_cell_count")
    if type(threshold) is not int or threshold < 10:
        raise ValueError("Review candidate requires minimum cell threshold >= 10")
    if rules.get("grain") != "month × borough × agency × original API complaint_type":
        raise ValueError("Unexpected aggregation grain")
    snapshot = private.get("snapshot_as_of")
    if not isinstance(snapshot, str):
        raise ValueError("Missing snapshot date")
    try:
        dt.date.fromisoformat(snapshot)
    except ValueError as exc:
        raise ValueError("Invalid snapshot date") from exc
    if type(quality.get("rows_read")) is not int or type(quality.get("unique_keys_verified")) is not int:
        raise ValueError("Missing private key audit")
    if quality["rows_read"] != quality["unique_keys_verified"]:
        raise ValueError("Private unique-key audit incomplete")
    if type(quality.get("small_cells_suppressed")) is not int or quality["small_cells_suppressed"] < 0:
        raise ValueError("Invalid private suppression metadata")
    output = []
    keys = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            raise ValueError("Unexpected aggregate fields")
        key = tuple(row.get(name) for name in GRAIN)
        if any(not isinstance(value, str) or not value.strip() for value in key):
            raise ValueError("Invalid aggregate key")
        if key in keys:
            raise ValueError("Duplicate aggregate key")
        keys.add(key)
        n = row["requests"]
        c = row["closed_with_valid_interval"]
        if type(n) is not int or n < threshold:
            raise ValueError("Unsafe request count")
        if c is not None:
            if type(c) is not int or c < 0 or c > n:
                raise ValueError("Invalid closure count")
            if (0 < c < threshold) or (0 < n - c < threshold):
                raise ValueError("Unsafe closure subgroup")
        output.append({name: row[name] for name in (*GRAIN, "requests", "closed_with_valid_interval")})
    # No exact private totals, suppressed-group count, source hash, byte size,
    # or other unreviewed metadata crosses this boundary.
    return {
        "schema_version": "nyc311-review-candidate-v1",
        "dataset_id": "erm2-nwe9",
        "snapshot_as_of": snapshot,
        "rules": {"grain": rules["grain"], "display_minimum_cell_count": threshold},
        "aggregates": output,
    }
