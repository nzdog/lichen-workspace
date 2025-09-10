#!/usr/bin/env python3
"""
JSON Schema validation script for Lichen Protocol contracts.

Validates all JSON contracts in the repo against their JSON Schemas.
"""

import argparse
import glob
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import os

try:
    from jsonschema import Draft202012Validator, FormatChecker, ValidationError
    from jsonschema.exceptions import SchemaError
except ImportError:
    print("Error: jsonschema package is required but not installed.")
    print("Please install it with: pip install jsonschema>=4,<5")
    sys.exit(2)


@dataclass
class ValidationResult:
    """Result of validating a single file against a schema."""
    file: str
    ok: bool
    errors: List[Dict[str, Any]]
    warnings: List[str]


@dataclass
class ValidationSummary:
    """Summary of all validation results."""
    checked: int
    valid: int
    invalid: int
    errors: int


class ContractValidator:
    """Main validator class for JSON contracts."""

    # Allowlist for warnings that should not be treated as errors
    ALLOWLIST = {"$comment"}

    def __init__(self, repo_root: Path, strict: bool = False):
        self.repo_root = repo_root
        self.strict = strict
        self.format_checker = FormatChecker()
        self.schema_cache: Dict[str, Any] = {}

    def check_schema_hygiene(self, schema_path: Path, schema: Dict[str, Any]) -> List[str]:
        """Check schema hygiene rules."""
        errors = []

        # Check that $schema is the first key
        schema_keys = list(schema.keys())
        if schema_keys and schema_keys[0] != '$schema':
            errors.append(f"SCHEMA_HYGIENE: $schema must be the first key -> {schema_path}")

        # Check for unknown keywords (warnings-as-errors)
        known_keywords = {
            '$schema', '$id', '$ref', '$anchor', '$dynamicRef', '$dynamicAnchor',
            '$vocabulary', '$comment', '$defs', 'title', 'description', 'default',
            'deprecated', 'readOnly', 'writeOnly', 'examples', 'const', 'enum',
            'type', 'properties', 'patternProperties', 'additionalProperties',
            'items', 'contains', 'additionalItems', 'unevaluatedItems',
            'prefixItems', 'minItems', 'maxItems', 'uniqueItems', 'allOf',
            'anyOf', 'oneOf', 'not', 'if', 'then', 'else', 'dependentSchemas',
            'pattern', 'format', 'contentEncoding', 'contentMediaType',
            'contentSchema', 'minLength', 'maxLength', 'minimum', 'maximum',
            'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf', 'minProperties',
            'maxProperties', 'required', 'dependentRequired', 'propertyNames',
            'unevaluatedProperties', 'minContains', 'maxContains'
        }

        def check_keywords(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key.startswith('$') and key not in known_keywords and key not in self.ALLOWLIST:
                        errors.append(f"Unknown keyword '{key}' at {current_path} in {schema_path}")
                    if isinstance(value, (dict, list)):
                        check_keywords(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_keywords(item, f"{path}[{i}]")

        check_keywords(schema)
        return errors

    def load_schema(self, schema_path: Path) -> Tuple[Any, List[str]]:
        """Load and validate a JSON schema file."""
        warnings = []

        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise ValueError(f"Could not read/parse schema {schema_path}: {e}")

        # Check schema hygiene
        hygiene_errors = self.check_schema_hygiene(schema_path, schema)
        if hygiene_errors:
            for error in hygiene_errors:
                print(f"❌ {error}")
            sys.exit(1)

        # Check if schema specifies draft-2020-12
        if '$schema' in schema and 'draft/2020-12' not in schema['$schema']:
            warnings.append(f"Non-draft-2020-12 $schema: {schema['$schema']}")

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as e:
            raise ValueError(f"Invalid schema {schema_path}: {e}")

        return schema, warnings

    def validate_file(self, file_path: Path, schema: Any) -> ValidationResult:
        """Validate a single JSON file against a schema."""
        errors = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            return ValidationResult(
                file=str(file_path.relative_to(self.repo_root)),
                ok=False,
                errors=[{"message": f"Could not read/parse file: {e}"}],
                warnings=[]
            )

        try:
            validator = Draft202012Validator(schema, format_checker=self.format_checker)
            validation_errors = list(validator.iter_errors(data))

            if validation_errors:
                for error in validation_errors:
                    errors.append({
                        "instance_path": error.path,
                        "schema_path": error.schema_path,
                        "message": error.message
                    })
                ok = False
            else:
                ok = True

        except Exception as e:
            errors.append({"message": f"Validation error: {e}"})
            ok = False

        return ValidationResult(
            file=str(file_path.relative_to(self.repo_root)),
            ok=ok,
            errors=errors,
            warnings=warnings
        )

    def validate_rooms(self) -> List[ValidationResult]:
        """Validate all room contracts."""
        schema_path = self.repo_root / "contracts" / "schema" / "rooms.schema.json"
        data_glob = str(self.repo_root / "contracts" / "rooms" / "*.json")

        try:
            schema, warnings = self.load_schema(schema_path)
            self.schema_cache[str(schema_path)] = (schema, warnings)
        except ValueError as e:
            return [ValidationResult(
                file="rooms.schema.json",
                ok=False,
                errors=[{"message": str(e)}],
                warnings=[]
            )]

        results = []
        data_files = sorted(glob.glob(data_glob))

        for data_file in data_files:
            result = self.validate_file(Path(data_file), schema)
            result.warnings.extend(warnings)  # Add schema warnings to each result
            results.append(result)

        return results

    def validate_services(self) -> List[ValidationResult]:
        """Validate all service contracts."""
        service_mappings = [
            ("diagnostics.schema.json", "diagnostics.json"),
            ("memory.schema.json", "memory.json")
        ]

        results = []
        for schema_name, data_name in service_mappings:
            schema_path = self.repo_root / "contracts" / "schema" / schema_name
            data_path = self.repo_root / "contracts" / "services" / data_name

            try:
                schema, warnings = self.load_schema(schema_path)
                self.schema_cache[str(schema_path)] = (schema, warnings)
            except ValueError as e:
                results.append(ValidationResult(
                    file=schema_name,
                    ok=False,
                    errors=[{"message": str(e)}],
                    warnings=[]
                ))
                continue

            if data_path.exists():
                result = self.validate_file(data_path, schema)
                result.warnings.extend(warnings)
                results.append(result)
            else:
                results.append(ValidationResult(
                    file=data_name,
                    ok=False,
                    errors=[{"message": f"Data file not found: {data_path}"}],
                    warnings=[]
                ))

        return results

    def validate_gates(self) -> List[ValidationResult]:
        """Auto-discover and validate all gate contracts."""
        schema_dir = self.repo_root / "contracts" / "schema" / "gates"
        gates_dir = self.repo_root / "contracts" / "gates"

        if not schema_dir.exists():
            return [ValidationResult(
                file="gates schema directory",
                ok=False,
                errors=[{"message": f"Schema directory not found: {schema_dir}"}],
                warnings=[]
            )]

        schema_files = sorted(glob.glob(str(schema_dir / "*.schema.json")))
        results = []

        for schema_file in schema_files:
            schema_path = Path(schema_file)
            basename = schema_path.stem.replace('.schema', '')
            data_file = gates_dir / f"{basename}.json"

            try:
                schema, warnings = self.load_schema(schema_path)
                self.schema_cache[str(schema_path)] = (schema, warnings)
            except ValueError as e:
                results.append(ValidationResult(
                    file=schema_path.name,
                    ok=False,
                    errors=[{"message": str(e)}],
                    warnings=[]
                ))
                continue

            if data_file.exists():
                result = self.validate_file(data_file, schema)
                result.warnings.extend(warnings)
                results.append(result)
            else:
                warning_msg = f"Schema exists but no corresponding data file: {data_file}"
                results.append(ValidationResult(
                    file=basename,
                    ok=False,
                    errors=[{"message": warning_msg}],
                    warnings=[]
                ))

        # Check for data files without schemas
        if gates_dir.exists():
            data_files = glob.glob(str(gates_dir / "*.json"))
            for data_file in data_files:
                data_path = Path(data_file)
                basename = data_path.stem
                schema_file = schema_dir / f"{basename}.schema.json"

                if not schema_file.exists():
                    warning_msg = f"Data file exists but no corresponding schema: {schema_file}"
                    if self.strict:
                        results.append(ValidationResult(
                            file=basename,
                            ok=False,
                            errors=[{"message": warning_msg}],
                            warnings=[]
                        ))
                    else:
                        # Just add a warning result
                        results.append(ValidationResult(
                            file=basename,
                            ok=True,
                            errors=[],
                            warnings=[warning_msg]
                        ))

        return results

    def validate_rag(self) -> List[ValidationResult]:
        """Validate all RAG schema files."""
        rag_dir = self.repo_root / "contracts" / "rag"

        if not rag_dir.exists():
            return [ValidationResult(
                file="rag directory",
                ok=False,
                errors=[{"message": f"RAG directory not found: {rag_dir}"}],
                warnings=[]
            )]

        schema_files = sorted(glob.glob(str(rag_dir / "*.schema.json")))
        results = []

        for schema_file in schema_files:
            schema_path = Path(schema_file)

            try:
                schema, warnings = self.load_schema(schema_path)
                self.schema_cache[str(schema_path)] = (schema, warnings)

                # For RAG schemas, we just validate the schema itself
                # No corresponding data files to validate against
                results.append(ValidationResult(
                    file=str(schema_path.relative_to(self.repo_root)),
                    ok=True,
                    errors=[],
                    warnings=warnings
                ))

            except ValueError as e:
                results.append(ValidationResult(
                    file=schema_path.name,
                    ok=False,
                    errors=[{"message": str(e)}],
                    warnings=[]
                ))

        return results

    def validate_rag_build(self) -> List[ValidationResult]:
        """Validate all RAG build schema files."""
        rag_build_dir = self.repo_root / "contracts" / "rag_build"

        if not rag_build_dir.exists():
            return [ValidationResult(
                file="rag_build directory",
                ok=False,
                errors=[{"message": f"RAG build directory not found: {rag_build_dir}"}],
                warnings=[]
            )]

        schema_files = sorted(glob.glob(str(rag_build_dir / "*.schema.json")))
        results = []

        for schema_file in schema_files:
            schema_path = Path(schema_file)

            try:
                schema, warnings = self.load_schema(schema_path)
                self.schema_cache[str(schema_path)] = (schema, warnings)

                # For RAG build schemas, we just validate the schema itself
                # No corresponding data files to validate against
                results.append(ValidationResult(
                    file=str(schema_path.relative_to(self.repo_root)),
                    ok=True,
                    errors=[],
                    warnings=warnings
                ))

            except ValueError as e:
                results.append(ValidationResult(
                    file=schema_path.name,
                    ok=False,
                    errors=[{"message": str(e)}],
                    warnings=[]
                ))

        return results

    def validate_custom(self, schema_path: str, data_glob: str) -> List[ValidationResult]:
        """Validate custom schema/data combinations."""
        schema_file = Path(schema_path)
        if not schema_file.is_absolute():
            schema_file = self.repo_root / schema_path

        try:
            schema, warnings = self.load_schema(schema_file)
        except ValueError as e:
            return [ValidationResult(
                file=schema_path,
                ok=False,
                errors=[{"message": str(e)}],
                warnings=[]
            )]

        # Resolve glob relative to repo root if not absolute
        if not Path(data_glob).is_absolute():
            data_glob = str(self.repo_root / data_glob)

        data_files = sorted(glob.glob(data_glob))
        results = []

        for data_file in data_files:
            result = self.validate_file(Path(data_file), schema)
            result.warnings.extend(warnings)
            results.append(result)

        return results


def print_results(results: List[ValidationResult], title: str, strict: bool = False):
    """Print validation results with nice formatting."""
    print(f"\n{title}")
    print("=" * len(title))

    for result in results:
        if result.ok and not result.errors and not result.warnings:
            print(f"✅ valid: {result.file}")
        else:
            print(f"❌ invalid: {result.file}")
            for error in result.errors:
                if "instance_path" in error and error["instance_path"]:
                    print(f"    {error['instance_path']}: {error['message']}")
                else:
                    print(f"    {error['message']}")
            for warning in result.warnings:
                print(f"    ⚠️  warning (treated as error): {warning}")


def print_summary(all_results: List[ValidationResult], strict: bool = False):
    """Print summary of all validation results."""
    checked = len(all_results)
    valid = sum(1 for r in all_results if r.ok and not r.errors)
    invalid = checked - valid
    errors = sum(1 for r in all_results if not r.ok or (strict and r.warnings))

    print(f"\nSummary: {checked} files checked | {valid} valid | {invalid} invalid | {errors} errors")

    if errors > 0:
        return False
    return True


def output_json(all_results: List[ValidationResult], summary: ValidationSummary):
    """Output machine-readable JSON report."""
    json_output = {
        "summary": asdict(summary),
        "results": [asdict(result) for result in all_results]
    }
    print(json.dumps(json_output, indent=2))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate JSON contracts against their JSON Schemas"
    )
    parser.add_argument(
        "--only",
        choices=["rooms", "services", "gates", "rag", "rag_build"],
        help="Only validate specific contract types"
    )
    parser.add_argument(
        "--schema",
        action="append",
        help="Custom schema path (can be repeated)"
    )
    parser.add_argument(
        "--data",
        action="append",
        help="Custom data glob pattern (can be repeated)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output machine-readable JSON report"
    )

    args = parser.parse_args()

    # Determine repo root (script's parent directory)
    repo_root = Path(__file__).resolve().parents[1]

    validator = ContractValidator(repo_root, strict=args.strict)
    all_results = []

    try:
        if args.schema and args.data:
            # Custom validation
            if len(args.schema) != len(args.data):
                print("Error: --schema and --data arguments must have matching counts")
                sys.exit(2)

            for schema, data in zip(args.schema, args.data):
                results = validator.validate_custom(schema, data)
                all_results.extend(results)
                print_results(results, f"Custom Validation: {schema} → {data}")

        else:
            # Default validation sets
            if not args.only or args.only == "rooms":
                results = validator.validate_rooms()
                all_results.extend(results)
                print_results(results, "Rooms Validation", args.strict)

            if not args.only or args.only == "services":
                results = validator.validate_services()
                all_results.extend(results)
                print_results(results, "Services Validation", args.strict)

            if not args.only or args.only == "gates":
                results = validator.validate_gates()
                all_results.extend(results)
                print_results(results, "Gates Validation", args.strict)

            if not args.only or args.only == "rag":
                results = validator.validate_rag()
                all_results.extend(results)
                print_results(results, "RAG Validation", args.strict)

            if not args.only or args.only == "rag_build":
                results = validator.validate_rag_build()
                all_results.extend(results)
                print_results(results, "RAG Build Validation", args.strict)

        # Calculate summary
        checked = len(all_results)
        valid = sum(1 for r in all_results if r.ok and not r.errors and not r.warnings)
        invalid = checked - valid
        errors = sum(1 for r in all_results if not r.ok or r.errors or r.warnings)

        summary = ValidationSummary(checked=checked, valid=valid, invalid=invalid, errors=errors)

        # Print summary
        success = print_summary(all_results, args.strict)

        # Output JSON if requested
        if args.json:
            output_json(all_results, summary)

        # Exit with appropriate code
        if errors > 0:
            sys.exit(1)
        elif not success:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()


# Validate everything:
#   python3 scripts/validate.py
# Only rooms:
#   python3 scripts/validate.py --only rooms
# Ad-hoc:
#   python3 scripts/validate.py --schema ./contracts/schema/rooms.schema.json --data "./contracts/rooms/*.json"
# JSON report:
#   python3 scripts/validate.py --json > validation_report.json
# Strict mode (warnings fail the build):
#   python3 scripts/validate.py --strict
