---
name: json-schema-validator
description: "Validates JSON files against expected structure, identifies type mismatches, missing required keys, unexpected extra keys, and nested structure issues, then produces a concise validation report. Use when the user asks to validate, check, inspect, or audit JSON data or configuration files. Also trigger when users mention 'JSON structure', 'schema check', 'validate my JSON', 'missing keys', 'malformed JSON', 'config validation', or 'API response validation'. Do NOT use for creating new JSON from scratch or for converting JSON to other formats."
---

# JSON Schema Validator

A skill for validating JSON files against an expected schema and producing a clear validation report.

## What this skill does

Given a JSON file (and optionally a schema definition), this skill runs a Python validation script that:

1. Checks if the file is valid JSON (catches syntax errors with line/position info)
2. Infers or applies a schema: required keys, expected types, nesting depth
3. Reports missing required keys at every nesting level
4. Reports unexpected/extra keys not in the schema
5. Detects type mismatches (e.g. a field expected to be an integer is a string)
6. Flags inconsistent types within arrays (e.g. mixed objects and strings)
7. Reports basic statistics: total keys, nesting depth, array lengths

The script outputs a structured JSON report. Claude then reads the JSON and presents a human-friendly summary highlighting the most critical issues.

## When to use this skill

- User uploads a JSON file and asks "is this valid?" or "check my JSON"
- User wants to validate API responses, config files, or data exports
- User says "schema validation" or "find missing fields in my JSON"
- User asks to compare a JSON file against expected structure

## When NOT to use this skill

- The file is YAML, XML, or another non-JSON format
- The user wants to *create* or *transform* JSON rather than validate it
- The user wants to pretty-print or format JSON (that's a simple built-in operation)

## Workflow

1. Copy the user's JSON from `/mnt/user-data/uploads/` to `/home/claude/`
2. Run the validation script:
   ```bash
   python /path/to/json-schema-validator/scripts/validate.py /home/claude/<filename>.json
   ```
   Optionally with a schema file:
   ```bash
   python /path/to/json-schema-validator/scripts/validate.py /home/claude/<filename>.json --schema /home/claude/schema.json
   ```
3. The script prints a JSON report to stdout
4. Read the JSON and present a clear summary covering:
   - Whether the JSON is syntactically valid
   - Missing required keys
   - Type mismatches
   - Unexpected extra keys
   - Array consistency issues
5. End with actionable suggestions

## Expected inputs

- One JSON file uploaded by the user
- Optionally a schema JSON file defining expected structure

## Expected output

- A conversational summary of validation issues with specific paths and details
- The raw JSON report is available if the user wants full details

## Important notes

- If no schema is provided, the script infers structure from the data itself (useful for finding inconsistencies within arrays of objects)
- The script handles common encodings (utf-8, latin-1) automatically
- For very large JSON files (>50 MB), warn the user that processing may take a moment
- If the JSON is completely malformed, the script reports the parse error location
