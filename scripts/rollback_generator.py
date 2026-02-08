import json
import os
import re

print("🔵 Generating rollback script...")

rollback_sql = "-- No rollback action required"

if os.path.exists("ddl_output.json"):
    with open("ddl_output.json", "r") as f:
        data = json.load(f)

    ddl = data.get("ddl")

    if ddl:
        ddl = ddl.strip().upper()

        # CREATE → DROP
        if ddl.startswith("CREATE TABLE"):
            match = re.search(r"CREATE TABLE\s+([^\s(]+)", ddl)
            if match:
                table = match.group(1)
                rollback_sql = f"DROP TABLE IF EXISTS {table};"

        elif ddl.startswith("DROP TABLE"):
            # ✅ Phase-2: metadata-driven restore
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

# ✅ ALWAYS CREATE FILE
with open("rollback.sql", "w") as f:
    f.write(rollback_sql)

print("Rollback script generated:")
print(rollback_sql)
