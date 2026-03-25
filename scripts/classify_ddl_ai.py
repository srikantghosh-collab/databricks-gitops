import json
import os
import re
import sys

from ddl_parser import split_sql_statements, extract_ddls

print("Starting AI DDL Classification...")

DDL_ARTIFACT = "ddl_output.json"
CLASSIFICATION_ARTIFACT = "ddl_classification.json"


def emit_outputs(is_drop: bool, rollback_type: str) -> None:
    print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
    print(f"##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]{rollback_type}")


def classify_statement(statement: str) -> tuple[str, str]:
    stmt = statement.strip().upper()

    if stmt.startswith("CREATE TABLE"):
        return "CREATE_TABLE", "REVERSIBLE"

    if stmt.startswith("DROP TABLE"):
        return "DROP_TABLE", "IRREVERSIBLE"

    if stmt.startswith("TRUNCATE TABLE"):
        return "TRUNCATE_TABLE", "IRREVERSIBLE"

    if stmt.startswith("ALTER TABLE"):
        if re.search(r"\bADD\s+COLUMNS?\b", stmt):
            return "ALTER_TABLE_ADD_COLUMN", "REVERSIBLE"

        if "RENAME COLUMN" in stmt:
            return "ALTER_TABLE_RENAME_COLUMN", "REVERSIBLE"

        if "DROP COLUMN" in stmt:
            return "ALTER_TABLE_DROP_COLUMN", "IRREVERSIBLE"

        if re.search(r"\bALTER\s+COLUMN\b", stmt) and re.search(r"\bTYPE\b", stmt):
            return "ALTER_TABLE_ALTER_COLUMN_TYPE", "IRREVERSIBLE"

        return "ALTER_TABLE_OTHER", "IRREVERSIBLE"

    return "NONE", "UNKNOWN"


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
classified_ddls = []

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
        ddl_classification, reversibility = classify_statement(ddl["statement"])
        print(f"  - {ddl['statement']}")
        print(f"    Classification: {ddl_classification}")
        print(f"    Reversibility: {reversibility}")

        classified_ddls.append({
            "script_name": script_name,
            "statement": ddl["statement"],
            "table": ddl.get("table"),
            "classification": ddl_classification,
            "reversibility": reversibility,
        })

    all_ddls.extend(ddls)

if not all_ddls:
    print("No DDL statements found")
    emit_outputs(False, "NONE")
    sys.exit(0)

statement_texts = [ddl["statement"].strip().upper() for ddl in all_ddls]
classification_names = [item["classification"] for item in classified_ddls]
reversibility_names = [item["reversibility"] for item in classified_ddls]

if "DROP_TABLE" in classification_names:
    final_classification = "DROP_TABLE"
elif any(name.startswith("ALTER_TABLE") for name in classification_names):
    final_classification = "ALTER_TABLE"
elif "CREATE_TABLE" in classification_names:
    final_classification = "CREATE_TABLE"
elif "TRUNCATE_TABLE" in classification_names:
    final_classification = "TRUNCATE_TABLE"
else:
    final_classification = "NONE"

if reversibility_names and all(name == "REVERSIBLE" for name in reversibility_names):
    rollback_type = "DIRECT_REVERSE"
elif any(name == "IRREVERSIBLE" for name in reversibility_names):
    rollback_type = "AI_RECONSTRUCT"
else:
    rollback_type = "NONE"

if reversibility_names and all(name == "REVERSIBLE" for name in reversibility_names):
    reversibility_summary = "REVERSIBLE"
elif any(name == "IRREVERSIBLE" for name in reversibility_names):
    reversibility_summary = "IRREVERSIBLE"
else:
    reversibility_summary = "UNKNOWN"

is_drop = any(stmt.startswith("DROP TABLE") for stmt in statement_texts)

with open(CLASSIFICATION_ARTIFACT, "w") as f:
    json.dump(
        {
            "final_classification": final_classification,
            "reversibility_summary": reversibility_summary,
            "rollback_type": rollback_type,
            "is_drop": is_drop,
            "statements": classified_ddls,
        },
        f,
        indent=2,
    )

print("Final Classification:", final_classification)
print("Reversibility Summary:", reversibility_summary)
print("Rollback Type:", rollback_type)
print("Is Drop:", is_drop)

emit_outputs(is_drop, rollback_type)
