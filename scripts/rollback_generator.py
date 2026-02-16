import json
import os
import re

print(" Rollback Generator started")

if not os.path.exists("ddl_output.json"):
    print("ddl_output.json not found")
    exit(0)

with open("ddl_output.json") as f:
    data = json.load(f)

ddls = data.get("ddls", [])
commit_id = data.get("commit_id", "unknown")

rollback_plan = {
    "commit_id": commit_id,
    "rollback_items": []
}

for ddl in ddls:
    stmt = ddl["statement"]
    ddl_id = ddl.get("id")
    ddl_type = ddl["type"]
    classification = ddl.get("classification")

    rollback_sql = "-- manual intervention required"

    stmt_upper = stmt.upper()

    # =====================
    # CREATE → DROP
    # =====================
    if stmt_upper.startswith("CREATE TABLE"):
        match = re.search(r"CREATE TABLE\s+([^\s(]+)", stmt, re.IGNORECASE)
        if match:
            table = match.group(1)
            rollback_sql = f"DROP TABLE IF EXISTS {table};"

    # =====================
    # ALTER HANDLING
    # =====================
    elif stmt_upper.startswith("ALTER TABLE"):

        table_match = re.search(r"ALTER TABLE\s+([^\s]+)", stmt, re.IGNORECASE)

        if table_match:
            table = table_match.group(1)

            # ADD COLUMN
            add_col = re.search(r"ADD COLUMN\s+([^\s]+)", stmt, re.IGNORECASE)
            if add_col:
                col = add_col.group(1)
                rollback_sql = f"ALTER TABLE {table} DROP COLUMN {col};"

            # RENAME COLUMN
            rename_col = re.search(
                r"RENAME COLUMN\s+([^\s]+)\s+TO\s+([^\s]+)",
                stmt,
                re.IGNORECASE
            )
            if rename_col:
                old, new = rename_col.groups()
                rollback_sql = (
                    f"ALTER TABLE {table} RENAME COLUMN {new} TO {old};"
                )

            # DROP COLUMN → needs backup
            drop_col = re.search(r"DROP COLUMN\s+([^\s]+)", stmt, re.IGNORECASE)
            if drop_col:
                rollback_sql = "RESTORE_FROM_BACKUP"

    # =====================
    # DROP → backup restore
    # =====================
    elif stmt_upper.startswith("DROP TABLE"):
        rollback_sql = "RESTORE_FROM_BACKUP"

    rollback_plan["rollback_items"].append({
        "ddl_id": ddl_id,
        "statement": stmt,
        "classification": classification,
        "rollback_sql": rollback_sql
    })

# Write rollback plan
with open("rollback_plan.json", "w") as f:
    json.dump(rollback_plan, f, indent=2)

print(" Rollback plan generated")
