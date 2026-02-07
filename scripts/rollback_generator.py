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

        # DROP → RESTORE
        elif ddl.startswith("DROP TABLE"):
            match = re.search(r"DROP TABLE\s+(IF EXISTS\s+)?([^\s;]+)", ddl)
            if match:
                table = match.group(2)
                rollback_sql = f"-- Restore required from backup for table {table}"

        # ALTER
        elif ddl.startswith("ALTER TABLE"):
            rollback_sql = "-- Manual rollback required for ALTER"

# ✅ ALWAYS CREATE FILE
with open("rollback.sql", "w") as f:
    f.write(rollback_sql)

print("Rollback script generated:")
print(rollback_sql)
