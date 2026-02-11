import json
import os
import re

print("🔵 Generating rollback script...")

rollback_lines = []

if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found")

    with open("rollback.sql", "w") as f:
        f.write("-- No rollback required")

    exit(0)

with open("ddl_output.json", "r") as f:
    data = json.load(f)

# 🔥 NEW: support multiple DDLs
ddls = data.get("ddls", [])

# backward compatibility (old format)
if not ddls and data.get("ddl"):
    ddls = [{"stmt": data["ddl"]}]

if not ddls:
    print("No DDL found")

    with open("rollback.sql", "w") as f:
        f.write("-- No rollback required")

    exit(0)

for item in ddls:

    ddl = item["stmt"].strip().upper()
    print("Processing:", ddl)

    rollback_sql = "-- No rollback action required"

    # CREATE → DROP
    if ddl.startswith("CREATE TABLE"):
        match = re.search(r"CREATE TABLE\s+([^\s(]+)", ddl)
        if match:
            table = match.group(1)
            rollback_sql = f"DROP TABLE IF EXISTS {table};"

    # DROP → metadata restore
    elif ddl.startswith("DROP TABLE"):

        if os.path.exists("rollback_metadata.json"):

            with open("rollback_metadata.json", "r") as mf:
                meta = json.load(mf)

            original = meta["original_table"]
            backup = meta["backup_table"]
            catalog = meta["catalog"]
            schema = meta["schema"]

            rollback_sql = f"""
USE CATALOG {catalog};
USE SCHEMA {schema};

DROP TABLE IF EXISTS {original};

CREATE TABLE {original}
AS SELECT * FROM {backup};
"""

        else:
            rollback_sql = "-- Metadata not found: manual restore required"

    # ALTER
    elif ddl.startswith("ALTER TABLE"):
        rollback_sql = "-- Manual rollback required for ALTER"

    rollback_lines.append(rollback_sql)

# ✅ write combined rollback file
with open("rollback.sql", "w") as f:
    f.write("\n\n".join(rollback_lines))

print("\nRollback script generated:")
print("\n".join(rollback_lines))
