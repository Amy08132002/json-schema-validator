# json-schema-validator

A reusable AI skill that validates JSON files for structural issues and produces a concise validation report.

## What it does

Given a JSON file, `json-schema-validator` runs a Python script that automatically:

- Checks if the file is syntactically valid JSON (with precise error location if not)
- Detects missing required keys at every nesting level
- Identifies type mismatches (e.g. a field expected to be an integer is a string)
- Finds unexpected/extra keys not defined in the schema
- Flags inconsistent types within arrays (e.g. mixed objects and strings)
- Checks key consistency across arrays of objects (e.g. one object missing a field all others have)
- Reports basic stats: total keys, nesting depth, root type

Two modes are supported:
1. **With a schema**: validates data against user-provided expected structure
2. **Without a schema**: performs self-consistency checks (finds internal inconsistencies)

## Why this skill

JSON is the most common data interchange format, but subtle structural issues — a missing key, a field that's a string instead of a number, an inconsistent array — can cause silent failures downstream. Manually inspecting nested JSON is tedious and error-prone. This skill automates that first-pass structural validation.

## How to use it

1. Upload a JSON file to Claude
2. Ask something like:
   - "Validate this JSON file"
   - "Check if this JSON has any structural issues"
   - "Are there missing keys or type problems in this config?"
3. Claude runs `scripts/validate.py` on your file and summarizes the results

## What the script does

`scripts/validate.py` is a standalone Python script (no external dependencies) that:

1. Auto-detects file encoding (utf-8, latin-1, cp1252)
2. Attempts to parse the JSON, reporting syntax errors with line/column info
3. Either validates against a user-provided schema or performs self-consistency analysis
4. Recursively walks the entire structure, checking types and keys at every level
5. For arrays of objects, infers expected schema and flags deviations
6. Outputs a structured JSON report to stdout

The script is the load-bearing part — it performs recursive traversal, type inference across array elements, and precise path-based error reporting that cannot be done reliably through prose alone.

## What it outputs

A conversational summary highlighting:
- Whether the JSON is valid
- Missing required keys (with JSON path)
- Type mismatches (with expected vs actual)
- Unexpected extra keys
- Array consistency issues
- Actionable suggestions for fixes

## Limitations

- Only handles `.json` files (not YAML, TOML, or XML)
- Schema format is a simplified custom format, not JSON Schema Draft 7/2020-12
- Very large files (>50 MB) may be slow
- Does not perform data transformation — only inspection and reporting

## Demo Video

[Video link placeholder — replace with your YouTube/Vimeo URL]
