import json
import os
import re

print("🔵 Generating rollback script...")

if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found — skipping rollback generation")
    exit(0)

with open("ddl_output.json", "r") as f:
    data = json.load(f)

ddl = data.get("ddl")

if not ddl:
    print("No DDL found — skipping rollback generation")
    exit(0)

ddl = ddl.strip().upper()

rollback_sql = None

# -----------------------------
# Rule 1: CREATE → DROP
# -----------------------------
if ddl.startswith("CREATE TABLE"):
    match = re.search(r"CREATE TABLE\s+([^\s(]+)", ddl)
    if match:
        table = match.group(1)
        rollback_sql = f"DROP TABLE IF EXISTS {table};"

# -----------------------------
# Rule 2: DROP → RESTORE
# -----------------------------
elif ddl.startswith("DROP TABLE"):
    match = re.search(r"DROP TABLE\s+(IF EXISTS\s+)?([^\s;]+)", ddl)
    if match:
        table = match.group(2)
        rollback_sql = f"-- Restore required from backup for table {table}"

# -----------------------------
# Rule 3: ALTER (basic)
# -----------------------------
elif ddl.startswith("ALTER TABLE"):
    rollback_sql = "-- Manual rollback required for ALTER"

# -----------------------------
# Save rollback file
# -----------------------------
if rollback_sql:
    with open("rollback.sql", "w") as f:
        f.write(rollback_sql)

    print("Rollback script generated:")
    print(rollback_sql)
else:
    print("No rollback rule matched")
