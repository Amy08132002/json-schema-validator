#!/usr/bin/env python3
"""
json-schema-validator: validate a JSON file's structure and produce a report.

Usage:
    python validate.py <path_to_json> [--schema <path_to_schema>]

Output:
    JSON validation report printed to stdout.
"""

import argparse
import json
import os
import sys
from collections import Counter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect_encoding(path: str) -> str:
    """Try common encodings and return the first that works."""
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(path, encoding=enc, errors="strict") as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def get_type_name(value) -> str:
    """Return a human-readable type name for a JSON value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def compute_depth(obj, current=0) -> int:
    """Compute the maximum nesting depth of a JSON structure."""
    if isinstance(obj, dict):
        if not obj:
            return current + 1
        return max(compute_depth(v, current + 1) for v in obj.values())
    elif isinstance(obj, list):
        if not obj:
            return current + 1
        return max(compute_depth(item, current + 1) for item in obj)
    else:
        return current


def count_keys(obj) -> int:
    """Count total number of keys in a JSON structure recursively."""
    total = 0
    if isinstance(obj, dict):
        total += len(obj)
        for v in obj.values():
            total += count_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            total += count_keys(item)
    return total


# ---------------------------------------------------------------------------
# Schema inference from arrays of objects
# ---------------------------------------------------------------------------

def infer_schema_from_array(arr: list) -> dict | None:
    """
    If an array contains objects, infer a schema from the union of all keys
    and their most common types.
    """
    objects = [item for item in arr if isinstance(item, dict)]
    if len(objects) < 2:
        return None

    key_types = {}
    key_counts = Counter()

    for obj in objects:
        for key, value in obj.items():
            key_counts[key] += 1
            t = get_type_name(value)
            if key not in key_types:
                key_types[key] = Counter()
            key_types[key][t] += 1

    total = len(objects)
    schema = {}
    for key, type_counter in key_types.items():
        dominant_type = type_counter.most_common(1)[0][0]
        required = key_counts[key] == total
        schema[key] = {
            "expected_type": dominant_type,
            "required": required,
            "occurrence_count": key_counts[key],
            "occurrence_pct": round(key_counts[key] / total * 100, 1),
            "type_distribution": dict(type_counter),
        }

    return schema


# ---------------------------------------------------------------------------
# Validation against explicit schema
# ---------------------------------------------------------------------------

def validate_against_schema(data, schema: dict, path: str = "$") -> list:
    """
    Validate data against a user-provided schema.
    Schema format:
    {
        "key_name": {"type": "string", "required": true},
        "nested_obj": {
            "type": "object",
            "required": true,
            "properties": { ... }
        }
    }
    """
    issues = []

    if not isinstance(data, dict):
        issues.append({
            "path": path,
            "issue": "type_mismatch",
            "expected": "object",
            "got": get_type_name(data),
        })
        return issues

    data_keys = set(data.keys())
    schema_keys = set(schema.keys())

    # Missing required keys
    for key, spec in schema.items():
        if isinstance(spec, dict) and spec.get("required", False):
            if key not in data:
                issues.append({
                    "path": f"{path}.{key}",
                    "issue": "missing_required_key",
                    "key": key,
                })

    # Extra keys not in schema
    extra = data_keys - schema_keys
    for key in sorted(extra):
        issues.append({
            "path": f"{path}.{key}",
            "issue": "unexpected_key",
            "key": key,
        })

    # Type checking
    for key in data_keys & schema_keys:
        spec = schema[key]
        if not isinstance(spec, dict):
            continue
        expected_type = spec.get("type")
        if expected_type:
            actual_type = get_type_name(data[key])
            # Allow integer where float is expected
            if expected_type == "float" and actual_type == "integer":
                continue
            if actual_type != expected_type and data[key] is not None:
                issues.append({
                    "path": f"{path}.{key}",
                    "issue": "type_mismatch",
                    "expected": expected_type,
                    "got": actual_type,
                })

        # Recurse into nested objects
        if spec.get("type") == "object" and "properties" in spec:
            if isinstance(data[key], dict):
                issues.extend(
                    validate_against_schema(data[key], spec["properties"], f"{path}.{key}")
                )

    return issues


# ---------------------------------------------------------------------------
# Self-consistency check (no schema provided)
# ---------------------------------------------------------------------------

def check_consistency(data, path: str = "$") -> list:
    """Check a JSON structure for internal inconsistencies."""
    issues = []

    if isinstance(data, dict):
        # Check for null values
        for key, value in data.items():
            if value is None:
                issues.append({
                    "path": f"{path}.{key}",
                    "issue": "null_value",
                    "key": key,
                })
            # Recurse
            issues.extend(check_consistency(value, f"{path}.{key}"))

    elif isinstance(data, list):
        if len(data) == 0:
            issues.append({
                "path": path,
                "issue": "empty_array",
            })
        else:
            # Check type consistency within array
            types = [get_type_name(item) for item in data]
            type_counts = Counter(types)
            if len(type_counts) > 1:
                issues.append({
                    "path": path,
                    "issue": "mixed_array_types",
                    "type_distribution": dict(type_counts),
                })

            # If array of objects, check key consistency
            inferred = infer_schema_from_array(data)
            if inferred:
                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    for key, spec in inferred.items():
                        if spec["required"] and key not in item:
                            issues.append({
                                "path": f"{path}[{i}]",
                                "issue": "missing_key_in_array_object",
                                "key": key,
                                "expected_in": f"{spec['occurrence_count']} of {len([x for x in data if isinstance(x, dict)])} objects",
                            })
                        if key in item:
                            actual_t = get_type_name(item[key])
                            expected_t = spec["expected_type"]
                            if actual_t != expected_t and item[key] is not None:
                                if not (expected_t == "float" and actual_t == "integer"):
                                    issues.append({
                                        "path": f"{path}[{i}].{key}",
                                        "issue": "type_mismatch_in_array",
                                        "expected": expected_t,
                                        "got": actual_t,
                                    })

            # Recurse into array items
            for i, item in enumerate(data):
                issues.extend(check_consistency(item, f"{path}[{i}]"))

    return issues


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_json(path: str, schema_path: str | None = None) -> dict:
    """Run all checks and return a report dict."""

    if not os.path.isfile(path):
        return {"error": f"File not found: {path}"}

    file_size = os.path.getsize(path)
    enc = detect_encoding(path)

    # Read and parse
    with open(path, encoding=enc, errors="replace") as f:
        raw = f.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {
            "file": os.path.basename(path),
            "valid_json": False,
            "parse_error": {
                "message": str(e),
                "line": e.lineno,
                "column": e.colno,
                "position": e.pos,
            },
        }

    # Basic stats
    root_type = get_type_name(data)
    depth = compute_depth(data)
    total_keys = count_keys(data)

    # Validation
    issues = []
    schema_used = None

    if schema_path:
        # Validate against provided schema
        if not os.path.isfile(schema_path):
            return {"error": f"Schema file not found: {schema_path}"}
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        issues = validate_against_schema(data, schema)
        schema_used = "user_provided"
    else:
        # Self-consistency check
        issues = check_consistency(data)
        schema_used = "self_consistency"

    # Categorize issues
    issue_summary = Counter(i["issue"] for i in issues)

    report = {
        "file": os.path.basename(path),
        "file_size_bytes": file_size,
        "encoding_detected": enc,
        "valid_json": True,
        "root_type": root_type,
        "max_nesting_depth": depth,
        "total_keys": total_keys,
        "schema_used": schema_used,
        "total_issues": len(issues),
        "issue_summary": dict(issue_summary),
        "issues": issues[:50],  # cap output
        "issues_truncated": len(issues) > 50,
    }

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="JSON Schema Validator")
    parser.add_argument("json_path", help="Path to the JSON file")
    parser.add_argument("--schema", default=None, help="Path to schema JSON file (optional)")
    args = parser.parse_args()

    report = validate_json(args.json_path, schema_path=args.schema)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
