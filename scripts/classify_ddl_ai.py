import json
import os
import sys

from ddl_parser import split_sql_statements, extract_ddls

print("Starting AI DDL Classification...")

DDL_ARTIFACT = "ddl_output.json"


def emit_outputs(is_drop: bool, rollback_type: str) -> None:
    print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
    print(f"##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]{rollback_type}")


if not os.path.exists(DDL_ARTIFACT):
    print("No ddl_output.json found — skipping classification")
    emit_outputs(False, "NONE")
    sys.exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

migrations = payload.get("migrations", [])

if not migrations:
    print("No migration scripts found in ddl_output.json")
    emit_outputs(False, "NONE")
    sys.exit(0)

all_ddls = []

for migration in migrations:
    script_name = migration.get("script_name", "<unknown>")
    path = migration.get("path")

    if not path or not os.path.exists(path):
        print(f"Skipping missing migration file: {script_name}")
        continue

    with open(path) as f:
        sql_text = f.read()

    statements = split_sql_statements(sql_text)
    ddls = extract_ddls(statements)

    print(f"{script_name}: found {len(ddls)} DDL command(s)")
    for ddl in ddls:
        print(f"  - {ddl['statement']}")

    all_ddls.extend(ddls)

if not all_ddls:
    print("No DDL statements found")
    emit_outputs(False, "NONE")
    sys.exit(0)

statement_texts = [ddl["statement"].strip().upper() for ddl in all_ddls]

if any(stmt.startswith("DROP TABLE") for stmt in statement_texts):
    final_classification = "DROP_TABLE"
    is_drop = True
elif any(stmt.startswith("ALTER TABLE") for stmt in statement_texts):
    final_classification = "ALTER_TABLE"
    is_drop = False
elif any(stmt.startswith("CREATE TABLE") for stmt in statement_texts):
    final_classification = "CREATE_TABLE"
    is_drop = False
else:
    final_classification = "NONE"
    is_drop = False

rollback_type = "AI_RECONSTRUCT" if final_classification != "NONE" else "NONE"

print("Final Classification:", final_classification)
print("Rollback Type:", rollback_type)
print("Is Drop:", is_drop)

emit_outputs(is_drop, rollback_type)
