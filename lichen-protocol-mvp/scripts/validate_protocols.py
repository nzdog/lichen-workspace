import json, glob, sys
from jsonschema import validate, Draft7Validator

with open("protocol_template_schema_v1.json") as f:
    schema = json.load(f)

validator = Draft7Validator(schema)

for file in glob.glob("lichen-protocol-mvp/protocols/*.json"):
    with open(file) as f:
        data = json.load(f)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        print(f"❌ {file}")
        for err in errors:
            print(f"  - {list(err.path)}: {err.message}")
    else:
        print(f"✅ {file}")