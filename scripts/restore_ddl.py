import os
import subprocess

ROLLBACK_FILE = os.path.join(os.environ.get("PIPELINE_WORKSPACE", "."), "rollback.sql")

if not os.path.exists(ROLLBACK_FILE):
    print("rollback.sql not found — nothing to restore")
    exit(0)

with open(ROLLBACK_FILE) as f:
    sql_text = f.read()

# split SQL statements safely
statements = [
    stmt.strip()
    for stmt in sql_text.split(";")
    if stmt.strip()
]

print(f"Executing {len(statements)} rollback statements")

for stmt in statements:

    cmd = f'databricks sql execute --warehouse-id $WAREHOUSE_ID --command "{stmt}"'

    subprocess.check_call(cmd, shell=True)

print("Rollback executed successfully")