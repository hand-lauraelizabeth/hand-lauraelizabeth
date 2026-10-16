"""Run official schema validation before a private NYC 311 monthly export."""
import argparse
import json
from pathlib import Path
from source_schema import fetch_schema
from source_export import acquire


def acquire_verified(month, output, **options):
    output = Path(output)
    proof = Path(str(output) + ".schema.json")
    if output.exists() or proof.exists():
        raise FileExistsError("Use a new versioned export filename")
    schema = fetch_schema()
    result = acquire(month, output, **options)
    with proof.open("x", encoding="utf-8") as handle:
        json.dump(schema, handle, sort_keys=True, indent=2)
    return result, schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    manifest, schema = acquire_verified(args.month, args.output, expected_count=args.expected_count)
    print(json.dumps({"rows_exported": manifest["rows_exported"], "sha256": manifest["sha256"],
                      "required_schema_sha256": schema["required_schema_sha256"]}))
