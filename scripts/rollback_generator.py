import json
import os
import re

print("Generating rollback script...")

rollback_sql = "-- No rollback required"

if os.path.exists("ddl_output.json"):

    with open("ddl_output.json") as f:
        data = json.load(f)

    ddl = data.get("ddl")

    if ddl:

        ddl_upper = ddl.upper()

        # CREATE → DROP
        if ddl_upper.startswith("CREATE TABLE"):
            match = re.search(r"CREATE TABLE\s+([^\s(]+)", ddl_upper)

            if match:
                table = match.group(1)
                rollback_sql = f"DROP TABLE IF EXISTS {table};"

        # DROP → restore
        elif ddl_upper.startswith("DROP TABLE"):

            if os.path.exists("rollback_metadata.json"):

                with open("rollback_metadata.json") as mf:
                    meta = json.load(mf)

                original = meta["original_table"]
                backup = meta["backup_table"]

                rollback_sql = f"""
DROP TABLE IF EXISTS {original};
CREATE TABLE {original}
AS SELECT * FROM {backup};
"""

            else:
                rollback_sql = "-- Metadata not found: manual restore required"

# Always create file
with open("rollback.sql", "w") as f:
    f.write(rollback_sql)

print("Rollback script generated:")
print(rollback_sql)
